namespace Hammer5Tools.Core.Settings;

/// <summary>
/// Service providing access to persistent application settings.
/// </summary>
public interface ISettingsService
{
    /// <summary>
    /// Gets the current application settings.
    /// </summary>
    AppSettings Settings { get; }

    /// <summary>
    /// Event raised when settings are modified and persisted.
    /// </summary>
    event EventHandler<AppSettings>? SettingsChanged;

    /// <summary>
    /// Loads settings from disk, applying defaults or legacy migration if necessary.
    /// </summary>
    void Load();

    /// <summary>
    /// Saves current settings to disk atomically.
    /// </summary>
    void Save();

    /// <summary>
    /// Updates settings using an action and atomically persists the change.
    /// </summary>
    /// <param name="updateAction">Action modifying the settings.</param>
    void Update(Action<AppSettings> updateAction);
}
