namespace Hammer5Tools.Core.Settings;

/// <summary>
/// Root persistent application settings model.
/// </summary>
public class AppSettings
{
    public string? SelectedAddon { get; set; }

    public string? Cs2PathOverride { get; set; }

    public string Theme { get; set; } = "Dark";

    public string UpdateChannel { get; set; } = "stable";

    public WindowStateSettings WindowState { get; set; } = new();

    public EditorPreferences Editor { get; set; } = new();
}
