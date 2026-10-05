namespace Hammer5Tools.App.Features.Shell;

using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.Features.Console;
using Hammer5Tools.App.Features.DetailProps;
using Hammer5Tools.App.Features.Hotkeys;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Commands;
using Hammer5Tools.Core.Compiler;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.Settings;
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
        private set => SetProperty(ref IsCs2RunningValue, value);
    }

    public IRelayCommand LaunchCs2Command { get; }

    public IRelayCommand KillCs2Command { get; }

    public IRelayCommand RestartCs2Command { get; }

    public IRelayCommand ClearVrad3CacheCommand { get; }

    public IRelayCommand OpenHotkeyEditorCommand { get; }

    public IRelayCommand OpenDetailPropEditorCommand { get; }

    public IRelayCommand OpenConsoleCommand { get; }

    public IRelayCommand<DocumentViewModel> CloseDocumentCommand { get; }

    public IRelayCommand SaveDocumentCommand { get; }

    public ShellViewModel(
        IAddonService addonService,
        ICs2Launcher cs2Launcher,
        ICs2Locator cs2Locator,
        ICommandService commandService,
        IResourceCompiler resourceCompiler,
        Vrad3CacheService vrad3CacheService,
        ISettingsService settingsService)
    {
        AddonService = addonService;
        Cs2Launcher = cs2Launcher;
        Cs2Locator = cs2Locator;
        CommandService = commandService;
        ResourceCompiler = resourceCompiler;
        Vrad3CacheService = vrad3CacheService;
        SettingsService = settingsService;

        LaunchCs2Command = new AsyncRelayCommand(OnLaunchCs2Async);
        KillCs2Command = new RelayCommand(OnKillCs2);
        RestartCs2Command = new AsyncRelayCommand(OnRestartCs2Async);
        ClearVrad3CacheCommand = new RelayCommand(OnClearVrad3Cache);
        OpenHotkeyEditorCommand = new RelayCommand(OpenHotkeyEditor);
        OpenDetailPropEditorCommand = new RelayCommand(OpenDetailPropEditor);
        OpenConsoleCommand = new RelayCommand(OpenConsole);
        CloseDocumentCommand = new RelayCommand<DocumentViewModel>(CloseDocument);
        SaveDocumentCommand = new RelayCommand(SaveCurrentDocument);

        AddonService.AddonsChanged += (_, _) => SyncAddons();
        AddonService.ActiveAddonChanged += (_, _) => OnPropertyChanged(nameof(SelectedAddon));
        Cs2Launcher.ProcessStateChanged += (_, running) => IsCs2Running = running;

        SyncAddons();

        // Default open the Hotkey and DetailProp editors so everything is directly usable
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
}
