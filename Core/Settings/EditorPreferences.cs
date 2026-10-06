namespace Hammer5Tools.Core.Settings;

/// <summary>
/// General editor preferences.
/// </summary>
public class EditorPreferences
{
    public bool GenerateGitCommitMessages { get; set; } = true;

    public bool LoadingUseSavedCameras { get; set; } = true;

    public bool SmartPropDisplayIds { get; set; }

    public bool SmartPropHideExperimental { get; set; } = true;

    public bool SmartPropRoundVmapValues { get; set; }

    public int SmartPropRoundDecimals { get; set; } = 4;

    public int SmartPropMsaa { get; set; } = 4;

    public string AssetGroupMonitorPaths { get; set; } = "models, materials, smartprops";

    public bool AssetGroupAutoRefresh { get; set; } = true;

    public bool SoundEventPlayOnClick { get; set; } = true;

    public bool LaunchNcmMode { get; set; }

    public bool MinimizeToTray { get; set; }

    public string CustomLaunchArgs { get; set; } = "+install_dlc_workshoptools_cvar 1 +sv_steamauth_enforce 0";

    public Cs2.LaunchOptions LaunchOptions { get; set; } = new();
}
