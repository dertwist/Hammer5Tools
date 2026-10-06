namespace Hammer5Tools.Core.IO.Commands;

using System.IO;
using System.IO.Pipes;
using System.Text;
using Microsoft.Extensions.Logging;

/// <summary>
/// Manages the NamedPipeServer streams for bidirectional console communication with CS2.
/// </summary>
public class Cs2CommandPipe : IDisposable
{
    public const string PipeNameIn = "hammer5tools_cmd";
    public const string PipeNameOut = "hammer5tools_out";

    private readonly ILogger? Logger;
    private readonly Lock SyncLock = new();
    private readonly CancellationTokenSource Cts = new();

    private NamedPipeServerStream? CommandPipeServer;
    private NamedPipeServerStream? OutputPipeServer;
    private Task? ListenTask;

    public bool IsConnected
    {
        get
        {
            lock (SyncLock)
            {
                return CommandPipeServer?.IsConnected == true;
            }
        }
    }

    public event EventHandler<string>? OutputReceived;

    public Cs2CommandPipe(ILogger? logger = null)
    {
        Logger = logger;
    }

    public void Start()
    {
        if (ListenTask is not null)
        {
            return;
        }

        ListenTask = Task.Run(() => ServerLoopAsync(Cts.Token));
    }

    public void Stop()
    {
        Cts.Cancel();
        lock (SyncLock)
        {
            try
            {
                CommandPipeServer?.Dispose();
                OutputPipeServer?.Dispose();
            }
            catch
            {
                // Ignore pipe close errors
            }

            CommandPipeServer = null;
            OutputPipeServer = null;
        }
    }

    public async Task<bool> SendCommandAsync(string command, CancellationToken ct = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(command);

        NamedPipeServerStream? server;
        lock (SyncLock)
        {
            server = CommandPipeServer;
        }

        if (server is null || !server.IsConnected)
        {
            Logger?.LogWarning("Cannot send command '{Command}': Pipe is not connected.", command);
            return false;
        }

        try
        {
            var line = command.TrimEnd() + "\n";
            var bytes = Encoding.UTF8.GetBytes(line);
            await server.WriteAsync(bytes, ct);
            await server.FlushAsync(ct);
            return true;
        }
        catch (Exception ex)
        {
            Logger?.LogError(ex, "Failed to write command to pipe: {Command}", command);
            return false;
        }
    }

    private async Task ServerLoopAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            try
            {
                var cmdPipe = new NamedPipeServerStream(
                    PipeNameIn,
                    PipeDirection.InOut,
                    1,
                    PipeTransmissionMode.Byte,
                    PipeOptions.Asynchronous);

                var outPipe = new NamedPipeServerStream(
                    PipeNameOut,
                    PipeDirection.InOut,
                    1,
                    PipeTransmissionMode.Byte,
                    PipeOptions.Asynchronous);

                lock (SyncLock)
                {
                    CommandPipeServer?.Dispose();
                    OutputPipeServer?.Dispose();
                    CommandPipeServer = cmdPipe;
                    OutputPipeServer = outPipe;
                }

                Logger?.LogInformation("Waiting for CS2 to connect to named pipes...");

                await Task.WhenAll(
                    cmdPipe.WaitForConnectionAsync(ct),
                    outPipe.WaitForConnectionAsync(ct));

                Logger?.LogInformation("CS2 connected to command pipe.");

                // Read output from outPipe until disconnected
                using var reader = new StreamReader(outPipe, Encoding.UTF8, leaveOpen: true);
                while (await reader.ReadLineAsync(ct) is { } line)
                {
                    OutputReceived?.Invoke(this, line);
                }
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                Logger?.LogDebug(ex, "Pipe server loop cycle error or disconnect.");
                await Task.Delay(500, ct);
            }
        }
    }

    public void Dispose()
    {
        Stop();
        Cts.Dispose();
        GC.SuppressFinalize(this);
    }
}
