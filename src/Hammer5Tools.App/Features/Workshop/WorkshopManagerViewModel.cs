namespace Hammer5Tools.App.Features.Workshop;

using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Workshop;

public class WorkshopManagerViewModel : DocumentViewModel
{
    private readonly IAddonService AddonService;
    private readonly IWorkshopManagerService WorkshopService;

    private string TitleValue = string.Empty;
    private string DescriptionValue = string.Empty;
    private bool ExcludeUnusedValue = true;
    private string StatusValue = "Ready";

    public ObservableCollection<string> PackageFiles { get; } = [];

    public string WorkshopTitle
    {
        get => TitleValue;
        set => SetProperty(ref TitleValue, value);
    }

    public string Description
    {
        get => DescriptionValue;
        set => SetProperty(ref DescriptionValue, value);
    }

    public bool ExcludeUnused
    {
        get => ExcludeUnusedValue;
        set => SetProperty(ref ExcludeUnusedValue, value);
    }

    public string Status
    {
        get => StatusValue;
        set => SetProperty(ref StatusValue, value);
    }

    public IRelayCommand RefreshFilesCommand { get; }

    public IRelayCommand BuildPackageCommand { get; }

    public WorkshopManagerViewModel(IAddonService addonService, IWorkshopManagerService workshopService)
    {
        AddonService = addonService;
        WorkshopService = workshopService;
        Title = "Workshop Manager";

        RefreshFilesCommand = new AsyncRelayCommand(OnRefreshFilesAsync);
        BuildPackageCommand = new AsyncRelayCommand(OnBuildPackageAsync);

        if (AddonService.ActiveAddon is not null)
        {
            WorkshopTitle = AddonService.ActiveAddon.Name;
        }

        _ = OnRefreshFilesAsync();
    }

    private async Task OnRefreshFilesAsync()
    {
        PackageFiles.Clear();
        var addon = AddonService.ActiveAddon;
        if (addon is null)
        {
            Status = "No active addon.";
            return;
        }

        Status = "Scanning addon files...";
        var files = await WorkshopService.AnalyzeAddonFilesAsync(addon.Name, ExcludeUnused);
        foreach (var f in files)
        {
            PackageFiles.Add(f);
        }

        Status = $"Found {PackageFiles.Count} file(s) ready for packaging.";
    }

    private async Task OnBuildPackageAsync()
    {
        var addon = AddonService.ActiveAddon;
        if (addon is null)
        {
            return;
        }

        Status = "Building VPK package...";
        var outVpk = Path.Combine(addon.GamePath, $"{addon.Name}.vpk");
        var config = new WorkshopPackConfig
        {
            AddonName = addon.Name,
            Title = WorkshopTitle,
            Description = Description,
            ExcludeUnusedContent = ExcludeUnused,
            OutputVpkPath = outVpk
        };

        var success = await WorkshopService.BuildWorkshopPackageAsync(config);
        Status = success ? $"VPK successfully prepared at {outVpk}" : "Packaging failed.";
    }
}
