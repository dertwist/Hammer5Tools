namespace Hammer5Tools.Core.IO.Settings;

using System.IO;
using System.Text.Json;
using Hammer5Tools.Core.Settings;
using Microsoft.Extensions.Logging;

/// <summary>
/// JSON-based settings service implementing atomic file persistence and thread-safe access.
/// </summary>
public class JsonSettingsService : ISettingsService
{
    private readonly string SettingsFilePath;
    private readonly string LegacyIniPath;
    private readonly ILogger<JsonSettingsService>? Logger;
    private readonly Lock SyncLock = new();

    private AppSettings CurrentSettings;

    public AppSettings Settings
    {
        get
        {
            lock (SyncLock)
            {
                return CurrentSettings;
            }
        }
    }

    public event EventHandler<AppSettings>? SettingsChanged;

    public JsonSettingsService(string? customSettingsPath = null, ILogger<JsonSettingsService>? logger = null)
    {
        Logger = logger;
        CurrentSettings = new AppSettings();

        if (!string.IsNullOrWhiteSpace(customSettingsPath))
        {
            SettingsFilePath = customSettingsPath;
            var directory = Path.GetDirectoryName(customSettingsPath) ?? string.Empty;
            LegacyIniPath = Path.Combine(directory, "settings.ini");
        }
        else
        {
            var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            var defaultDir = Path.Combine(appData, "Hammer5Tools");
            SettingsFilePath = Path.Combine(defaultDir, "settings.json");
            LegacyIniPath = Path.Combine(defaultDir, "settings.ini");
        }

        Load();
    }

    /// <inheritdoc/>
    public void Load()
    {
        lock (SyncLock)
        {
            if (File.Exists(SettingsFilePath))
            {
                try
                {
                    using var stream = new FileStream(SettingsFilePath, FileMode.Open, FileAccess.Read, FileShare.Read);
                    var deserialized = JsonSerializer.Deserialize(stream, SettingsJsonContext.Default.AppSettings);
                    if (deserialized is not null)
                    {
                        stream.Position = 0;
                        using var document = JsonDocument.Parse(stream);
                        if (document.RootElement.TryGetProperty("editor", out var editor) && !editor.TryGetProperty("launchOptions", out _))
                        {
                            var launch = Core.Cs2.LaunchOptions.FromLegacy(deserialized.Editor.CustomLaunchArgs);
                            launch.Options.OpenTools = true;
                            launch.Options.Insecure = true;
                            deserialized.Editor.LaunchOptions = launch.Options;
                            deserialized.Editor.CustomLaunchArgs = launch.CustomArgs;
                        }
                        CurrentSettings = deserialized;
                        return;
                    }
                }
                catch (Exception ex)
                {
                    Logger?.LogWarning(ex, "Failed to read settings from {Path}, resetting to defaults", SettingsFilePath);
                }
            }

            CurrentSettings = new AppSettings();

            var migrator = new LegacySettingsMigrator(Logger);
            if (migrator.TryMigrate(LegacyIniPath, CurrentSettings))
            {
                SaveInternal();
            }
        }
    }

    /// <inheritdoc/>
    public void Save()
    {
        lock (SyncLock)
        {
            SaveInternal();
        }

        SettingsChanged?.Invoke(this, Settings);
    }

    /// <inheritdoc/>
    public void Update(Action<AppSettings> updateAction)
    {
        ArgumentNullException.ThrowIfNull(updateAction);

        lock (SyncLock)
        {
            updateAction(CurrentSettings);
            SaveInternal();
        }

        SettingsChanged?.Invoke(this, Settings);
    }

    private void SaveInternal()
    {
        var targetDirectory = Path.GetDirectoryName(SettingsFilePath);
        if (!string.IsNullOrEmpty(targetDirectory) && !Directory.Exists(targetDirectory))
        {
            Directory.CreateDirectory(targetDirectory);
        }

        var tempPath = $"{SettingsFilePath}.tmp.{Guid.NewGuid():N}";

        try
        {
            using (var stream = new FileStream(tempPath, FileMode.Create, FileAccess.Write, FileShare.None))
            {
                JsonSerializer.Serialize(stream, CurrentSettings, SettingsJsonContext.Default.AppSettings);
                stream.Flush(true);
            }

            File.Move(tempPath, SettingsFilePath, overwrite: true);
        }
        catch (Exception ex)
        {
            Logger?.LogError(ex, "Failed to atomically write settings to {Path}", SettingsFilePath);
            if (File.Exists(tempPath))
            {
                try
                {
                    File.Delete(tempPath);
                }
                catch
                {
                    // Ignore temp file cleanup errors
                }
            }

            throw;
        }
    }
}
