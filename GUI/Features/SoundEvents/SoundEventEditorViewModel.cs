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
    private readonly ICs2Locator? Cs2Locator;
    internal ObservableCollection<SoundAudioRow> AddonAudioRows { get; } = [];
    private readonly ISoundEventService SoundEventService;
    private readonly Hammer5Tools.Core.Commands.ICommandService? CommandService;

    private readonly Hammer5Tools.Core.IO.SoundEvents.SoundPreview AudioPreview;
    private readonly Avalonia.Threading.DispatcherTimer AudioTimer;
    private string? ContentRoot;
    private readonly CancellationTokenSource AudioCancellation = new();
    public bool LoopAudio { get; set; }
    private string? SelectedSoundValue;
    public string? SelectedSound { get => SelectedSoundValue; set => SetProperty(ref SelectedSoundValue, value); }
    private double AudioPositionValue;
    public double AudioPosition
    {
        get => AudioPositionValue;
        set { if (SetProperty(ref AudioPositionValue, value)) AudioPreview.Seek((int)value, LoopAudio); }
    }
    public int AudioDuration => AudioPreview.Duration;
    public string AudioTime => $"{TimeSpan.FromMilliseconds(AudioPosition):mm\\:ss} : {TimeSpan.FromMilliseconds(AudioDuration):mm\\:ss}";
    public IRelayCommand PlayAudioCommand { get; }
    public IRelayCommand StopAudioCommand { get; }

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

    public ObservableCollection<SoundEvent> InternalEvents { get; } = [];
    public bool IsInternalEvent => SelectedEvent is not null && !Document.Events.Contains(SelectedEvent);

    public IRelayCommand SearchInternalEventsCommand => new AsyncRelayCommand(async () =>
    {
        try
        {
            var events = await SoundEventService.QueryInternalEventsAsync();
            InternalEvents.Clear();
            foreach (var item in events) InternalEvents.Add(item);
        }
        catch (Exception ex)
        {
            await DialogService.ShowErrorAsync($"Could not load built-in events: {ex.Message}");
        }
    });

    public IRelayCommand CopyInternalEventCommand => new RelayCommand(() =>
    {
        if (!IsInternalEvent || SelectedEvent is null) return;
        var copy = new SoundEvent(SelectedEvent.Name, SelectedEvent.Type) { HasExplicitType = SelectedEvent.HasExplicitType };
        foreach (var property in SelectedEvent.Properties) copy.Properties.Add(new SoundProperty(property.Key, property.Value));
        if (Document.Events.Any(item => item.Name == copy.Name)) return;
        Document.Events.Add(copy);
        ApplyFilter();
        SelectedEvent = copy;
        ObserveDocument();
        MarkDirty();
    });

    public ObservableCollection<string> VpkSounds { get; } = [];

    public SoundEvent? SelectedEvent
    {
        get => SelectedEventValue;
        set
        {
            if (SelectedEventValue is not null) SelectedEventValue.PropertyChanged -= SelectedEventChanged;
            if (SetProperty(ref SelectedEventValue, value))
            {
                OnPropertyChanged(nameof(PropertiesTitle));
                OnPropertyChanged(nameof(IsInternalEvent));
            }
            if (SelectedEventValue is not null) SelectedEventValue.PropertyChanged += SelectedEventChanged;
        }
    }

    private void SelectedEventChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e) => OnPropertyChanged(nameof(PropertiesTitle));

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

    public SoundEventEditorViewModel(IAddonService? addonService, ISoundEventService soundEventService, Services.IDialogService dialogService, string? filePath = null, ICs2Locator? cs2Locator = null, Hammer5Tools.Core.Commands.ICommandService? commandService = null)
    {
        AddonService = addonService;
        Cs2Locator = cs2Locator;
        CommandService = commandService;
        AudioPreview = new(cs2Locator);
        AudioTimer = new Avalonia.Threading.DispatcherTimer { Interval = TimeSpan.FromMilliseconds(200) };
        AudioTimer.Tick += (_, _) =>
        {
            SetProperty(ref AudioPositionValue, (double)AudioPreview.Position, nameof(AudioPosition));
            OnPropertyChanged(nameof(AudioTime));
            OnPropertyChanged(nameof(AudioDuration));
        };
        PlayAudioCommand = new AsyncRelayCommand(async () =>
        {
            if (SelectedSound is null) return;
            try
            {
                await AudioPreview.PlayAsync(SelectedSound, ContentRoot, LoopAudio, AudioCancellation.Token);
                if (AudioCancellation.IsCancellationRequested) return;
                AudioTimer.Start();
                OnPropertyChanged(nameof(AudioDuration));
            }
            catch (OperationCanceledException) { }
            catch (Exception ex)
            {
                await dialogService.ShowErrorAsync($"Could not preview sound: {ex.Message}");
            }
        });
        StopAudioCommand = new RelayCommand(() => { AudioTimer.Stop(); AudioPreview.Stop(); });
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
        Document = new SoundEventDocument();
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
                var initial = SoundEventService.CreateFromTemplate($"{addon.Name}.ambient_wind", Templates.FirstOrDefault() ?? "SoundGeneric");
                Document.Events.Add(initial);
            }
        }
        else
        {
            var initial = SoundEventService.CreateFromTemplate("example.sound", Templates.FirstOrDefault() ?? "SoundGeneric");
            Document.Events.Add(initial);
        }

        LoadAddonSounds();
        ApplyFilter();
        SelectedEvent = FilteredEvents.FirstOrDefault();
        InitializeHistory(() => Document.Serialize(), text =>
        {
            var selectedName = SelectedEvent?.Name;
            Document = SoundEventDocument.Parse(text);
            ApplyFilter();
            SelectedEvent = FilteredEvents.FirstOrDefault(item => item.Name == selectedName) ?? FilteredEvents.FirstOrDefault();
            ObserveDocument();
        });
        ObserveDocument();
    }

    private void LoadAddonSounds()
    {
        var install = Cs2Locator?.FindCs2Path();
        var fileAddon = install is not null && DocumentPath is not null ? Cs2Paths.GetContentAddonName(install, DocumentPath) : null;
        ContentRoot = fileAddon is not null ? Cs2Paths.GetAddonContentPath(install!, fileAddon) : AddonService?.ActiveAddon?.ContentPath;
        AddonSounds.Clear();
        AddonAudioRows.Clear();
        if (ContentRoot is null) return;
        foreach (var item in SoundEventService.GetAddonSounds(ContentRoot))
        {
            AddonSounds.Add(item.Path);
            AddonAudioRows.Add(new(item.Path, item.Size));
        }
    }

    public IRelayCommand OpenTemplatesCommand => new AsyncRelayCommand(async () =>
    {
        try { SoundEventService.OpenTemplateDirectory(); }
        catch (Exception ex) { await DialogService.ShowErrorAsync($"Could not open templates: {ex.Message}"); }
    });

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
        while (Document.Events.Any(item => item.Name == $"sound_event_{count}")) count++;
        var newEvent = new SoundEvent($"sound_event_{count}");
        Document.Events.Add(newEvent);
        ApplyFilter();
        SelectedEvent = newEvent;
        ObserveDocument();
        MarkDirty();
    }

    private void OnDeleteEvent()
    {
        if (SelectedEvent is null || IsInternalEvent)
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

        AddNamedProperty("volume");
    }

    private void OnDeleteProperty(SoundProperty? prop)
    {
        if (SelectedEvent is null || IsInternalEvent || prop is null)
        {
            return;
        }

        SelectedEvent.Properties.Remove(prop);
        ObserveDocument();
        MarkDirty();
        OnPropertyChanged(nameof(PropertiesTitle));
    }

    public string PropertiesTitle => SelectedEvent is { } item ? $"Properties: {item.Name}    |    {item.Properties.Count + (item.HasExplicitType ? 1 : 0)} properties" : "Properties";

    private string AudioFilterValue = string.Empty;
    public string AudioFilter
    {
        get => AudioFilterValue;
        set => SetProperty(ref AudioFilterValue, value);
    }

    public IRelayCommand LoadCommand => new AsyncRelayCommand(async () =>
    {
        if (!await DialogService.ConfirmCloseAsync([this])) return;
        var path = await DialogService.OpenFileAsync("Load sound events", "*.vsndevts");
        if (path is null) return;
        DocumentPath = path;
        await LoadDocumentSafelyAsync();
    });

    public IRelayCommand SaveTemplateCommand => new AsyncRelayCommand(async () =>
    {
        if (SelectedEvent is null) return;
        var path = await DialogService.SaveFileAsync("Save as Template", $"{SelectedEvent.Name}.kv3");
        if (path is null) return;
        try
        {
            await SoundEventService.SaveTemplateAsync(path, SelectedEvent);
            RefreshTemplates();
        }
        catch (Exception ex)
        {
            await DialogService.ShowErrorAsync($"Could not save template: {ex.Message}");
        }
    });

    public IRelayCommand PlayEventCommand => new AsyncRelayCommand(async () =>
    {
        if (SelectedEvent is not { } item) return;
        if (item.Name.IndexOfAny(['\n', '\r', ';', '"']) >= 0)
        {
            await DialogService.ShowErrorAsync("The event name contains console command characters.");
            return;
        }
        await SendGameCommandsAsync(["snd_sos_stop_all_soundevents", $"snd_sos_start_soundevent \"{item.Name}\""]);
    });

    public IRelayCommand StopEventCommand => new AsyncRelayCommand(() => SendGameCommandsAsync(["snd_sos_stop_all_soundevents"]));

    private async Task SendGameCommandsAsync(string[] commands)
    {
        if (CommandService is null || !await CommandService.SendCommandsAsync(commands))
        {
            await DialogService.ShowErrorAsync("Launch CS2 through Hammer 5 Tools to play sound events.");
        }
    }

    public void RefreshTemplates()
    {
        Templates.Clear();
        foreach (var name in SoundEventService.GetPredefinedTemplates()) Templates.Add(name);
    }

    public void AddNamedProperty(string key)
    {
        if (SelectedEvent is null || IsInternalEvent) return;
        var spec = SoundEventPresentation.Legacy.GetSpec(key);
        if (key == "type")
        {
            SelectedEvent.HasExplicitType = true;
            return;
        }
        if (key == "comment")
        {
            var suffix = 2;
            while (SelectedEvent.GetValue(key) is not null) key = $"comment_{suffix++}";
        }
        else if (SelectedEvent.GetValue(key) is not null) return;
        SelectedEvent.Properties.Add(new SoundProperty(key, spec.DefaultValue));
        ObserveDocument();
        MarkDirty();
        OnPropertyChanged(nameof(PropertiesTitle));
    }

    public async Task CreateFromTemplateAsync(string template)
    {
        try
        {
            var name = template;
            var suffix = 2;
            while (Document.Events.Any(item => item.Name == name)) name = $"{template}_{suffix++}";
            var item = SoundEventService.CreateFromTemplate(name, template);
            Document.Events.Add(item);
            SearchFilter = string.Empty;
            ApplyFilter();
            SelectedEvent = item;
            ObserveDocument();
            MarkDirty();
        }
        catch (Exception ex)
        {
            await DialogService.ShowErrorAsync($"Could not create event from template: {ex.Message}");
        }
    }

    public IRelayCommand RenameEventCommand => new AsyncRelayCommand(async () =>
    {
        if (SelectedEvent is null || IsInternalEvent) return;
        var name = await DialogService.PromptAsync("Rename sound event", "Event name");
        if (string.IsNullOrWhiteSpace(name)) return;
        if (Document.Events.Any(item => item != SelectedEvent && item.Name == name))
        {
            await DialogService.ShowErrorAsync("An event with that name already exists.");
            return;
        }
        SelectedEvent.Name = name;
    });

    public string CopySelectedEvent()
    {
        if (SelectedEvent is null) return string.Empty;
        var copy = new SoundEventDocument();
        copy.Events.Add(SelectedEvent);
        return copy.Serialize();
    }

    public void DuplicateSelectedEvent()
    {
        if (SelectedEvent is null) return;
        var copy = SoundEventDocument.Parse(CopySelectedEvent()).Events.Single();
        AddCopiedEvent(copy);
    }

    private void AddCopiedEvent(SoundEvent copy)
    {
        var original = copy.Name;
        var index = 2;
        while (Document.Events.Any(item => item.Name == copy.Name)) copy.Name = $"{original}_{index++}";
        Document.Events.Add(copy);
        ApplyFilter();
        SelectedEvent = copy;
        ObserveDocument();
        MarkDirty();
    }

    public async Task PasteEventsAsync(string text)
    {
        try
        {
            var source = text.Contains("<!-- kv3", StringComparison.Ordinal) ? text : SoundEventDocument.DefaultHeader + "\n{\n" + text + "\n}";
            var pasted = SoundEventDocument.ParseValidated(source);
            foreach (var item in pasted.Events) AddCopiedEvent(item);
        }
        catch (Exception ex)
        {
            await DialogService.ShowErrorAsync($"Could not paste sound events: {ex.Message}");
        }
    }

    public async Task PastePropertiesAsync(string text)
    {
        if (SelectedEvent is null || IsInternalEvent) return;
        try
        {
            var pasted = SoundEventDocument.ParseValidated(SoundEventDocument.DefaultHeader + "\n{ clipboard = {\n" + text + "\n} }").Events.Single();
            foreach (var item in pasted.Properties)
            {
                if (SelectedEvent.GetValue(item.Key) is null) SelectedEvent.Properties.Add(item);
            }
            ObserveDocument();
            MarkDirty();
        }
        catch (Exception ex)
        {
            await DialogService.ShowErrorAsync($"Could not paste properties: {ex.Message}");
        }
    }

    public IEnumerable<string> EventNames => Document.Events.Concat(InternalEvents).Select(item => item.Name).Distinct(StringComparer.Ordinal);

    public void RemoveProperty(SoundProperty property) => OnDeleteProperty(property);

    private async Task OnSearchVpkAsync()
    {
        VpkSounds.Clear();
        IReadOnlyList<string> sounds;
        try
        {
            sounds = await SoundEventService.QueryVpkSoundsAsync(AudioFilter);
        }
        catch (Exception ex)
        {
            await DialogService.ShowErrorAsync($"Could not search game sounds: {ex.Message}");
            return;
        }
        foreach (var s in sounds)
        {
            VpkSounds.Add(s);
        }
        OnPropertyChanged(nameof(VpkSounds));
    }

    public override void Dispose()
    {
        if (SelectedEvent is not null) SelectedEvent.PropertyChanged -= SelectedEventChanged;
        AudioCancellation.Cancel();
        AudioTimer.Stop();
        AudioPreview.Dispose();
        AudioCancellation.Dispose();
        base.Dispose();
        GC.SuppressFinalize(this);
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
