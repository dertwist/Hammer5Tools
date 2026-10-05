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
    private readonly Services.IDialogService DialogService;

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

    public WorkshopManagerViewModel(IAddonService addonService, IWorkshopManagerService workshopService, Services.IDialogService dialogService)
    {
        AddonService = addonService;
        WorkshopService = workshopService;
        DialogService = dialogService;
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
        IReadOnlyList<string> files;
        try
        {
            files = await WorkshopService.AnalyzeAddonFilesAsync(addon.Name, ExcludeUnused);
        }
        catch (Exception ex)
        {
            Status = $"Cannot scan addon: {ex.Message}";
            return;
        }
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
        var outVpk = await DialogService.SaveFileAsync("Save Workshop package", $"{addon.Name}_dir.vpk");
        if (outVpk is null)
        {
            Status = "Packaging cancelled";
            return;
        }
        var config = new WorkshopPackConfig
        {
            AddonName = addon.Name,
            Title = WorkshopTitle,
            Description = Description,
            ExcludeUnusedContent = ExcludeUnused,
            OutputVpkPath = outVpk
        };

        try
        {
            var success = await WorkshopService.BuildWorkshopPackageAsync(config);
            Status = success ? $"Package written to {outVpk} and its numbered chunks" : "Packaging failed";
        }
        catch (Exception ex)
        {
            Status = $"Packaging failed: {ex.Message}";
        }
    }
}
