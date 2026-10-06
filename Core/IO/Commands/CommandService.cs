namespace Hammer5Tools.Core.IO.Commands;

using System.IO;
using Hammer5Tools.Core.Commands;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.IO.Cs2;
using Microsoft.Extensions.Logging;

/// <summary>
/// High-level service combining named pipe commands and console log listening.
/// </summary>
public class CommandService : ICommandService, IDisposable
{
    private readonly ICs2Locator Cs2Locator;
    private readonly ILogger<CommandService>? Logger;
    private readonly CommandPipeClient Pipe;

    private bool IsStarted;

    private ConsoleLogListener? LogListener;

    public bool IsConnected => Pipe.IsConnected;

    public IReadOnlyList<ConsoleHelperCommand> HelperCommands { get; private set; } = [];

    public event EventHandler<string>? OutputLineReceived;

    public CommandService(
        ICs2Locator cs2Locator,
        ILogger<CommandService>? logger = null,
        CommandPipeClient? pipe = null)
    {
        Cs2Locator = cs2Locator;
        Logger = logger;
        Pipe = pipe ?? new CommandPipeClient(logger);
    }

    /// <inheritdoc/>
    public void Start()
    {
        if (IsStarted)
        {
            return;
        }

        IsStarted = true;
        HelperCommands = ConvarHelperFiles.Load(Cs2Locator.ResolvedCs2Path, Logger);
        Pipe.Start();

        var cs2Path = Cs2Locator.ResolvedCs2Path;
        if (!string.IsNullOrWhiteSpace(cs2Path))
        {
            var logPath = Path.Combine(cs2Path, "game", "csgo", Cs2Launcher.LogFileName);
            LogListener = new ConsoleLogListener(logPath, Logger);
            LogListener.LineReceived += OnOutputReceived;
            LogListener.Start();
        }
    }

    /// <inheritdoc/>
    public void Stop()
    {
        IsStarted = false;
        Pipe.Stop();
        LogListener?.Stop();
        LogListener?.Dispose();
        LogListener = null;
    }

    /// <inheritdoc/>
    public async Task<bool> PrepareLaunchAsync(CancellationToken ct = default)
    {
        Start();
        return await Pipe.WaitUntilReadyAsync(ct);
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

            if (!await SendCommandAsync(cmd, ct))
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
