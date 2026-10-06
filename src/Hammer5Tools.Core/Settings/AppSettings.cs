namespace Hammer5Tools.Core.Settings;

/// <summary>
/// Root persistent application settings model.
/// </summary>
public class AppSettings
{
    public string? SelectedAddon { get; set; }

    public string? Cs2PathOverride { get; set; }

    public string Theme { get; set; } = "Standard";

    public string UpdateChannel { get; set; } = "stable";

    public Dictionary<string, string> WorkspaceLayouts { get; set; } = [];

    public string ArchivePath { get; set; } = string.Empty;

    public string? SelectedAddonPreset { get; set; }

    public List<MapBuilder.MapBuildConfiguration> MapBuildPresets { get; set; } = [];

    public WindowStateSettings WindowState { get; set; } = new();

    public EditorPreferences Editor { get; set; } = new();
}
