namespace Hammer5Tools.Core.IO.Commands;

using System.IO.Pipes;
using System.Text;

/// <summary>Keeps CS2's pipe handles alive independently of the application windows.</summary>
public sealed class CommandPipeHost
{
    internal const string ControlPipeName = "hammer5tools_console_control_v1";
    public const string StartupArgument = "--command-pipe-host";
    private readonly Cs2CommandPipe GamePipe;
    private readonly string ControlName;

    /// <summary>Creates a host, optionally using isolated pipe names for regression tests.</summary>
    public CommandPipeHost(Cs2CommandPipe? gamePipe = null, string controlName = ControlPipeName)
    {
        GamePipe = gamePipe ?? new Cs2CommandPipe();
        ControlName = controlName;
    }

    /// <summary>Runs the hidden host once per user session, without starting the GUI.</summary>
    public static void Run()
    {
        using var mutex = new Mutex(true, @"Local\" + ControlPipeName, out var ownsHost);
        if (!ownsHost)
        {
            return;
        }
        try
        {
            new CommandPipeHost().RunAsync().GetAwaiter().GetResult();
        }
        finally
        {
            mutex.ReleaseMutex();
        }
    }

    /// <summary>Serves reconnectable application clients until idle, retaining the game connection.</summary>
    public async Task RunAsync(CancellationToken ct = default)
    {
        using (GamePipe)
        using (var lifetime = CancellationTokenSource.CreateLinkedTokenSource(ct))
        using (var sendLock = new SemaphoreSlim(1))
        {
            GamePipe.Start();
            var clients = new List<Task>();
            var lastActive = DateTime.UtcNow;
            try
            {
                while (!lifetime.IsCancellationRequested)
                {
                    var control = new NamedPipeServerStream(ControlName, PipeDirection.InOut, NamedPipeServerStream.MaxAllowedServerInstances,
                        PipeTransmissionMode.Byte, PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);
                    using var idle = CancellationTokenSource.CreateLinkedTokenSource(lifetime.Token);
                    idle.CancelAfter(TimeSpan.FromSeconds(1));
                    try
                    {
                        await control.WaitForConnectionAsync(idle.Token);
                        clients.Add(ServeClientAsync(control, sendLock, lifetime.Token));
                    }
                    catch (OperationCanceledException) when (!lifetime.IsCancellationRequested)
                    {
                        control.Dispose();
                    }
                    catch
                    {
                        control.Dispose();
                        throw;
                    }
                    clients.RemoveAll(task => task.IsCompleted);
                    if (clients.Count > 0 || GamePipe.IsConnected)
                    {
                        lastActive = DateTime.UtcNow;
                    }
                    if (DateTime.UtcNow - lastActive > TimeSpan.FromSeconds(30))
                    {
                        return;
                    }
                }
            }
            finally
            {
                await lifetime.CancelAsync();
                await Task.WhenAll(clients);
            }
        }
    }

    private async Task ServeClientAsync(NamedPipeServerStream control, SemaphoreSlim sendLock, CancellationToken ct)
    {
        using (control)
        {
            try
            {
                using var reader = new StreamReader(control, Encoding.UTF8, leaveOpen: true);
                using var writer = new StreamWriter(control, new UTF8Encoding(false), leaveOpen: true) { AutoFlush = true };
                while (await reader.ReadLineAsync(ct) is { } request)
                {
                    var success = GamePipe.IsConnected;
                    if (request.Length > 0)
                    {
                        var command = Encoding.UTF8.GetString(Convert.FromBase64String(request));
                        await sendLock.WaitAsync(ct);
                        try
                        {
                            success = await GamePipe.SendCommandAsync(command, ct);
                        }
                        finally
                        {
                            sendLock.Release();
                        }
                    }
                    await writer.WriteLineAsync((success ? "1" : "0").AsMemory(), ct);
                }
            }
            catch (Exception ex) when (ex is IOException or ArgumentException or OperationCanceledException or FormatException)
            {
                // Closing an application client must never disconnect the game pipes.
            }
        }
    }
}
