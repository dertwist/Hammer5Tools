namespace Hammer5Tools.App.Features.NavMesh;

using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.NavMesh;

public class NavMeshRadarViewModel : DocumentViewModel
{
    public override string IconUri => "avares://Hammer5Tools/Assets/Icons/map_sm.png";

    private readonly IAddonService AddonService;
    private readonly INavMeshRadarService RadarService;

    private string MapNameValue = string.Empty;
    private int ResolutionValue = 1024;
    private float HeightMinValue = -500f;
    private float HeightMaxValue = 1000f;
    private bool CollapseNgonsValue = true;
    private string StatusValue = "Ready";

    public string VpkPath => AddonService.ActiveAddon is { } addon
        ? Path.Combine(addon.GamePath, "maps", $"{MapName}.vpk") : string.Empty;

    public string VmapPath => AddonService.ActiveAddon is { } addon
        ? Path.Combine(addon.ContentPath, "maps", $"{MapName}.vmap") : string.Empty;

    public string MapName
    {
        get => MapNameValue;
        set => SetProperty(ref MapNameValue, value);
    }

    public int Resolution
    {
        get => ResolutionValue;
        set => SetProperty(ref ResolutionValue, value);
    }

    public float HeightMin
    {
        get => HeightMinValue;
        set => SetProperty(ref HeightMinValue, value);
    }

    public float HeightMax
    {
        get => HeightMaxValue;
        set => SetProperty(ref HeightMaxValue, value);
    }

    public bool CollapseNgons
    {
        get => CollapseNgonsValue;
        set => SetProperty(ref CollapseNgonsValue, value);
    }

    public string Status
    {
        get => StatusValue;
        set => SetProperty(ref StatusValue, value);
    }

    public IRelayCommand GenerateRadarCommand { get; }

    public NavMeshRadarViewModel(IAddonService addonService, INavMeshRadarService radarService)
    {
        AddonService = addonService;
        RadarService = radarService;
        Title = "NavMesh Radar";

        GenerateRadarCommand = new AsyncRelayCommand(OnGenerateRadarAsync);

        if (AddonService.ActiveAddon is not null)
        {
            MapName = AddonService.ActiveAddon.Name;
        }
    }

    private async Task OnGenerateRadarAsync()
    {
        var addon = AddonService.ActiveAddon;
        if (addon is null || string.IsNullOrWhiteSpace(MapName))
        {
            Status = "Please select an addon and specify a map name.";
            return;
        }

        Status = "Generating radar...";
        var outPath = Path.Combine(addon.ContentPath, "panorama", "images", "overheadmaps", $"{MapName}_radar.png");

        var config = new NavMeshRadarConfig
        {
            AddonName = addon.Name,
            MapName = MapName,
            Resolution = Resolution,
            HeightMin = HeightMin,
            HeightMax = HeightMax,
            CollapseNgons = CollapseNgons,
            OutputPath = outPath
        };

        var success = await RadarService.GenerateRadarAsync(config);
        Status = success ? $"Radar metadata created at {outPath}" : "Failed to generate radar.";
    }
}
