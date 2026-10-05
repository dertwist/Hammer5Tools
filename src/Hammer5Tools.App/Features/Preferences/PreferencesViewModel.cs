namespace Hammer5Tools.App.Features.Preferences;

using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.Services;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Settings;

public class PreferencesViewModel : ViewModelBase
{
    private readonly ISettingsService SettingsService;
    private readonly IDialogService DialogService;
    public string[] Themes { get; } = ["System", "Standard", "Bright", "Vintage Steam"];
    public string[] UpdateChannels { get; } = ["stable", "dev"];
    public IRelayCommand ApplyCommand { get; }
    public IRelayCommand BrowseCs2Command { get; }
    public IRelayCommand BrowseArchiveCommand { get; }
    public IRelayCommand ResetLayoutCommand { get; }
    public event EventHandler? Applied;

    public Func<Task<bool>>? BeforeApply { get; set; }

    private string Cs2PathValue = string.Empty;

    public string Cs2Path
    {
        get => Cs2PathValue;
        set => SetProperty(ref Cs2PathValue, value);
    }

    private string ArchivePathValue = string.Empty;

    public string ArchivePath
    {
        get => ArchivePathValue;
        set => SetProperty(ref ArchivePathValue, value);
    }

    private string ThemeValue = string.Empty;

    public string Theme
    {
        get => ThemeValue;
        set => SetProperty(ref ThemeValue, value);
    }

    private string UpdateChannelValue = string.Empty;

    public string UpdateChannel
    {
        get => UpdateChannelValue;
        set => SetProperty(ref UpdateChannelValue, value);
    }

    private string CustomLaunchArgsValue = string.Empty;

    public string CustomLaunchArgs
    {
        get => CustomLaunchArgsValue;
        set => SetProperty(ref CustomLaunchArgsValue, value);
    }

    private bool LaunchNcmModeValue;

    public bool LaunchNcmMode
    {
        get => LaunchNcmModeValue;
        set => SetProperty(ref LaunchNcmModeValue, value);
    }

    private bool MinimizeToTrayValue;

    public bool MinimizeToTray
    {
        get => MinimizeToTrayValue;
        set => SetProperty(ref MinimizeToTrayValue, value);
    }

    private bool GenerateGitCommitMessagesValue;

    public bool GenerateGitCommitMessages
    {
        get => GenerateGitCommitMessagesValue;
        set => SetProperty(ref GenerateGitCommitMessagesValue, value);
    }

    private bool LoadingUseSavedCamerasValue;

    public bool LoadingUseSavedCameras
    {
        get => LoadingUseSavedCamerasValue;
        set => SetProperty(ref LoadingUseSavedCamerasValue, value);
    }

    private bool SoundEventPlayOnClickValue;

    public bool SoundEventPlayOnClick
    {
        get => SoundEventPlayOnClickValue;
        set => SetProperty(ref SoundEventPlayOnClickValue, value);
    }

    private bool SmartPropDisplayIdsValue;

    public bool SmartPropDisplayIds
    {
        get => SmartPropDisplayIdsValue;
        set => SetProperty(ref SmartPropDisplayIdsValue, value);
    }

    private bool SmartPropHideExperimentalValue;

    public bool SmartPropHideExperimental
    {
        get => SmartPropHideExperimentalValue;
        set => SetProperty(ref SmartPropHideExperimentalValue, value);
    }

    private bool SmartPropRoundVmapValuesValue;

    public bool SmartPropRoundVmapValues
    {
        get => SmartPropRoundVmapValuesValue;
        set => SetProperty(ref SmartPropRoundVmapValuesValue, value);
    }

    private int SmartPropRoundDecimalsValue;

    public int SmartPropRoundDecimals
    {
        get => SmartPropRoundDecimalsValue;
        set => SetProperty(ref SmartPropRoundDecimalsValue, value);
    }

    private int SmartPropMsaaValue;

    public int SmartPropMsaa
    {
        get => SmartPropMsaaValue;
        set => SetProperty(ref SmartPropMsaaValue, value);
    }

    private string AssetGroupMonitorPathsValue = string.Empty;

    public string AssetGroupMonitorPaths
    {
        get => AssetGroupMonitorPathsValue;
        set => SetProperty(ref AssetGroupMonitorPathsValue, value);
    }

    private bool AssetGroupAutoRefreshValue;

    public bool AssetGroupAutoRefresh
    {
        get => AssetGroupAutoRefreshValue;
        set => SetProperty(ref AssetGroupAutoRefreshValue, value);
    }

    public PreferencesViewModel(ISettingsService settingsService, IDialogService dialogService)
    {
        SettingsService = settingsService;
        DialogService = dialogService;
        var settings = settingsService.Settings;
        Cs2Path = settings.Cs2PathOverride ?? string.Empty;
        ArchivePath = settings.ArchivePath;
        Theme = settings.Theme == "Dark" ? "Standard" : settings.Theme;
        UpdateChannel = settings.UpdateChannel;
        CustomLaunchArgs = settings.Editor.CustomLaunchArgs;
        LaunchNcmMode = settings.Editor.LaunchNcmMode;
        MinimizeToTray = settings.Editor.MinimizeToTray;
        GenerateGitCommitMessages = settings.Editor.GenerateGitCommitMessages;
        LoadingUseSavedCameras = settings.Editor.LoadingUseSavedCameras;
        SoundEventPlayOnClick = settings.Editor.SoundEventPlayOnClick;
        SmartPropDisplayIds = settings.Editor.SmartPropDisplayIds;
        SmartPropHideExperimental = settings.Editor.SmartPropHideExperimental;
        SmartPropRoundVmapValues = settings.Editor.SmartPropRoundVmapValues;
        SmartPropRoundDecimals = settings.Editor.SmartPropRoundDecimals;
        SmartPropMsaa = settings.Editor.SmartPropMsaa;
        AssetGroupAutoRefresh = settings.Editor.AssetGroupAutoRefresh;
        AssetGroupMonitorPaths = settings.Editor.AssetGroupMonitorPaths;
        ApplyCommand = new AsyncRelayCommand(ApplyAsync);
        BrowseCs2Command = new AsyncRelayCommand(async () => Cs2Path = await DialogService.PickFolderAsync("CS2 installation") ?? Cs2Path);
        BrowseArchiveCommand = new AsyncRelayCommand(async () => ArchivePath = await DialogService.PickFolderAsync("Archive folder") ?? ArchivePath);
        ResetLayoutCommand = new RelayCommand(Controls.WorkspaceView.ResetAllLayouts);
    }

    private async Task ApplyAsync()
    {
        if (!string.IsNullOrWhiteSpace(Cs2Path) && !Core.Cs2.Cs2Paths.IsValidCs2Path(Cs2Path))
        {
            await DialogService.ShowErrorAsync("Select the Counter-Strike Global Offensive installation folder containing game and content.");
            return;
        }

        if (BeforeApply is not null && !await BeforeApply())
        {
            return;
        }

        SettingsService.Update(settings =>
        {
            settings.Cs2PathOverride = Cs2Path == string.Empty ? null : Cs2Path;
            settings.ArchivePath = ArchivePath;
            settings.Theme = Theme;
            settings.UpdateChannel = UpdateChannel;
            settings.Editor.CustomLaunchArgs = CustomLaunchArgs;
            settings.Editor.LaunchNcmMode = LaunchNcmMode;
            settings.Editor.MinimizeToTray = MinimizeToTray;
            settings.Editor.GenerateGitCommitMessages = GenerateGitCommitMessages;
            settings.Editor.LoadingUseSavedCameras = LoadingUseSavedCameras;
            settings.Editor.SoundEventPlayOnClick = SoundEventPlayOnClick;
            settings.Editor.SmartPropDisplayIds = SmartPropDisplayIds;
            settings.Editor.SmartPropHideExperimental = SmartPropHideExperimental;
            settings.Editor.SmartPropRoundVmapValues = SmartPropRoundVmapValues;
            settings.Editor.SmartPropRoundDecimals = SmartPropRoundDecimals;
            settings.Editor.SmartPropMsaa = SmartPropMsaa;
            settings.Editor.AssetGroupAutoRefresh = AssetGroupAutoRefresh;
            settings.Editor.AssetGroupMonitorPaths = AssetGroupMonitorPaths;
        });
        Styles.ThemeService.Apply(Theme);
        Applied?.Invoke(this, EventArgs.Empty);
    }
}
