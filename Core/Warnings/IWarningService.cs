namespace Hammer5Tools.Core.Warnings;

/// <summary>
/// Service that tracks and manages active application warnings.
/// </summary>
public interface IWarningService
{
    /// <summary>
    /// Gets all currently active warnings.
    /// </summary>
    IReadOnlyList<AppWarning> Warnings { get; }

    /// <summary>
    /// Gets whether any warnings are currently active.
    /// </summary>
    bool HasWarnings { get; }

    /// <summary>
    /// Gets the primary active warning, if any.
    /// </summary>
    AppWarning? PrimaryWarning { get; }

    /// <summary>
    /// Event raised when the list of active warnings changes.
    /// </summary>
    event EventHandler? WarningsChanged;

    /// <summary>
    /// Adds or updates an active warning.
    /// </summary>
    void SetWarning(AppWarning warning);

    /// <summary>
    /// Removes a warning by its identifier.
    /// </summary>
    bool RemoveWarning(string id);

    /// <summary>
    /// Clears all active warnings.
    /// </summary>
    void Clear();
}
