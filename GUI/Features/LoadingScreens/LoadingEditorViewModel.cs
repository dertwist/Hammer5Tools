namespace Hammer5Tools.App.Features.LoadingScreens;

using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.LoadingScreens;

public class LoadingEditorViewModel : DocumentViewModel
{
    public override string IconUri => "avares://Hammer5Tools.App/Assets/Icons/loading_editor.png";

    private readonly IAddonService AddonService;
    private readonly ILoadingScreenService LoadingScreenService;
    private readonly Services.IDialogService DialogService;
    private Avalonia.Media.Imaging.Bitmap? ImagePreviewValue;
    private string MapIconPathValue = string.Empty;
    private string StatusValue = "Ready";
    private bool IsDisposed;
    private bool DescriptionLoaded;

    public Task Initialization { get; }

    public ObservableCollection<string> Screenshots { get; } = [];
    public Avalonia.Media.Imaging.Bitmap? ImagePreview
    {
        get => ImagePreviewValue;
        private set => SetProperty(ref ImagePreviewValue, value);
    }

    public string MapIconPath
    {
        get => MapIconPathValue;
        set => SetProperty(ref MapIconPathValue, value);
    }

    public string Status
    {
        get => StatusValue;
        set => SetProperty(ref StatusValue, value);
    }

    public IRelayCommand BrowseImageCommand { get; }
    public IRelayCommand RefreshScreenshotsCommand { get; }
    public IRelayCommand BrowseIconCommand { get; }
    public IRelayCommand ApplyIconCommand { get; }


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
                MarkDirty();
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
                MarkDirty();
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
                MarkDirty();
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
                _ = LoadImagePreviewAsync();
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

    public LoadingEditorViewModel(IAddonService addonService, ILoadingScreenService loadingScreenService, Services.IDialogService dialogService)
    {
        AddonService = addonService;
        LoadingScreenService = loadingScreenService;
        DialogService = dialogService;
        ReportSaveFailure = dialogService.ShowErrorAsync;
        Title = "Loading Screen Editor";

        RefreshCamerasCommand = new AsyncRelayCommand(OnRefreshCamerasAsync);
        CaptureScreenshotCommand = new AsyncRelayCommand(OnCaptureScreenshotAsync);
        GenerateLoadingScreenCommand = new AsyncRelayCommand(OnGenerateLoadingScreenAsync);

        BrowseImageCommand = new AsyncRelayCommand(async () => SelectedImagePath = await DialogService.OpenFileAsync("Select screenshot", "*") ?? SelectedImagePath);
        RefreshScreenshotsCommand = new RelayCommand(RefreshScreenshots);
        BrowseIconCommand = new AsyncRelayCommand(async () => MapIconPath = await DialogService.OpenFileAsync("Select map icon", "*.svg") ?? MapIconPath);
        ApplyIconCommand = new AsyncRelayCommand(async () =>
        {
            if (AddonService.ActiveAddon is { } addon && File.Exists(MapIconPath))
            {
                Status = await LoadingScreenService.ApplyMapIconAsync(addon.ContentPath, addon.Name, MapIconPath) ? "Map icon applied" : "Map icon could not be applied";
            }
        });
        if (AddonService.ActiveAddon is not null)
        {
            MapTitle = AddonService.ActiveAddon.Name;
        }

        Initialization = LoadDescriptionAsync();
        RefreshScreenshots();
        _ = OnRefreshCamerasAsync();
    }

    private async Task LoadDescriptionAsync()
    {
        try
        {
            if (AddonService.ActiveAddon is { } addon)
            {
                var info = await LoadingScreenService.LoadAddonInfoAsync(addon.ContentPath);
                if (IsDisposed)
                {
                    return;
                }

                MapTitle = string.IsNullOrEmpty(info.Title) ? addon.Name : info.Title;
                Author = info.Author;
                Description = info.Description;
            }

            DescriptionLoaded = true;
            InitializeHistory(() => System.Text.Json.JsonSerializer.Serialize(new[] { MapTitle, Author, Description }), text =>
            {
                var fields = System.Text.Json.JsonSerializer.Deserialize<string[]>(text)!;
                MapTitle = fields[0];
                Author = fields[1];
                Description = fields[2];
            });
        }
        catch (Exception ex)
        {
            Status = $"Could not load addon description: {ex.Message}";
        }
    }

    protected override async Task<bool> SaveCoreAsync()
    {
        await Initialization;
        if (!DescriptionLoaded)
        {
            throw new InvalidOperationException("Reload the addon description before saving; the original file could not be read.");
        }

        var addon = AddonService.ActiveAddon;
        if (addon is not null)
        {
            return await LoadingScreenService.SaveAddonInfoAsync(addon.ContentPath, addon.Name, MapTitle, Author, Description);
        }

        return false;
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

        var success = await LoadingScreenService.CaptureCameraScreenshotAsync(SelectedCamera, SelectedImagePath);
        Status = success ? "Screenshot requested in CS2" : "Screenshot capture failed: check the CS2 connection";
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

        var generated = await LoadingScreenService.GenerateLoadingScreenAssetsAsync(config, SelectedImagePath);
        Status = generated ? "Loading screen compiled" : "Loading screen generation failed";
        if (generated)
        {
            await SaveAsync();
        }
    }
    private void RefreshScreenshots()
    {
        Screenshots.Clear();
        if (AddonService.ActiveAddon is not { } addon)
        {
            return;
        }

        foreach (var directory in new[] { Path.Combine(addon.ContentPath, "screenshots"), Path.Combine(addon.ContentPath, "panorama", "images", "map_icons", "screenshots") })
        {
            if (!Directory.Exists(directory))
            {
                continue;
            }

            foreach (var file in Directory.EnumerateFiles(directory, "*", SearchOption.AllDirectories).OrderBy(File.GetLastWriteTimeUtc))
            {
                if (Path.GetExtension(file).ToLowerInvariant() is ".png" or ".jpg" or ".jpeg" or ".tga")
                {
                    Screenshots.Add(file);
                }
            }
        }
    }

    private async Task LoadImagePreviewAsync()
    {
        var path = SelectedImagePath;
        Avalonia.Media.Imaging.Bitmap? bitmap = null;
        try
        {
            if (File.Exists(path))
            {
                bitmap = await Task.Run(() =>
                {
                    using var stream = File.OpenRead(path);
                    return Avalonia.Media.Imaging.Bitmap.DecodeToWidth(stream, 1920);
                });
            }

            if (IsDisposed || path != SelectedImagePath)
            {
                bitmap?.Dispose();
                return;
            }

            var previous = ImagePreview;
            ImagePreview = bitmap;
            previous?.Dispose();
        }
        catch (Exception ex)
        {
            bitmap?.Dispose();
            Status = $"Could not display screenshot: {ex.Message}";
        }
    }

    public override void Dispose()
    {
        IsDisposed = true;
        ImagePreview?.Dispose();
        base.Dispose();
        GC.SuppressFinalize(this);
    }
}
