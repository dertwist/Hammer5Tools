namespace Hammer5Tools.Core.Commands;

/// <summary>
/// Service for bidirectional console communication with a running Counter-Strike 2 instance.
/// </summary>
public interface ICommandService
{
    /// <summary>
    /// Gets whether the command pipe is currently connected to a running CS2 instance.
    /// </summary>
    bool IsConnected { get; }

    /// <summary>Gets shared workshop and current-user Convar Helper command presets.</summary>
    IReadOnlyList<ConsoleHelperCommand> HelperCommands { get; }

    /// <summary>Compatibility status for older application assemblies. VConsole is unused.</summary>
    string VConsoleStatus => "Command pipe console";

    /// <summary>Compatibility revision for the retired live catalog.</summary>
    int ConvarRevision => 0;

    /// <summary>Compatibility live catalog for older application assemblies.</summary>
    IReadOnlyList<ConsoleVariable> Convars => [];

    /// <summary>Retains binary compatibility; the command service never connects to VConsole.</summary>
    void SetVConsoleEnabled(bool enabled) { }

    /// <summary>
    /// Event raised when a line is output to the console log or pipe.
    /// </summary>
    event EventHandler<string>? OutputLineReceived;

    /// <summary>
    /// Starts the command pipe servers and log listener.
    /// </summary>
    void Start();

    /// <summary>Ensures that persistent command pipes exist before the game starts.</summary>
    Task<bool> PrepareLaunchAsync(CancellationToken ct = default)
    {
        Start();
        return Task.FromResult(true);
    }

    /// <summary>
    /// Stops the command pipe servers and log listener.
    /// </summary>
    void Stop();

    /// <summary>
    /// Sends a console command to CS2 via the command pipe.
    /// </summary>
    Task<bool> SendCommandAsync(string command, CancellationToken ct = default);

    /// <summary>
    /// Sends a sequence of console commands to CS2.
    /// </summary>
    Task<bool> SendCommandsAsync(IEnumerable<string> commands, CancellationToken ct = default);
}
