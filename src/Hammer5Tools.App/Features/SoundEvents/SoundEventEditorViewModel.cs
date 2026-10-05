namespace Hammer5Tools.App.Features.SoundEvents;

using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.SoundEvents;

public class SoundEventEditorViewModel : DocumentViewModel
{
    public override string IconUri => "avares://Hammer5Tools.App/Assets/Icons/soundviewer.png";

    private readonly IAddonService AddonService;
    private readonly ISoundEventService SoundEventService;

    private SoundEventDocument Document = new();
    private SoundEvent? SelectedEventValue;
    private string SearchFilterValue = string.Empty;
    private string DocumentFilePath = string.Empty;

    public ObservableCollection<SoundEvent> FilteredEvents { get; } = [];

    public ObservableCollection<string> Templates { get; } = [];

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

    public SoundEventEditorViewModel(IAddonService addonService, ISoundEventService soundEventService)
    {
        AddonService = addonService;
        SoundEventService = soundEventService;
        Title = "SoundEvent Editor";

        AddEventCommand = new RelayCommand(OnAddEvent);
        DeleteEventCommand = new RelayCommand(OnDeleteEvent);
        AddPropertyCommand = new RelayCommand(OnAddProperty);
        DeletePropertyCommand = new RelayCommand<SoundProperty>(OnDeleteProperty);
        SearchVpkCommand = new AsyncRelayCommand(OnSearchVpkAsync);

        foreach (var t in SoundEventService.GetPredefinedTemplates())
        {
            Templates.Add(t);
        }

        _ = LoadInitialDocumentAsync();
    }

    private async Task LoadInitialDocumentAsync()
    {
        var addon = AddonService.ActiveAddon;
        if (addon is not null)
        {
            DocumentFilePath = Path.Combine(addon.ContentPath, "sounds", "soundevents_addon.vsndevts");
            if (File.Exists(DocumentFilePath))
            {
                Document = await SoundEventService.LoadDocumentAsync(DocumentFilePath);
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
        IsDirty = true;
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
        IsDirty = true;
    }

    private void OnAddProperty()
    {
        if (SelectedEvent is null)
        {
            return;
        }

        SelectedEvent.Properties.Add(new SoundProperty("param_name", "\"default\""));
        IsDirty = true;
    }

    private void OnDeleteProperty(SoundProperty? prop)
    {
        if (SelectedEvent is null || prop is null)
        {
            return;
        }

        SelectedEvent.Properties.Remove(prop);
        IsDirty = true;
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

    public override void Save()
    {
        if (!string.IsNullOrEmpty(DocumentFilePath))
        {
            _ = SoundEventService.SaveDocumentAsync(DocumentFilePath, Document);
            IsDirty = false;
        }
    }
}
