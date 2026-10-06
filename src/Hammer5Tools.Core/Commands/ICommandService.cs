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

    /// <summary>Gets the VConsole connection status.</summary>
    string VConsoleStatus { get; }

    /// <summary>Gets the current live convar catalog revision.</summary>
    int ConvarRevision { get; }

    /// <summary>Gets a snapshot of convars learned from VConsole.</summary>
    IReadOnlyList<ConsoleVariable> Convars { get; }

    /// <summary>Enables or releases the local game's VConsole connection.</summary>
    void SetVConsoleEnabled(bool enabled);

    /// <summary>
    /// Event raised when a line is output to the console log or pipe.
    /// </summary>
    event EventHandler<string>? OutputLineReceived;

    /// <summary>
    /// Starts the command pipe servers and log listener.
    /// </summary>
    void Start();

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
