namespace Hammer5Tools.Core.IO.Commands;

using System.Diagnostics;
using System.IO.Pipes;
using System.Reflection;
using System.Text;
using Microsoft.Extensions.Logging;

/// <summary>Connects the application to the persistent CS2 command pipe host.</summary>
public sealed class CommandPipeClient : IDisposable
{
    private readonly string ControlName;
    private readonly bool LaunchHost;
    private readonly ILogger? Logger;
    private readonly SemaphoreSlim RequestLock = new(1);
    private CancellationTokenSource? Cts;
    private Task? ListenTask;
    private NamedPipeClientStream? Stream;
    private StreamReader? Reader;
    private StreamWriter? Writer;
    private volatile bool Connected;
    private bool IsDisposed;

    /// <summary>Gets the last reported game pipe connection state.</summary>
    public bool IsConnected => Connected;

    /// <summary>Creates a client, optionally attaching to an isolated test host.</summary>
    public CommandPipeClient(ILogger? logger = null, string controlName = CommandPipeHost.ControlPipeName, bool launchHost = true)
    {
        Logger = logger;
        ControlName = controlName;
        LaunchHost = launchHost;
    }

    /// <summary>Starts reconnecting without blocking the UI.</summary>
    public void Start()
    {
        ObjectDisposedException.ThrowIf(IsDisposed, this);
        if (ListenTask is not null)
        {
            return;
        }
        Cts = new CancellationTokenSource();
        ListenTask = Task.Run(() => ConnectAsync(Cts.Token));
    }

    /// <summary>Detaches only this client, leaving the game's handles alive.</summary>
    public void Stop()
    {
        Cts?.Cancel();
        Stream?.Dispose();
        try
        {
            ListenTask?.GetAwaiter().GetResult();
        }
        catch (OperationCanceledException)
        {
            // Shutdown cancels pending connects and reads.
        }
        ListenTask = null;
        Cts?.Dispose();
        Cts = null;
        Connected = false;
    }

    /// <summary>Sends a command to the host; false indicates that CS2 did not receive it.</summary>
    public Task<bool> SendCommandAsync(string command, CancellationToken ct = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(command);
        return RequestAsync(Convert.ToBase64String(Encoding.UTF8.GetBytes(command)), ct);
    }

    /// <summary>Waits until the host has created the game pipes before CS2 starts.</summary>
    public async Task<bool> WaitUntilReadyAsync(CancellationToken ct = default)
    {
        Start();
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeout.CancelAfter(TimeSpan.FromSeconds(10));
        try
        {
            while (!timeout.IsCancellationRequested)
            {
                await RequestLock.WaitAsync(timeout.Token);
                try
                {
                    if (Writer is not null)
                    {
                        return true;
                    }
                }
                finally
                {
                    RequestLock.Release();
                }
                await Task.Delay(50, timeout.Token);
            }
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            return false;
        }
        return false;
    }

    private async Task<bool> RequestAsync(string request, CancellationToken ct)
    {
        await RequestLock.WaitAsync(ct);
        try
        {
            if (Writer is null || Reader is null)
            {
                return false;
            }
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
            timeout.CancelAfter(TimeSpan.FromSeconds(3));
            await Writer.WriteLineAsync(request.AsMemory(), timeout.Token);
            return await Reader.ReadLineAsync(timeout.Token) == "1";
        }
        catch (Exception ex) when (ex is IOException or ObjectDisposedException or OperationCanceledException)
        {
            Connected = false;
            Stream?.Dispose();
            return false;
        }
        finally
        {
            RequestLock.Release();
        }
    }

    private async Task ConnectAsync(CancellationToken ct)
    {
        var lastLaunch = DateTime.MinValue;
        while (!ct.IsCancellationRequested)
        {
            using var stream = new NamedPipeClientStream(".", ControlName, PipeDirection.InOut, PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);
            try
            {
                Stream = stream;
                await stream.ConnectAsync(500, ct);
                using var reader = new StreamReader(stream, Encoding.UTF8, leaveOpen: true);
                using var writer = new StreamWriter(stream, new UTF8Encoding(false), leaveOpen: true) { AutoFlush = true };
                await RequestLock.WaitAsync(ct);
                try
                {
                    Reader = reader;
                    Writer = writer;
                }
                finally
                {
                    RequestLock.Release();
                }
                while (stream.IsConnected && !ct.IsCancellationRequested)
                {
                    Connected = await RequestAsync(string.Empty, ct);
                    await Task.Delay(200, ct);
                }
            }
            catch (Exception ex) when (ex is IOException or TimeoutException or ObjectDisposedException or OperationCanceledException)
            {
                if (!ct.IsCancellationRequested && LaunchHost && DateTime.UtcNow - lastLaunch > TimeSpan.FromSeconds(5))
                {
                    lastLaunch = DateTime.UtcNow;
                    StartHost();
                }
            }
            finally
            {
                await RequestLock.WaitAsync(CancellationToken.None);
                try
                {
                    Reader = null;
                    Writer = null;
                    Stream = null;
                    Connected = false;
                }
                finally
                {
                    RequestLock.Release();
                }
            }
            await Task.Delay(200, ct);
        }
    }

    private void StartHost()
    {
        try
        {
            var executable = Environment.ProcessPath ?? throw new InvalidOperationException("Application executable is unavailable.");
            var start = new ProcessStartInfo(executable) { UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden };
            if (string.Equals(Path.GetFileNameWithoutExtension(executable), "dotnet", StringComparison.OrdinalIgnoreCase))
            {
                start.ArgumentList.Add(Assembly.GetEntryAssembly()!.Location);
            }
            start.ArgumentList.Add(CommandPipeHost.StartupArgument);
            using var process = Process.Start(start);
        }
        catch (Exception ex) when (ex is InvalidOperationException or System.ComponentModel.Win32Exception)
        {
            Logger?.LogWarning(ex, "Could not start the CS2 command pipe host");
        }
    }

    /// <inheritdoc/>
    public void Dispose()
    {
        if (IsDisposed)
        {
            return;
        }
        Stop();
        IsDisposed = true;
        RequestLock.Dispose();
    }
}
