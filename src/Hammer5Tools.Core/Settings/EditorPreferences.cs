namespace Hammer5Tools.Core.Settings;

/// <summary>
/// General editor preferences.
/// </summary>
public class EditorPreferences
{
    public bool SoundEventPlayOnClick { get; set; } = true;

    public bool LaunchNcmMode { get; set; }

    public bool MinimizeToTray { get; set; }

    public string CustomLaunchArgs { get; set; } = "-tools";
}
