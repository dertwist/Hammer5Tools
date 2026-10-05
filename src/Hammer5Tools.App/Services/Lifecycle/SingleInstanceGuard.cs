namespace Hammer5Tools.App.Services.Lifecycle;

using System.Diagnostics;
using System.IO.Pipes;

/// <summary>
/// Coordinates single-instance ownership and forwards tool launches to the running application.
/// </summary>
public class SingleInstanceGuard : IDisposable
{
    private const string MutexName = "Local\\Hammer5Tools_SingleInstance_Mutex";

    private readonly Mutex? InstanceMutex;
    private readonly bool HasHandle;
    private readonly string PipeName;
    private readonly CancellationTokenSource Shutdown = new();
    private Task? Listener;
    private bool IsDisposed;

    public bool IsFirstInstance => HasHandle;

    public SingleInstanceGuard(string? instanceName = null)
    {
        using var process = Process.GetCurrentProcess();
        PipeName = instanceName ?? $"Hammer5Tools_Startup_{Environment.UserName}_{process.SessionId}";
        try
        {
            InstanceMutex = new Mutex(initiallyOwned: true, instanceName ?? MutexName, out var createdNew);
            HasHandle = createdNew;
        }
        catch
        {
            HasHandle = true; // Fallback to allowing startup if mutex creation fails
        }
    }

    public void StartListening(Action<StartupTool> openTool)
    {
        if (!IsFirstInstance || Listener is not null)
        {
            throw new InvalidOperationException("Only the owning instance can start the launch listener once.");
        }

        Listener = ListenAsync(openTool);
    }

    public async Task ForwardAsync(StartupTool tool, CancellationToken cancellationToken = default)
    {
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromSeconds(5));
        using var client = new NamedPipeClientStream(".", PipeName, PipeDirection.InOut, PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);
        await client.ConnectAsync(timeout.Token);
        await client.WriteAsync(new byte[] { (byte)tool }, timeout.Token);
        var acknowledgement = new byte[1];
        if (await client.ReadAsync(acknowledgement, timeout.Token) != 1 || acknowledgement[0] != 1)
        {
            throw new IOException("The running application did not accept the launch request.");
        }
    }

    private async Task ListenAsync(Action<StartupTool> openTool)
    {
        while (!Shutdown.IsCancellationRequested)
        {
            try
            {
                using var server = new NamedPipeServerStream(PipeName, PipeDirection.InOut, 1,
                    PipeTransmissionMode.Byte, PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);
                await server.WaitForConnectionAsync(Shutdown.Token).ConfigureAwait(false);
                using var timeout = CancellationTokenSource.CreateLinkedTokenSource(Shutdown.Token);
                timeout.CancelAfter(TimeSpan.FromSeconds(5));
                var request = new byte[1];
                if (await server.ReadAsync(request, timeout.Token).ConfigureAwait(false) == 1 && Enum.IsDefined((StartupTool)request[0]))
                {
                    openTool((StartupTool)request[0]);
                    await server.WriteAsync(new byte[] { 1 }, timeout.Token).ConfigureAwait(false);
                }
            }
            catch (OperationCanceledException) when (Shutdown.IsCancellationRequested)
            {
                return;
            }
            catch (Exception ex) when (ex is IOException or OperationCanceledException)
            {
                // A disconnected client must not stop subsequent launch requests.
            }
        }
    }

    public void Dispose()
    {
        if (IsDisposed) return;
        IsDisposed = true;
        Shutdown.Cancel();
        Listener?.GetAwaiter().GetResult();
        Shutdown.Dispose();
        if (HasHandle)
        {
            try
            {
                InstanceMutex?.ReleaseMutex();
            }
            catch
            {
                // Ignore release errors
            }
        }

        InstanceMutex?.Dispose();
        GC.SuppressFinalize(this);
    }
}
