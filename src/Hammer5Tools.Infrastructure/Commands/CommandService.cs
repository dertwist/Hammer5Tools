namespace Hammer5Tools.Infrastructure.Commands;

using System.IO;
using Hammer5Tools.Core.Commands;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Infrastructure.Cs2;
using Microsoft.Extensions.Logging;

/// <summary>
/// High-level service combining named pipe commands and console log listening.
/// </summary>
public class CommandService : ICommandService, IDisposable
{
    private readonly ICs2Locator Cs2Locator;
    private readonly ILogger<CommandService>? Logger;
    private readonly Cs2CommandPipe Pipe;

    private ConsoleLogListener? LogListener;

    public bool IsConnected => Pipe.IsConnected;

    public event EventHandler<string>? OutputLineReceived;

    public CommandService(
        ICs2Locator cs2Locator,
        ILogger<CommandService>? logger = null)
    {
        Cs2Locator = cs2Locator;
        Logger = logger;
        Pipe = new Cs2CommandPipe(logger);
        Pipe.OutputReceived += OnOutputReceived;
    }

    /// <inheritdoc/>
    public void Start()
    {
        Pipe.Start();

        var cs2Path = Cs2Locator.ResolvedCs2Path;
        if (!string.IsNullOrWhiteSpace(cs2Path))
        {
            var logPath = Path.Combine(Cs2Paths.GetBinWin64Path(cs2Path), Cs2Launcher.LogFileName);
            LogListener = new ConsoleLogListener(logPath, Logger);
            LogListener.LineReceived += OnOutputReceived;
            LogListener.Start();
        }
    }

    /// <inheritdoc/>
    public void Stop()
    {
        Pipe.Stop();
        LogListener?.Stop();
        LogListener?.Dispose();
        LogListener = null;
    }

    /// <inheritdoc/>
    public async Task<bool> SendCommandAsync(string command, CancellationToken ct = default)
    {
        return await Pipe.SendCommandAsync(command, ct);
    }

    /// <inheritdoc/>
    public async Task<bool> SendCommandsAsync(IEnumerable<string> commands, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(commands);

        var allSuccess = true;
        foreach (var cmd in commands)
        {
            if (ct.IsCancellationRequested)
            {
                return false;
            }

            if (!await Pipe.SendCommandAsync(cmd, ct))
            {
                allSuccess = false;
            }
        }

        return allSuccess;
    }

    private void OnOutputReceived(object? sender, string line)
    {
        OutputLineReceived?.Invoke(this, line);
    }

    public void Dispose()
    {
        Stop();
        Pipe.Dispose();
        GC.SuppressFinalize(this);
    }
}
