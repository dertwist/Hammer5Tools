namespace Hammer5Tools.Infrastructure.Settings;

using System.IO;
using Hammer5Tools.Core.Settings;
using Microsoft.Extensions.Logging;

/// <summary>
/// Handles one-time migration from legacy Python QSettings (settings.ini).
/// </summary>
internal class LegacySettingsMigrator
{
    private readonly ILogger? Logger;

    public LegacySettingsMigrator(ILogger? logger = null)
    {
        Logger = logger;
    }

    /// <summary>
    /// Attempts to migrate from legacy settings.ini into the target AppSettings instance.
    /// </summary>
    /// <param name="legacyIniPath">Path to settings.ini.</param>
    /// <param name="settings">Target settings instance to populate.</param>
    /// <returns>True if migration occurred; otherwise false.</returns>
    public bool TryMigrate(string legacyIniPath, AppSettings settings)
    {
        if (!File.Exists(legacyIniPath))
        {
            return false;
        }

        try
        {
            var lines = File.ReadAllLines(legacyIniPath);
            var currentSection = string.Empty;

            foreach (var rawLine in lines)
            {
                var line = rawLine.Trim();
                if (string.IsNullOrEmpty(line) || line.StartsWith(';') || line.StartsWith('#'))
                {
                    continue;
                }

                if (line.StartsWith('[') && line.EndsWith(']'))
                {
                    currentSection = line[1..^1].Trim();
                    continue;
                }

                var separatorIndex = line.IndexOf('=');
                if (separatorIndex <= 0)
                {
                    continue;
                }

                var key = line[..separatorIndex].Trim();
                var value = line[(separatorIndex + 1)..].Trim();
                var fullKey = string.IsNullOrEmpty(currentSection) ? key : $"{currentSection}/{key}";

                ApplyLegacyKey(fullKey, value, settings);
            }

            Logger?.LogInformation("Successfully migrated legacy settings from {Path}", legacyIniPath);
            return true;
        }
        catch (Exception ex)
        {
            Logger?.LogWarning(ex, "Failed to migrate legacy settings from {Path}", legacyIniPath);
            return false;
        }
    }

    private static void ApplyLegacyKey(string key, string value, AppSettings settings)
    {
        switch (key)
        {
            case "PATHS/manual_cs2_path":
                if (!string.IsNullOrWhiteSpace(value))
                {
                    settings.Cs2PathOverride = value;
                }
                break;

            case "PATHS/archive":
            case "General/SelectedAddon":
            case "APP/SelectedAddon":
                if (!string.IsNullOrWhiteSpace(value))
                {
                    settings.SelectedAddon = value;
                }
                break;

            case "APP/theme_level":
                settings.Theme = value switch
                {
                    "1" => "Light",
                    "2" => "System",
                    _ => "Dark",
                };
                break;

            case "APP/minimize_to_tray":
                if (bool.TryParse(value, out var minimizeToTray))
                {
                    settings.Editor.MinimizeToTray = minimizeToTray;
                }
                break;

            case "LAUNCH/ncm_mode":
                if (bool.TryParse(value, out var ncmMode))
                {
                    settings.Editor.LaunchNcmMode = ncmMode;
                }
                break;

            case "SoundEventEditor/play_on_click":
                if (bool.TryParse(value, out var playOnClick))
                {
                    settings.Editor.SoundEventPlayOnClick = playOnClick;
                }
                break;
        }
    }
}
