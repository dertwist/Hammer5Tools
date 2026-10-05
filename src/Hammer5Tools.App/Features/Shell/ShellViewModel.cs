namespace Hammer5Tools.App.Features.Shell;

using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.Features.AssetTools;
using Hammer5Tools.App.Features.Console;
using Hammer5Tools.App.Features.DetailProps;
using Hammer5Tools.App.Features.Explorer;
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

public class ShellViewModel : ViewModelBase, IDisposable
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
    private readonly Services.IDialogService DialogService;

    private bool IsChangingDocuments;

    private DocumentViewModel? ActiveDocumentValue;
    private string StatusMessageValue = "Ready";
    private bool IsCs2RunningValue;

    public ObservableCollection<DocumentViewModel> Documents { get; } = [];

    public ObservableCollection<Addon> Addons { get; } = [];

    public AssetExplorerViewModel Explorer { get; }

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
                _ = SwitchAddonAsync(value);
            }
        }
    }

    public async Task<bool> SwitchAddonAsync(Addon addon)
    {
        if (IsChangingDocuments)
        {
            return false;
        }

        IsChangingDocuments = true;
        try
        {
            if (!await DialogService.ConfirmCloseAsync(Documents.ToArray()))
            {
                OnPropertyChanged(nameof(SelectedAddon));
                return false;
            }

            Controls.WorkspaceView.SaveAllLayouts();
            DialogService.CloseUtilities();
            Controls.WorkspaceView.CloseAllFloatingWindows();
            if (!AddonService.SetActiveAddon(addon.Name))
            {
                OnPropertyChanged(nameof(SelectedAddon));
                return false;
            }

            DisposeDocuments();
            OpenDefaultEditors();
            StatusMessage = $"Active addon: {addon.Name}";
            OnPropertyChanged(nameof(SelectedAddon));
            return true;
        }
        catch (Exception ex)
        {
            await DialogService.ShowErrorAsync(ex.Message);
            return false;
        }
        finally
        {
            IsChangingDocuments = false;
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

    public IRelayCommand OpenPreferencesCommand { get; }

    public IRelayCommand OpenFileCommand { get; }

    public IRelayCommand UndoDocumentCommand { get; }

    public IRelayCommand RedoDocumentCommand { get; }

    public IRelayCommand ResetLayoutCommand { get; }

    public IRelayCommand ExitCommand { get; }

    public event EventHandler? ExitRequested;

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
        IGitSyncService gitSyncService,
        Services.IDialogService dialogService)
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
        DialogService = dialogService;

        Explorer = new AssetExplorerViewModel(AddonService, OnOpenFileFromExplorer);

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

        CloseDocumentCommand = new AsyncRelayCommand<DocumentViewModel>(CloseDocumentAsync);
        SaveDocumentCommand = new AsyncRelayCommand(SaveCurrentDocumentAsync);
        OpenPreferencesCommand = new RelayCommand(OpenPreferences);
        OpenFileCommand = new AsyncRelayCommand(OpenFileAsync);
        UndoDocumentCommand = new RelayCommand(() => ActiveDocument?.Undo.Undo());
        RedoDocumentCommand = new RelayCommand(() => ActiveDocument?.Undo.Redo());
        ResetLayoutCommand = new RelayCommand(Controls.WorkspaceView.ResetAllLayouts);
        ExitCommand = new RelayCommand(() => ExitRequested?.Invoke(this, EventArgs.Empty));

        AddonService.AddonsChanged += OnAddonsChanged;
        AddonService.ActiveAddonChanged += OnActiveAddonChanged;
        Cs2Launcher.ProcessStateChanged += OnProcessStateChanged;

        SyncAddons();

        OpenDefaultEditors();
    }

    private void OpenDefaultEditors()
    {
        OpenLoadingEditor();
        OpenSoundEventEditor();
        OpenHotkeyEditor();
        OpenDetailPropEditor();
        ActiveDocument = Documents.FirstOrDefault();
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

        var editor = new HotkeyEditorViewModel(Cs2Locator, DialogService, Cs2Launcher);
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

        var editor = new DetailPropEditorViewModel(AddonService, DialogService);
        AddDocument(editor);
    }

    public void OpenConsole()
    {
        var console = new ConsoleViewModel(CommandService);
        DialogService.ShowUtility("Console", console, 880, 560);
    }

    public void OpenLoadingEditor()
    {
        var existing = Documents.OfType<LoadingEditorViewModel>().FirstOrDefault();
        if (existing is not null)
        {
            ActiveDocument = existing;
            return;
        }

        var editor = new LoadingEditorViewModel(AddonService, LoadingScreenService, DialogService);
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

        var editor = new SoundEventEditorViewModel(AddonService, SoundEventService, DialogService);
        AddDocument(editor);
    }

    public void OpenMapBuilder()
    {
        var builder = new MapBuilderViewModel(AddonService, MapBuilderService);
        DialogService.ShowUtility("Map Builder", builder, 1020, 700);
    }

    public void OpenNavMeshRadar()
    {
        var radar = new NavMeshRadarViewModel(AddonService, NavMeshRadarService);
        DialogService.ShowUtility("NavMesh Radar", radar, 920, 640);
    }

    public void OpenWorkshopManager()
    {
        var workshop = new WorkshopManagerViewModel(AddonService, WorkshopManagerService, DialogService);
        DialogService.ShowUtility("Workshop Manager", workshop, 960, 680);
    }

    public void OpenAssetTools()
    {
        var tools = new AssetToolsViewModel(AddonService, AssetToolsService);
        DialogService.ShowUtility("Asset Tools", tools, 900, 600);
    }

    public void OpenGitSync()
    {
        var sync = new GitSyncViewModel(AddonService, GitSyncService, SettingsService);
        DialogService.ShowUtility("Git Sync", sync, 920, 620);
    }

    private void AddDocument(DocumentViewModel doc)
    {
        doc.RequestClose += async (_, _) => await CloseDocumentAsync(doc);
        Documents.Add(doc);
        ActiveDocument = doc;
    }

    public async Task CloseDocumentAsync(DocumentViewModel? doc)
    {
        if (doc is null || IsChangingDocuments)
        {
            return;
        }

        IsChangingDocuments = true;
        try
        {
            if (!await DialogService.ConfirmCloseAsync([doc]))
            {
                return;
            }

            Controls.WorkspaceView.SaveAllLayouts();
            Documents.Remove(doc);
            doc.Dispose();
            if (ActiveDocument == doc)
            {
                ActiveDocument = Documents.LastOrDefault();
            }
        }
        finally
        {
            IsChangingDocuments = false;
        }
    }

    public async Task<bool> CanExitAsync()
    {
        return !IsChangingDocuments && await DialogService.ConfirmCloseAsync(Documents.ToArray());
    }

    private void DisposeDocuments()
    {
        foreach (var document in Documents)
        {
            document.Dispose();
        }

        Documents.Clear();
        ActiveDocument = null;
    }

    private async Task SaveCurrentDocumentAsync()
    {
        var document = ActiveDocument;
        if (document is null)
        {
            return;
        }

        try
        {
            if (await document.SaveAsync())
            {
                StatusMessage = $"Saved {document.Title}";
            }
        }
        catch (Exception ex)
        {
            StatusMessage = $"Save failed: {ex.Message}";
            await DialogService.ShowErrorAsync(ex.Message);
        }
    }

    private void OpenPreferences()
    {
        var preferences = new Preferences.PreferencesViewModel(SettingsService, DialogService);
        var pathChanged = false;
        preferences.BeforeApply = async () =>
        {
            pathChanged = preferences.Cs2Path != (SettingsService.Settings.Cs2PathOverride ?? string.Empty);
            return !pathChanged || await DialogService.ConfirmCloseAsync(Documents.ToArray());
        };
        preferences.Applied += (_, _) =>
        {
            if (pathChanged)
            {
                Controls.WorkspaceView.SaveAllLayouts();
                Cs2Locator.FindCs2Path();
                AddonService.RefreshAddons();
                DisposeDocuments();
                OpenDefaultEditors();
            }
        };
        DialogService.ShowUtility("Settings", preferences, 830, 600);
    }

    private async Task OpenFileAsync()
    {
        var path = await DialogService.OpenFileAsync("Open source document", "*");
        if (path is not null)
        {
            OnOpenFileFromExplorer(path);
        }
    }

    private void OnAddonsChanged(object? sender, IReadOnlyList<Addon> addons)
    {
        Avalonia.Threading.Dispatcher.UIThread.Post(SyncAddons);
    }

    private void OnActiveAddonChanged(object? sender, Addon? addon)
    {
        Avalonia.Threading.Dispatcher.UIThread.Post(() => OnPropertyChanged(nameof(SelectedAddon)));
    }

    private void OnProcessStateChanged(object? sender, bool running)
    {
        Avalonia.Threading.Dispatcher.UIThread.Post(() => IsCs2Running = running);
        if (!running)
        {
            CommandService.Stop();
        }
    }

    private async Task OnLaunchCs2Async()
    {
        StatusMessage = "Launching Counter-Strike 2 Workshop Tools...";
        CommandService.Start();
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

    public void OnOpenFileFromExplorer(string filePath)
    {
        try
        {
            var fullPath = Path.GetFullPath(filePath);
            var existing = Documents.FirstOrDefault(document => string.Equals(document.DocumentPath, fullPath, StringComparison.OrdinalIgnoreCase));
            if (existing is not null)
            {
                ActiveDocument = existing;
                return;
            }

            var extension = Path.GetExtension(fullPath).ToLowerInvariant();
            DocumentViewModel? document = extension switch
            {
                ".vsndevts" => new SoundEventEditorViewModel(AddonService, SoundEventService, DialogService, fullPath),
                ".vdata" when Path.GetFileName(fullPath).Equals("detail_prop_types.vdata", StringComparison.OrdinalIgnoreCase)
                    => new DetailPropEditorViewModel(AddonService, DialogService, fullPath),
                ".txt" when Path.GetFileName(fullPath).StartsWith("keybindings", StringComparison.OrdinalIgnoreCase)
                    => new HotkeyEditorViewModel(Cs2Locator, DialogService, Cs2Launcher, fullPath),
                _ => null,
            };
            if (document is not null)
            {
                AddDocument(document);
            }
            else
            {
                Process.Start(new ProcessStartInfo { FileName = fullPath, UseShellExecute = true });
            }

            StatusMessage = $"Opened {Path.GetFileName(fullPath)}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Failed to open file: {ex.Message}";
        }
    }

    public void Dispose()
    {
        AddonService.AddonsChanged -= OnAddonsChanged;
        AddonService.ActiveAddonChanged -= OnActiveAddonChanged;
        Cs2Launcher.ProcessStateChanged -= OnProcessStateChanged;
        DialogService.CloseUtilities();
        Controls.WorkspaceView.CloseAllFloatingWindows();
        Explorer.Dispose();
        DisposeDocuments();
        GC.SuppressFinalize(this);
    }
}
