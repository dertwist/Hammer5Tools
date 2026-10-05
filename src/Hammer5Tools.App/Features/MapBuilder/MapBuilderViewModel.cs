namespace Hammer5Tools.App.Features.MapBuilder;

using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.MapBuilder;

public class MapBuilderViewModel : DocumentViewModel
{
    private readonly IAddonService AddonService;
    private readonly IMapBuilderService MapBuilderService;

    private string MapNameValue = string.Empty;
    private MapBuildPreset SelectedPresetValue = MapBuildPreset.Standard;
    private bool ClearVradValue = true;
    private bool LaunchAfterBuildValue;
    private MapBuildJob? SelectedJobValue;

    public MapBuildPreset[] Presets { get; } = Enum.GetValues<MapBuildPreset>();

    public ObservableCollection<MapBuildJob> Jobs { get; } = [];

    public string MapName
    {
        get => MapNameValue;
        set => SetProperty(ref MapNameValue, value);
    }

    public MapBuildPreset SelectedPreset
    {
        get => SelectedPresetValue;
        set => SetProperty(ref SelectedPresetValue, value);
    }

    public bool ClearVrad
    {
        get => ClearVradValue;
        set => SetProperty(ref ClearVradValue, value);
    }

    public bool LaunchAfterBuild
    {
        get => LaunchAfterBuildValue;
        set => SetProperty(ref LaunchAfterBuildValue, value);
    }

    public MapBuildJob? SelectedJob
    {
        get => SelectedJobValue;
        set => SetProperty(ref SelectedJobValue, value);
    }

    public IRelayCommand StartBuildCommand { get; }

    public IRelayCommand CancelBuildCommand { get; }

    public MapBuilderViewModel(IAddonService addonService, IMapBuilderService mapBuilderService)
    {
        AddonService = addonService;
        MapBuilderService = mapBuilderService;
        Title = "Map Builder";

        StartBuildCommand = new AsyncRelayCommand(OnStartBuildAsync);
        CancelBuildCommand = new RelayCommand(OnCancelBuild);

        MapBuilderService.JobUpdated += OnJobUpdated;

        if (AddonService.ActiveAddon is not null)
        {
            MapName = AddonService.ActiveAddon.Name;
        }
    }

    private async Task OnStartBuildAsync()
    {
        var addon = AddonService.ActiveAddon;
        if (addon is null || string.IsNullOrWhiteSpace(MapName))
        {
            return;
        }

        var job = await MapBuilderService.EnqueueBuildAsync(addon.Name, MapName, SelectedPreset, ClearVrad, LaunchAfterBuild);
        SelectedJob = job;
    }

    private void OnCancelBuild()
    {
        if (SelectedJob is not null)
        {
            MapBuilderService.CancelJob(SelectedJob.Id);
        }
    }
    private void OnJobUpdated(object? sender, MapBuildJob job)
    {
        Avalonia.Threading.Dispatcher.UIThread.Post(() =>
        {
            var existing = Jobs.FirstOrDefault(item => item.Id == job.Id);
            if (existing is null)
            {
                Jobs.Insert(0, job);
            }
            else
            {
                var index = Jobs.IndexOf(existing);
                Jobs[index] = job;
            }

            OnPropertyChanged(nameof(SelectedJob));
        });
    }

    public override void Dispose()
    {
        MapBuilderService.JobUpdated -= OnJobUpdated;
        base.Dispose();
        GC.SuppressFinalize(this);
    }
}
