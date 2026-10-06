namespace Hammer5Tools.App.Features.SoundEvents;

using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.SoundEvents;

public class SoundEventEditorViewModel : DocumentViewModel
{
    public override string IconUri => "avares://Hammer5Tools/Assets/Icons/soundviewer.png";

    private readonly IAddonService? AddonService;
    private readonly ISoundEventService SoundEventService;

    private bool LoadSucceeded;

    private SoundEventDocument Document = new();
    private SoundEvent? SelectedEventValue;
    private string SearchFilterValue = string.Empty;
    private readonly Services.IDialogService DialogService;

    public Task Initialization { get; }

    public ObservableCollection<SoundEvent> FilteredEvents { get; } = [];

    public ObservableCollection<string> Templates { get; } = [];

    public ObservableCollection<string> AddonSounds { get; } = [];

    public IRelayCommand ReloadCommand { get; }

    public ObservableCollection<string> VpkSounds { get; } = [];

    public SoundEvent? SelectedEvent
    {
        get => SelectedEventValue;
        set => SetProperty(ref SelectedEventValue, value);
    }

    public string SearchFilter
    {
        get => SearchFilterValue;
        set
        {
            if (SetProperty(ref SearchFilterValue, value))
            {
                ApplyFilter();
            }
        }
    }

    public IRelayCommand AddEventCommand { get; }

    public IRelayCommand DeleteEventCommand { get; }

    public IRelayCommand AddPropertyCommand { get; }

    public IRelayCommand DeletePropertyCommand { get; }

    public IRelayCommand SearchVpkCommand { get; }

    public SoundEventEditorViewModel(IAddonService? addonService, ISoundEventService soundEventService, Services.IDialogService dialogService, string? filePath = null, ICs2Locator? cs2Locator = null)
    {
        AddonService = addonService;
        SoundEventService = soundEventService;
        DialogService = dialogService;
        ReportSaveFailure = dialogService.ShowErrorAsync;
        DocumentPath = filePath;
        Title = "SoundEvent Editor";

        AddEventCommand = new RelayCommand(OnAddEvent);
        DeleteEventCommand = new RelayCommand(OnDeleteEvent);
        AddPropertyCommand = new RelayCommand(OnAddProperty);
        DeletePropertyCommand = new RelayCommand<SoundProperty>(OnDeleteProperty);
        SearchVpkCommand = new AsyncRelayCommand(OnSearchVpkAsync);
        ReloadCommand = new AsyncRelayCommand(async () =>
        {
            if (await DialogService.ConfirmCloseAsync([this]))
            {
                await LoadDocumentSafelyAsync();
            }
        });
        var install = cs2Locator?.FindCs2Path();
        var fileAddon = install is not null && filePath is not null ? Cs2Paths.GetContentAddonName(install, filePath) : null;
        var contentPath = fileAddon is not null ? Cs2Paths.GetAddonContentPath(install!, fileAddon) : AddonService?.ActiveAddon?.ContentPath;
        if (contentPath is not null)
        {
            var soundsPath = Path.Combine(contentPath, "sounds");
            if (Directory.Exists(soundsPath))
            {
                foreach (var sound in Directory.EnumerateFiles(soundsPath, "*", SearchOption.AllDirectories)
                    .Where(path => Path.GetExtension(path).ToLowerInvariant() is ".wav" or ".mp3" or ".vsnd")
                    .OrderBy(path => path))
                {
                    AddonSounds.Add(Path.GetRelativePath(contentPath, sound));
                }
            }
        }

        foreach (var t in SoundEventService.GetPredefinedTemplates())
        {
            Templates.Add(t);
        }

        Initialization = LoadDocumentSafelyAsync();
    }

    private async Task LoadDocumentSafelyAsync()
    {
        LoadSucceeded = false;
        try
        {
            await LoadInitialDocumentAsync();
            LoadSucceeded = true;
        }
        catch (Exception ex)
        {
            await DialogService.ShowErrorAsync($"Could not load sound events: {ex.Message}");
        }
    }

    private async Task LoadInitialDocumentAsync()
    {
        var addon = AddonService?.ActiveAddon;
        if (DocumentPath is not null)
        {
            Document = await SoundEventService.LoadDocumentAsync(DocumentPath);
        }
        else if (addon is not null)
        {
            DocumentPath ??= Path.Combine(addon.ContentPath, "soundevents", "soundevents_addon.vsndevts");
            if (File.Exists(DocumentPath))
            {
                Document = await SoundEventService.LoadDocumentAsync(DocumentPath);
            }
            else
            {
                // Create sample event
                var initial = SoundEventService.CreateFromTemplate($"{addon.Name}.ambient_wind", Templates.First());
                Document.Events.Add(initial);
            }
        }
        else
        {
            var initial = SoundEventService.CreateFromTemplate("example.sound", Templates.First());
            Document.Events.Add(initial);
        }

        ApplyFilter();
        SelectedEvent = FilteredEvents.FirstOrDefault();
        InitializeHistory(() => Document.Serialize(), text =>
        {
            Document = SoundEventDocument.Parse(text);
            ApplyFilter();
            SelectedEvent = FilteredEvents.FirstOrDefault();
            ObserveDocument();
        });
        ObserveDocument();
    }

    private void ObserveDocument()
    {
        ObserveModels(Document.Events.Cast<System.ComponentModel.INotifyPropertyChanged>()
            .Concat(Document.Events.SelectMany(item => item.Properties)));
    }

    private void ApplyFilter()
    {
        FilteredEvents.Clear();
        foreach (var ev in Document.Events)
        {
            if (string.IsNullOrWhiteSpace(SearchFilter) ||
                ev.Name.Contains(SearchFilter, StringComparison.OrdinalIgnoreCase) ||
                ev.Type.Contains(SearchFilter, StringComparison.OrdinalIgnoreCase))
            {
                FilteredEvents.Add(ev);
            }
        }
    }

    private void OnAddEvent()
    {
        var count = Document.Events.Count + 1;
        var newEvent = SoundEventService.CreateFromTemplate($"sound_event_{count}", Templates.First());
        Document.Events.Add(newEvent);
        ApplyFilter();
        SelectedEvent = newEvent;
        ObserveDocument();
        MarkDirty();
    }

    private void OnDeleteEvent()
    {
        if (SelectedEvent is null)
        {
            return;
        }

        Document.Events.Remove(SelectedEvent);
        ApplyFilter();
        SelectedEvent = FilteredEvents.FirstOrDefault();
        ObserveDocument();
        MarkDirty();
    }

    private void OnAddProperty()
    {
        if (SelectedEvent is null)
        {
            return;
        }

        SelectedEvent.Properties.Add(new SoundProperty("param_name", "\"default\""));
        ObserveDocument();
        MarkDirty();
    }

    private void OnDeleteProperty(SoundProperty? prop)
    {
        if (SelectedEvent is null || prop is null)
        {
            return;
        }

        SelectedEvent.Properties.Remove(prop);
        ObserveDocument();
        MarkDirty();
    }

    private async Task OnSearchVpkAsync()
    {
        VpkSounds.Clear();
        var sounds = await SoundEventService.QueryVpkSoundsAsync(SearchFilter);
        foreach (var s in sounds)
        {
            VpkSounds.Add(s);
        }
    }

    protected override async Task<bool> SaveCoreAsync()
    {
        await Initialization;
        if (!LoadSucceeded)
        {
            throw new InvalidOperationException("Reload the sound-event file before saving; the original could not be read.");
        }

        DocumentPath ??= await DialogService.SaveFileAsync("Save sound events", "soundevents_addon.vsndevts");
        if (DocumentPath is null)
        {
            return false;
        }

        await SoundEventService.SaveDocumentAsync(DocumentPath, Document);
        return true;
    }
}
