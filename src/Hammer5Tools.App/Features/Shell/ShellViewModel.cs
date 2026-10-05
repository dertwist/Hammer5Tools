namespace Hammer5Tools.App.Features.Shell;

using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.Features.AssetTools;
using Hammer5Tools.App.Features.Console;
using Hammer5Tools.App.Features.DetailProps;
using Hammer5Tools.App.Features.GitSync;
using Hammer5Tools.App.Features.Hotkeys;
using Hammer5Tools.App.Features.LoadingScreens;
using Hammer5Tools.App.Features.MapBuilder;
using Hammer5Tools.App.Features.NavMesh;
using Hammer5Tools.App.Features.SoundEvents;
using Hammer5Tools.App.Features.Workshop;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Commands;
using Hammer5Tools.Core.Compiler;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.GitSync;
using Hammer5Tools.Core.LoadingScreens;
using Hammer5Tools.Core.MapBuilder;
using Hammer5Tools.Core.NavMesh;
using Hammer5Tools.Core.Settings;
using Hammer5Tools.Core.SoundEvents;
using Hammer5Tools.Core.Workshop;
using Hammer5Tools.Infrastructure.Cs2;

public class ShellViewModel : ViewModelBase
{
    private readonly IAddonService AddonService;
    private readonly ICs2Launcher Cs2Launcher;
    private readonly ICs2Locator Cs2Locator;
    private readonly ICommandService CommandService;
    private readonly IResourceCompiler ResourceCompiler;
    private readonly Vrad3CacheService Vrad3CacheService;
    private readonly ISettingsService SettingsService;

    private readonly ILoadingScreenService LoadingScreenService;
    private readonly ISoundEventService SoundEventService;
    private readonly IMapBuilderService MapBuilderService;
    private readonly INavMeshRadarService NavMeshRadarService;
    private readonly IWorkshopManagerService WorkshopManagerService;
    private readonly IAssetToolsService AssetToolsService;
    private readonly IGitSyncService GitSyncService;

    private DocumentViewModel? ActiveDocumentValue;
    private string StatusMessageValue = "Ready";
    private bool IsCs2RunningValue;

    public ObservableCollection<DocumentViewModel> Documents { get; } = [];

    public ObservableCollection<Addon> Addons { get; } = [];

    public DocumentViewModel? ActiveDocument
    {
        get => ActiveDocumentValue;
        set => SetProperty(ref ActiveDocumentValue, value);
    }

    public Addon? SelectedAddon
    {
        get => AddonService.ActiveAddon;
        set
        {
            if (value is not null && AddonService.ActiveAddon?.Name != value.Name)
            {
                AddonService.SetActiveAddon(value.Name);
                OnPropertyChanged(nameof(SelectedAddon));
                StatusMessage = $"Active addon: {value.Name}";
            }
        }
    }

    public string StatusMessage
    {
        get => StatusMessageValue;
        set => SetProperty(ref StatusMessageValue, value);
    }

    public bool IsCs2Running
    {
        get => IsCs2RunningValue;
        private set
        {
            if (SetProperty(ref IsCs2RunningValue, value))
            {
                OnPropertyChanged(nameof(Cs2StatusText));
                OnPropertyChanged(nameof(Cs2StatusColor));
            }
        }
    }

    public string Cs2StatusText => IsCs2Running ? "CS2: Running" : "CS2: Stopped";

    public string Cs2StatusColor => IsCs2Running ? "#5ab55e" : "#797979";

    public IRelayCommand LaunchCs2Command { get; }

    public IRelayCommand KillCs2Command { get; }

    public IRelayCommand RestartCs2Command { get; }

    public IRelayCommand ClearVrad3CacheCommand { get; }

    public IRelayCommand OpenHotkeyEditorCommand { get; }

    public IRelayCommand OpenDetailPropEditorCommand { get; }

    public IRelayCommand OpenConsoleCommand { get; }

    public IRelayCommand OpenLoadingEditorCommand { get; }

    public IRelayCommand OpenSoundEventEditorCommand { get; }

    public IRelayCommand OpenMapBuilderCommand { get; }

    public IRelayCommand OpenNavMeshRadarCommand { get; }

    public IRelayCommand OpenWorkshopManagerCommand { get; }

    public IRelayCommand OpenAssetToolsCommand { get; }

    public IRelayCommand OpenGitSyncCommand { get; }

    public IRelayCommand OpenContentFolderCommand { get; }

    public IRelayCommand OpenGameFolderCommand { get; }

    public IRelayCommand RefreshAddonsCommand { get; }

    public IRelayCommand<string> OpenUrlCommand { get; }

    public IRelayCommand<DocumentViewModel> CloseDocumentCommand { get; }

    public IRelayCommand SaveDocumentCommand { get; }

    public ShellViewModel(
        IAddonService addonService,
        ICs2Launcher cs2Launcher,
        ICs2Locator cs2Locator,
        ICommandService commandService,
        IResourceCompiler resourceCompiler,
        Vrad3CacheService vrad3CacheService,
        ISettingsService settingsService,
        ILoadingScreenService loadingScreenService,
        ISoundEventService soundEventService,
        IMapBuilderService mapBuilderService,
        INavMeshRadarService navMeshRadarService,
        IWorkshopManagerService workshopManagerService,
        IAssetToolsService assetToolsService,
        IGitSyncService gitSyncService)
    {
        AddonService = addonService;
        Cs2Launcher = cs2Launcher;
        Cs2Locator = cs2Locator;
        CommandService = commandService;
        ResourceCompiler = resourceCompiler;
        Vrad3CacheService = vrad3CacheService;
        SettingsService = settingsService;

        LoadingScreenService = loadingScreenService;
        SoundEventService = soundEventService;
        MapBuilderService = mapBuilderService;
        NavMeshRadarService = navMeshRadarService;
        WorkshopManagerService = workshopManagerService;
        AssetToolsService = assetToolsService;
        GitSyncService = gitSyncService;

        LaunchCs2Command = new AsyncRelayCommand(OnLaunchCs2Async);
        KillCs2Command = new RelayCommand(OnKillCs2);
        RestartCs2Command = new AsyncRelayCommand(OnRestartCs2Async);
        ClearVrad3CacheCommand = new RelayCommand(OnClearVrad3Cache);
        OpenHotkeyEditorCommand = new RelayCommand(OpenHotkeyEditor);
        OpenDetailPropEditorCommand = new RelayCommand(OpenDetailPropEditor);
        OpenConsoleCommand = new RelayCommand(OpenConsole);
        OpenLoadingEditorCommand = new RelayCommand(OpenLoadingEditor);
        OpenSoundEventEditorCommand = new RelayCommand(OpenSoundEventEditor);
        OpenMapBuilderCommand = new RelayCommand(OpenMapBuilder);
        OpenNavMeshRadarCommand = new RelayCommand(OpenNavMeshRadar);
        OpenWorkshopManagerCommand = new RelayCommand(OpenWorkshopManager);
        OpenAssetToolsCommand = new RelayCommand(OpenAssetTools);
        OpenGitSyncCommand = new RelayCommand(OpenGitSync);

        OpenContentFolderCommand = new RelayCommand(OnOpenContentFolder);
        OpenGameFolderCommand = new RelayCommand(OnOpenGameFolder);
        RefreshAddonsCommand = new RelayCommand(OnRefreshAddons);
        OpenUrlCommand = new RelayCommand<string>(OnOpenUrl);

        CloseDocumentCommand = new RelayCommand<DocumentViewModel>(CloseDocument);
        SaveDocumentCommand = new RelayCommand(SaveCurrentDocument);

        AddonService.AddonsChanged += (_, _) => SyncAddons();
        AddonService.ActiveAddonChanged += (_, _) => OnPropertyChanged(nameof(SelectedAddon));
        Cs2Launcher.ProcessStateChanged += (_, running) => IsCs2Running = running;

        SyncAddons();

        // Default open the primary Hotkey and DetailProp editors
        OpenHotkeyEditor();
        OpenDetailPropEditor();
    }

    private void SyncAddons()
    {
        Addons.Clear();
        foreach (var addon in AddonService.Addons)
        {
            Addons.Add(addon);
        }

        OnPropertyChanged(nameof(SelectedAddon));
    }

    public void OpenHotkeyEditor()
    {
        var existing = Documents.OfType<HotkeyEditorViewModel>().FirstOrDefault();
        if (existing is not null)
        {
            ActiveDocument = existing;
            return;
        }

        var editor = new HotkeyEditorViewModel(Cs2Locator);
        AddDocument(editor);
    }

    public void OpenDetailPropEditor()
    {
        var existing = Documents.OfType<DetailPropEditorViewModel>().FirstOrDefault();
        if (existing is not null)
        {
            ActiveDocument = existing;
            return;
        }

        var editor = new DetailPropEditorViewModel(AddonService);
        AddDocument(editor);
    }

    public void OpenConsole()
    {
        var existing = Documents.OfType<ConsoleViewModel>().FirstOrDefault();
        if (existing is not null)
        {
            ActiveDocument = existing;
            return;
        }

        var console = new ConsoleViewModel(CommandService);
        AddDocument(console);
    }

    public void OpenLoadingEditor()
    {
        var existing = Documents.OfType<LoadingEditorViewModel>().FirstOrDefault();
        if (existing is not null)
        {
            ActiveDocument = existing;
            return;
        }

        var editor = new LoadingEditorViewModel(AddonService, LoadingScreenService);
        AddDocument(editor);
    }

    public void OpenSoundEventEditor()
    {
        var existing = Documents.OfType<SoundEventEditorViewModel>().FirstOrDefault();
        if (existing is not null)
        {
            ActiveDocument = existing;
            return;
        }

        var editor = new SoundEventEditorViewModel(AddonService, SoundEventService);
        AddDocument(editor);
    }

    public void OpenMapBuilder()
    {
        var existing = Documents.OfType<MapBuilderViewModel>().FirstOrDefault();
        if (existing is not null)
        {
            ActiveDocument = existing;
            return;
        }

        var builder = new MapBuilderViewModel(AddonService, MapBuilderService);
        AddDocument(builder);
    }

    public void OpenNavMeshRadar()
    {
        var existing = Documents.OfType<NavMeshRadarViewModel>().FirstOrDefault();
        if (existing is not null)
        {
            ActiveDocument = existing;
            return;
        }

        var radar = new NavMeshRadarViewModel(AddonService, NavMeshRadarService);
        AddDocument(radar);
    }

    public void OpenWorkshopManager()
    {
        var existing = Documents.OfType<WorkshopManagerViewModel>().FirstOrDefault();
        if (existing is not null)
        {
            ActiveDocument = existing;
            return;
        }

        var workshop = new WorkshopManagerViewModel(AddonService, WorkshopManagerService);
        AddDocument(workshop);
    }

    public void OpenAssetTools()
    {
        var existing = Documents.OfType<AssetToolsViewModel>().FirstOrDefault();
        if (existing is not null)
        {
            ActiveDocument = existing;
            return;
        }

        var tools = new AssetToolsViewModel(AddonService, AssetToolsService);
        AddDocument(tools);
    }

    public void OpenGitSync()
    {
        var existing = Documents.OfType<GitSyncViewModel>().FirstOrDefault();
        if (existing is not null)
        {
            ActiveDocument = existing;
            return;
        }

        var sync = new GitSyncViewModel(AddonService, GitSyncService);
        AddDocument(sync);
    }

    private void AddDocument(DocumentViewModel doc)
    {
        doc.RequestClose += (_, _) => CloseDocument(doc);
        Documents.Add(doc);
        ActiveDocument = doc;
    }

    private void CloseDocument(DocumentViewModel? doc)
    {
        if (doc is null)
        {
            return;
        }

        Documents.Remove(doc);
        if (ActiveDocument == doc)
        {
            ActiveDocument = Documents.LastOrDefault();
        }
    }

    private void SaveCurrentDocument()
    {
        ActiveDocument?.Save();
        StatusMessage = $"Saved {ActiveDocument?.Title}";
    }

    private async Task OnLaunchCs2Async()
    {
        StatusMessage = "Launching Counter-Strike 2 Workshop Tools...";
        var success = await Cs2Launcher.LaunchAsync();
        StatusMessage = success ? "CS2 running" : "Failed to launch CS2";
    }

    private void OnKillCs2()
    {
        Cs2Launcher.Kill();
        StatusMessage = "CS2 terminated";
    }

    private async Task OnRestartCs2Async()
    {
        StatusMessage = "Restarting CS2...";
        var success = await Cs2Launcher.RestartAsync();
        StatusMessage = success ? "CS2 restarted" : "Failed to restart CS2";
    }

    private void OnClearVrad3Cache()
    {
        var cleared = Vrad3CacheService.ClearCache(SelectedAddon?.Name);
        StatusMessage = $"Cleared {cleared} VRAD3 cache file(s).";
    }

    private void OnOpenContentFolder()
    {
        if (SelectedAddon is not null && Directory.Exists(SelectedAddon.ContentPath))
        {
            OpenFolder(SelectedAddon.ContentPath);
        }
        else
        {
            StatusMessage = "No content folder found for selected addon";
        }
    }

    private void OnOpenGameFolder()
    {
        if (SelectedAddon is not null && Directory.Exists(SelectedAddon.GamePath))
        {
            OpenFolder(SelectedAddon.GamePath);
        }
        else
        {
            StatusMessage = "No game folder found for selected addon";
        }
    }

    private void OnRefreshAddons()
    {
        AddonService.RefreshAddons();
        SyncAddons();
        StatusMessage = $"Refreshed addons ({Addons.Count} discovered)";
    }

    private void OnOpenUrl(string? url)
    {
        if (!string.IsNullOrWhiteSpace(url))
        {
            try
            {
                Process.Start(new ProcessStartInfo { FileName = url, UseShellExecute = true });
            }
            catch
            {
                // Ignore failure
            }
        }
    }

    private void OpenFolder(string path)
    {
        try
        {
            Process.Start(new ProcessStartInfo { FileName = path, UseShellExecute = true });
            StatusMessage = $"Opened {Path.GetFileName(path)}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Failed to open directory: {ex.Message}";
        }
    }
}
