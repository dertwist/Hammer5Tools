namespace Hammer5Tools.App.Features.LoadingScreens;

using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.LoadingScreens;

public class LoadingEditorViewModel : DocumentViewModel
{
    private readonly IAddonService AddonService;
    private readonly ILoadingScreenService LoadingScreenService;

    private string TitleValue = string.Empty;
    private string AuthorValue = string.Empty;
    private string DescriptionValue = string.Empty;
    private string SelectedImagePathValue = string.Empty;
    private CameraInfo? SelectedCameraValue;

    public ObservableCollection<CameraInfo> Cameras { get; } = [];

    public string MapTitle
    {
        get => TitleValue;
        set
        {
            if (SetProperty(ref TitleValue, value))
            {
                IsDirty = true;
            }
        }
    }

    public string Author
    {
        get => AuthorValue;
        set
        {
            if (SetProperty(ref AuthorValue, value))
            {
                IsDirty = true;
            }
        }
    }

    public string Description
    {
        get => DescriptionValue;
        set
        {
            if (SetProperty(ref DescriptionValue, value))
            {
                IsDirty = true;
            }
        }
    }

    public string SelectedImagePath
    {
        get => SelectedImagePathValue;
        set
        {
            if (SetProperty(ref SelectedImagePathValue, value))
            {
                IsDirty = true;
            }
        }
    }

    public CameraInfo? SelectedCamera
    {
        get => SelectedCameraValue;
        set => SetProperty(ref SelectedCameraValue, value);
    }

    public IRelayCommand RefreshCamerasCommand { get; }

    public IRelayCommand CaptureScreenshotCommand { get; }

    public IRelayCommand GenerateLoadingScreenCommand { get; }

    public LoadingEditorViewModel(IAddonService addonService, ILoadingScreenService loadingScreenService)
    {
        AddonService = addonService;
        LoadingScreenService = loadingScreenService;
        Title = "Loading Screen Editor";

        RefreshCamerasCommand = new AsyncRelayCommand(OnRefreshCamerasAsync);
        CaptureScreenshotCommand = new AsyncRelayCommand(OnCaptureScreenshotAsync);
        GenerateLoadingScreenCommand = new AsyncRelayCommand(OnGenerateLoadingScreenAsync);

        if (AddonService.ActiveAddon is not null)
        {
            MapTitle = AddonService.ActiveAddon.Name;
        }

        _ = OnRefreshCamerasAsync();
    }

    public override void Save()
    {
        var addon = AddonService.ActiveAddon;
        if (addon is not null)
        {
            _ = LoadingScreenService.SaveAddonInfoAsync(addon.ContentPath, addon.Name, MapTitle, Author, Description);
            IsDirty = false;
        }
    }

    private async Task OnRefreshCamerasAsync()
    {
        Cameras.Clear();
        var addon = AddonService.ActiveAddon;
        if (addon is null)
        {
            return;
        }

        var vmapPath = Path.Combine(addon.ContentPath, "maps", $"{addon.Name}.vmap");
        var list = await LoadingScreenService.ExtractCamerasFromVmapAsync(vmapPath);
        foreach (var cam in list)
        {
            Cameras.Add(cam);
        }

        SelectedCamera = Cameras.FirstOrDefault();
    }

    private async Task OnCaptureScreenshotAsync()
    {
        if (SelectedCamera is null)
        {
            return;
        }

        await LoadingScreenService.CaptureCameraScreenshotAsync(SelectedCamera, SelectedImagePath);
    }

    private async Task OnGenerateLoadingScreenAsync()
    {
        var addon = AddonService.ActiveAddon;
        if (addon is null || string.IsNullOrWhiteSpace(SelectedImagePath))
        {
            return;
        }

        var config = new LoadingScreenConfig
        {
            AddonName = addon.Name,
            MapName = addon.Name,
            Title = MapTitle,
            Author = Author,
            Description = Description,
            SelectedImagePath = SelectedImagePath
        };

        await LoadingScreenService.GenerateLoadingScreenAssetsAsync(config, SelectedImagePath);
        Save();
    }
}
