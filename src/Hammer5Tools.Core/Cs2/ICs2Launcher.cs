namespace Hammer5Tools.Core.Cs2;

/// <summary>
/// Service managing the lifecycle, launching, monitoring, and killing of the Counter-Strike 2 process.
/// </summary>
public interface ICs2Launcher
{
    /// <summary>
    /// Gets whether a CS2 process is currently running.
    /// </summary>
    bool IsRunning { get; }

    /// <summary>
    /// Gets the process ID of the running CS2 process, if running.
    /// </summary>
    int? ProcessId { get; }

    /// <summary>
    /// Event raised when the CS2 process starts or exits.
    /// </summary>
    event EventHandler<bool>? ProcessStateChanged;

    /// <summary>
    /// Constructs the complete command line arguments for launching CS2 Workshop Tools.
    /// </summary>
    string BuildLaunchArguments(string? additionalArgs = null, bool ncmMode = false);

    /// <summary>
    /// Launches the CS2 process with Workshop Tools enabled.
    /// </summary>
    Task<bool> LaunchAsync(string? additionalArgs = null, bool ncmMode = false, CancellationToken ct = default);

    /// <summary>
    /// Terminates the running CS2 process immediately.
    /// </summary>
    bool Kill();

    /// <summary>
    /// Kills the running CS2 process (if any) and restarts it.
    /// </summary>
    Task<bool> RestartAsync(string? additionalArgs = null, bool ncmMode = false, CancellationToken ct = default);
}
