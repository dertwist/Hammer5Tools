namespace Hammer5Tools.App.Features.LoadingScreens;

using System.Collections.ObjectModel;
using System.Text.RegularExpressions;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.LoadingScreens;

public partial class LoadingEditorViewModel : DocumentViewModel
{
    private readonly IAddonService AddonService;
    private readonly ILoadingScreenService LoadingScreenService;
    private readonly Services.IDialogService DialogService;
    private Avalonia.Media.Imaging.Bitmap? ImagePreviewValue;
    private Avalonia.Media.Imaging.Bitmap? MapIconPreviewValue;
    private string MapIconPathValue = string.Empty;
    private string StatusValue = "Ready";
    private string DescriptionValue = string.Empty;
    private string SelectedImagePathValue = string.Empty;
    private string SelectedFormatValue = "GIF";
    private string SelectedQualityValue = "High";
    private LoadingTreeItem? SelectedExplorerItemValue;
    private LoadingTreeItem? SelectedTimelineItemValue;
    private bool DeleteExistingValue = true;
    private bool IncludeCameraNameValue;
    private bool FitIconToViewBoxValue = true;
    private bool IsDisposed;
    private bool DescriptionLoaded;
    private string MapTitleValue = string.Empty;
    private string AuthorValue = string.Empty;

    public override string IconUri => "avares://Hammer5Tools/Assets/Icons/loading_editor.png";

    public Task Initialization { get; }
    public ObservableCollection<LoadingTreeItem> ExplorerItems { get; } = [];
    public ObservableCollection<LoadingTreeItem> LoadingShotItems { get; } = [];
    public ObservableCollection<LoadingTreeItem> HistoryItems { get; } = [];
    public ObservableCollection<LoadingTreeItem> TimelineItems { get; } = [];
    public ObservableCollection<CameraInfo> Cameras { get; } = [];
    public ObservableCollection<string> AnimationFormats { get; } = ["GIF", "WEBP", "MP4"];
    public ObservableCollection<string> AnimationQualities { get; } = ["Low", "Medium", "High"];

    public Avalonia.Media.Imaging.Bitmap? ImagePreview
    {
        get => ImagePreviewValue;
        private set
        {
            if (SetProperty(ref ImagePreviewValue, value)) OnPropertyChanged(nameof(PreviewWidth));
        }
    }

    public string MapIconPath
    {
        get => MapIconPathValue;
        set
        {
            if (SetProperty(ref MapIconPathValue, value)) _ = LoadIconPreviewAsync();
        }
    }

    public double PreviewWidth => ImagePreview is { } image ? image.Size.Width / image.Size.Height * 1080 : 1920;
    public bool IsLoadingShotPreview => ImagePreview is not null && LoadingShotItems.Any(item => string.Equals(item.FullPath, SelectedImagePath, StringComparison.OrdinalIgnoreCase));
    public string PreviewDescription => string.IsNullOrWhiteSpace(Description) ? "community placeholder text" : Description.Replace("<br>", "\n").Replace("<br/>", "\n").Replace("<p>", "").Replace("</p>", "\n");
    public string PreviewCameraName
    {
        get
        {
            if (!IncludeCameraName) return string.Empty;
            var name = Regex.Replace(Path.GetFileNameWithoutExtension(SelectedImagePath), @"_\d+$", string.Empty);
            name = Regex.Replace(name, $"^(?:(?:de|cs|ar)_)?{Regex.Escape(PreviewMapName)}_", string.Empty, RegexOptions.IgnoreCase);
            name = Regex.Replace(name, @"^(?:de|cs|ar|cp)_[a-zA-Z0-9]+_", string.Empty, RegexOptions.IgnoreCase);
            return Regex.IsMatch(name, @"^cam(?:era)?[\s_]*\d*$", RegexOptions.IgnoreCase) ? string.Empty : name;
        }
    }
    public Avalonia.Media.Imaging.Bitmap? MapIconPreview
    {
        get => MapIconPreviewValue;
        private set => SetProperty(ref MapIconPreviewValue, value);
    }

    private async Task LoadIconPreviewAsync()
    {
        var path = MapIconPath;
        Avalonia.Media.Imaging.Bitmap? bitmap = null;
        try
        {
            if (File.Exists(path))
            {
                bitmap = await Task.Run(() =>
                {
                    using var svg = new Svg.Skia.SKSvg();
                    if (svg.Load(path) is not { } picture) return null;
                    var bounds = picture.CullRect;
                    if (bounds.Width <= 0 || bounds.Height <= 0) return null;
                    var scale = 512 / Math.Max(bounds.Width, bounds.Height);
                    using var raster = new SkiaSharp.SKBitmap(Math.Max(1, (int)(bounds.Width * scale)), Math.Max(1, (int)(bounds.Height * scale)));
                    using var canvas = new SkiaSharp.SKCanvas(raster);
                    canvas.Clear(SkiaSharp.SKColors.Transparent);
                    canvas.Scale(scale);
                    canvas.Translate(-bounds.Left, -bounds.Top);
                    canvas.DrawPicture(picture);
                    using var data = raster.Encode(SkiaSharp.SKEncodedImageFormat.Png, 100);
                    using var stream = data.AsStream();
                    return new Avalonia.Media.Imaging.Bitmap(stream);
                });
            }
            if (IsDisposed || path != MapIconPath)
            {
                bitmap?.Dispose();
                return;
            }
            var previous = MapIconPreview;
            MapIconPreview = bitmap;
            previous?.Dispose();
        }
        catch (Exception ex)
        {
            bitmap?.Dispose();
            Status = $"Could not preview map icon: {ex.Message}";
        }
    }

    public string MapIconPreviewText => File.Exists(MapIconPath) ? Path.GetFileName(MapIconPath) : "Drag and drop a SVG";

    public string Status
    {
        get => StatusValue;
        set => SetProperty(ref StatusValue, value);
    }

    public string MapTitle
    {
        get => MapTitleValue;
        set
        {
            if (SetProperty(ref MapTitleValue, value) && DescriptionLoaded) MarkDirty();
        }
    }
    public string PreviewMapName => AddonService.ActiveAddon?.Name ?? string.Empty;
    public string Author
    {
        get => AuthorValue;
        set
        {
            if (SetProperty(ref AuthorValue, value) && DescriptionLoaded) MarkDirty();
        }
    }

    public string Description
    {
        get => DescriptionValue;
        set
        {
            if (SetProperty(ref DescriptionValue, value))
            {
                OnPropertyChanged(nameof(PreviewDescription));
                if (DescriptionLoaded) MarkDirty();
            }
        }
    }

    public string SelectedImagePath
    {
        get => SelectedImagePathValue;
        set
        {
            if (SetProperty(ref SelectedImagePathValue, value)) _ = LoadImagePreviewAsync();
        }
    }

    public LoadingTreeItem? SelectedExplorerItem
    {
        get => SelectedExplorerItemValue;
        set
        {
            if (SetProperty(ref SelectedExplorerItemValue, value) && value is { IsImage: true }) SelectedImagePath = value.FullPath;
        }
    }

    public LoadingTreeItem? SelectedTimelineItem
    {
        get => SelectedTimelineItemValue;
        set
        {
            if (SetProperty(ref SelectedTimelineItemValue, value) && value is { IsImage: true }) SelectedImagePath = value.FullPath;
        }
    }

    public string SelectedFormat
    {
        get => SelectedFormatValue;
        set => SetProperty(ref SelectedFormatValue, value);
    }

    public string SelectedQuality
    {
        get => SelectedQualityValue;
        set => SetProperty(ref SelectedQualityValue, value);
    }

    public bool DeleteExisting
    {
        get => DeleteExistingValue;
        set => SetProperty(ref DeleteExistingValue, value);
    }

    public bool IncludeCameraName
    {
        get => IncludeCameraNameValue;
        set
        {
            if (SetProperty(ref IncludeCameraNameValue, value)) OnPropertyChanged(nameof(PreviewCameraName));
        }
    }

    public bool FitIconToViewBox
    {
        get => FitIconToViewBoxValue;
        set => SetProperty(ref FitIconToViewBoxValue, value);
    }

    public IRelayCommand BrowseImageCommand { get; }
    public IRelayCommand RefreshScreenshotsCommand { get; }
    public IRelayCommand BrowseIconCommand { get; }
    public IRelayCommand ApplyIconCommand { get; }
    public IRelayCommand RefreshCamerasCommand { get; }
    public IRelayCommand CaptureScreenshotCommand { get; }
    public IRelayCommand CaptureHistoryShotsCommand { get; }
    public IRelayCommand GenerateLoadingScreenCommand { get; }
    public IRelayCommand ExportAnimationsCommand { get; }
    public IRelayCommand<LoadingTreeItem?> ExportCameraAnimationCommand { get; }
    public IRelayCommand ApplyDescriptionCommand { get; }
    public IRelayCommand<string?> OpenFolderCommand { get; }
    public IRelayCommand<LoadingTreeItem?> RemoveItemCommand { get; }

    public LoadingEditorViewModel(IAddonService addonService, ILoadingScreenService loadingScreenService, Services.IDialogService dialogService)
    {
        AddonService = addonService;
        LoadingScreenService = loadingScreenService;
        DialogService = dialogService;
        ReportSaveFailure = dialogService.ShowErrorAsync;
        Title = "Loading Screen Editor";

        BrowseImageCommand = new AsyncRelayCommand(async () => SelectedImagePath = await DialogService.OpenFileAsync("Select screenshot", "*") ?? SelectedImagePath);
        RefreshScreenshotsCommand = new RelayCommand(RefreshScreenshots);
        BrowseIconCommand = new AsyncRelayCommand(async () =>
        {
            MapIconPath = await DialogService.OpenFileAsync("Select map icon", "*.svg") ?? MapIconPath;
            OnPropertyChanged(nameof(MapIconPreviewText));
        });
        ApplyIconCommand = new AsyncRelayCommand(ApplyIconAsync);
        RefreshCamerasCommand = new AsyncRelayCommand(RefreshCamerasAsync);
        CaptureScreenshotCommand = new AsyncRelayCommand(() => CaptureAllScreenshotsAsync(history: false));
        CaptureHistoryShotsCommand = new AsyncRelayCommand(() => CaptureAllScreenshotsAsync(history: true));
        GenerateLoadingScreenCommand = new AsyncRelayCommand(ApplyLoadingImagesAsync);
        ExportAnimationsCommand = new AsyncRelayCommand(ExportAnimationsAsync);
        ExportCameraAnimationCommand = new AsyncRelayCommand<LoadingTreeItem?>(ExportCameraAnimationAsync);
        ApplyDescriptionCommand = new AsyncRelayCommand(ApplyDescriptionAsync);
        OpenFolderCommand = new RelayCommand<string?>(OpenFolder);
        RemoveItemCommand = new AsyncRelayCommand<LoadingTreeItem?>(RemoveItemAsync);

        Initialization = LoadDescriptionAsync();
        RefreshScreenshots();
        _ = RefreshCamerasAsync();
    }

    private async Task LoadDescriptionAsync()
    {
        try
        {
            if (AddonService.ActiveAddon is { } addon)
            {
                var info = await LoadingScreenService.LoadAddonInfoAsync(addon.ContentPath);
                MapTitle = string.IsNullOrEmpty(info.Title) ? addon.Name : info.Title;
                Author = info.Author;
                var addonGameRoot = Directory.GetParent(addon.GamePath)?.FullName ?? addon.GamePath;
                Description = await LoadingScreenService.LoadMapDescriptionAsync(addonGameRoot, addon.Name) is { Length: > 0 } mapDescription
                    ? mapDescription : info.Description;
                MapIconPath = Path.Combine(addon.ContentPath, "panorama", "images", "map_icons", $"map_icon_{addon.Name}.svg");
                if (!File.Exists(MapIconPath)) MapIconPath = string.Empty;
                OnPropertyChanged(nameof(MapIconPreviewText));
            }

            DescriptionLoaded = true;
            InitializeHistory(SerializeDescription, RestoreDescription);
        }
        catch (Exception ex)
        {
            Status = $"Could not load addon description: {ex.Message}";
        }
    }

    private string SerializeDescription()
    {
        return System.Text.Json.JsonSerializer.Serialize(new[] { MapTitle, Author, Description });
    }

    private void RestoreDescription(string text)
    {
        var fields = System.Text.Json.JsonSerializer.Deserialize<string[]>(text) ?? [];
        if (fields.Length != 3) throw new InvalidDataException("The loading screen description history is invalid.");
        MapTitle = fields[0];
        Author = fields[1];
        Description = fields[2];
    }

    protected override async Task<bool> SaveCoreAsync()
    {
        await Initialization;
        if (!DescriptionLoaded) throw new InvalidOperationException("Reload the addon description before saving; the original file could not be read.");
        var addon = AddonService.ActiveAddon;
        return addon is not null && await LoadingScreenService.SaveAddonInfoAsync(addon.ContentPath, addon.Name, MapTitle, Author, Description);
    }

    private async Task RefreshCamerasAsync()
    {
        Cameras.Clear();
        if (AddonService.ActiveAddon is not { } addon) return;
        var vmapPath = Path.Combine(addon.ContentPath, "maps", $"{addon.Name}.vmap");
        foreach (var camera in await LoadingScreenService.ExtractCamerasFromVmapAsync(vmapPath)) Cameras.Add(camera);
        RebuildTimeline();
    }

    private async Task CaptureAllScreenshotsAsync(bool history)
    {
        var addon = AddonService.ActiveAddon;
        if (addon is null) return;
        var vmapPath = Path.Combine(addon.ContentPath, "maps", $"{addon.Name}.vmap");
        var addonGameRoot = Directory.GetParent(addon.GamePath)?.FullName ?? addon.GamePath;
        Status = await LoadingScreenService.CaptureAddonScreenshotsAsync(vmapPath, addonGameRoot, addon.ContentPath, history)
            ? history ? "History screenshots captured" : "Loading screen screenshots captured"
            : "Could not capture screenshots; check cameras and the CS2 connection";
        RefreshScreenshots();
    }

    private async Task ApplyLoadingImagesAsync()
    {
        var addon = AddonService.ActiveAddon;
        if (addon is null) return;
        var directory = Path.Combine(Directory.GetParent(addon.GamePath)?.FullName ?? addon.GamePath, "screenshots", "Hammer5Tools", "LoadingScreen");
        var count = Directory.Exists(directory) ? Directory.EnumerateFiles(directory).Count() : 0;
        if (count > 10 && !await DialogService.ConfirmAsync("Loading screenshots", "More than 10 files were found. CS2 supports at most 10. Continue?")) return;
        Status = await LoadingScreenService.ApplyLoadingScreenImagesAsync(addon.Name, directory, DeleteExisting, IncludeCameraName)
            ? "Loading screen images compiled" : "Loading screen image generation failed";
        if (Status == "Loading screen images compiled") await SaveAsync();
    }

    private async Task ApplyIconAsync()
    {
        var addon = AddonService.ActiveAddon;
        if (addon is null || !File.Exists(MapIconPath)) return;
        Status = await LoadingScreenService.ApplyMapIconAsync(addon.ContentPath, addon.Name, MapIconPath, FitIconToViewBox)
            ? "Map icon applied" : "Map icon could not be applied";
    }

    private async Task ApplyDescriptionAsync()
    {
        var addon = AddonService.ActiveAddon;
        if (addon is null) return;
        var addonGameRoot = Directory.GetParent(addon.GamePath)?.FullName ?? addon.GamePath;
        var saved = await LoadingScreenService.SaveMapDescriptionAsync(addonGameRoot, addon.Name, Description);
        if (saved) saved = await SaveAsync();
        Status = saved ? "Description applied" : "Description could not be applied";
    }

    private async Task ExportAnimationsAsync()
    {
        var outputDirectory = await DialogService.PickFolderAsync("Select Output Directory for Animations");
        if (string.IsNullOrWhiteSpace(outputDirectory)) return;
        var cameras = TimelineItems.Where(item => item.Children.Count > 0).ToArray();
        foreach (var camera in cameras)
        {
            try
            {
                var paths = camera.Children.OrderBy(item => Path.GetFileName(Path.GetDirectoryName(item.FullPath)), StringComparer.Ordinal)
                    .ThenBy(item => Path.GetFileName(item.FullPath), StringComparer.OrdinalIgnoreCase).Select(item => item.FullPath).ToArray();
                await LoadingScreenService.ExportTimelineAsync(paths, outputDirectory, camera.Name, SelectedFormat, SelectedQuality);
            }
            catch (Exception ex)
            {
                await DialogService.ShowErrorAsync($"Could not export {camera.Name}: {ex.Message}");
                return;
            }
        }

        Status = $"Exported {cameras.Length} camera animations";
    }

    private async Task ExportCameraAnimationAsync(LoadingTreeItem? camera)
    {
        if (camera is null || camera.Children.Count == 0) return;
        var outputDirectory = await DialogService.PickFolderAsync("Select Output Directory");
        if (string.IsNullOrWhiteSpace(outputDirectory)) return;
        try
        {
            var paths = camera.Children.OrderBy(item => Path.GetFileName(Path.GetDirectoryName(item.FullPath)), StringComparer.Ordinal)
                .ThenBy(item => Path.GetFileName(item.FullPath), StringComparer.OrdinalIgnoreCase).Select(item => item.FullPath).ToArray();
            var output = await LoadingScreenService.ExportTimelineAsync(paths, outputDirectory, camera.Name, SelectedFormat, SelectedQuality);
            Status = $"Animation exported to {output}";
        }
        catch (Exception ex)
        {
            await DialogService.ShowErrorAsync($"Could not export {camera.Name}: {ex.Message}");
        }
    }

    private void RefreshScreenshots()
    {
        foreach (var item in ExplorerItems) item.DisposeTree();
        foreach (var item in TimelineItems) item.DisposeTree();
        ExplorerItems.Clear();
        LoadingShotItems.Clear();
        HistoryItems.Clear();
        var addon = AddonService.ActiveAddon;
        if (addon is null) return;

        var loadingPath = Path.Combine(Directory.GetParent(addon.GamePath)?.FullName ?? addon.GamePath, "screenshots", "Hammer5Tools", "LoadingScreen");
        var historyPath = Path.Combine(addon.ContentPath, "panorama", "history_screenshots");
        var loading = CreateFolder("LoadingShots", loadingPath, imageExtensionsOnly: true);
        var history = CreateFolder("History", historyPath, imageExtensionsOnly: false);
        ExplorerItems.Add(loading);
        ExplorerItems.Add(history);
        foreach (var item in loading.Children) LoadingShotItems.Add(item);
        foreach (var item in history.Children) HistoryItems.Add(item);
        foreach (var item in LoadingShotItems) LoadThumbnails(item);
        foreach (var item in HistoryItems) LoadThumbnails(item);
        RebuildTimeline();
    }

    private static LoadingTreeItem CreateFolder(string title, string path, bool imageExtensionsOnly)
    {
        var root = new LoadingTreeItem(title, path, false);
        if (!Directory.Exists(path)) return root;
        foreach (var entry in Directory.EnumerateFileSystemEntries(path).OrderBy(value => value, StringComparer.OrdinalIgnoreCase))
        {
            if (Directory.Exists(entry))
            {
                var folder = new LoadingTreeItem(Path.GetFileName(entry), entry, false);
                foreach (var image in EnumerateImages(entry, recursive: false)) folder.Children.Add(new LoadingTreeItem(Path.GetFileName(image), image, true));
                root.Children.Add(folder);
            }
            else if (!imageExtensionsOnly || IsImage(entry))
            {
                root.Children.Add(new LoadingTreeItem(Path.GetFileName(entry), entry, IsImage(entry)));
            }
        }

        return root;
    }

    private void RebuildTimeline()
    {
        foreach (var item in TimelineItems) item.DisposeTree();
        TimelineItems.Clear();
        var grouped = new SortedDictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
        foreach (var session in HistoryItems)
        {
            foreach (var file in EnumerateImages(session.FullPath, recursive: false))
            {
                var name = CameraName(Path.GetFileName(file));
                if (!grouped.TryGetValue(name, out var images)) grouped[name] = images = [];
                images.Add(file);
            }
        }

        foreach (var (name, images) in grouped)
        {
            var camera = new LoadingTreeItem($"{name} ({images.Count} images)", string.Empty, false);
            foreach (var image in images.OrderBy(image => Path.GetFileName(Path.GetDirectoryName(image)), StringComparer.Ordinal).ThenBy(image => Path.GetFileName(image), StringComparer.OrdinalIgnoreCase))
            {
                var frame = new LoadingTreeItem(Path.GetFileName(image), image, true);
                camera.Children.Add(frame);
                LoadThumbnail(frame);
            }
            TimelineItems.Add(camera);
        }
    }

    private static void LoadThumbnails(LoadingTreeItem item)
    {
        if (item.IsImage) LoadThumbnail(item);
        foreach (var child in item.Children) LoadThumbnails(child);
    }

    private static async void LoadThumbnail(LoadingTreeItem item)
    {
        try
        {
            var bitmap = await Task.Run(() =>
            {
                using var stream = File.OpenRead(item.FullPath);
                return Avalonia.Media.Imaging.Bitmap.DecodeToWidth(stream, 64);
            });
            if (item.IsDisposed) bitmap.Dispose();
            else item.Thumbnail = bitmap;
        }
        catch (IOException)
        {
        }
        catch (UnauthorizedAccessException)
        {
        }
        catch (ArgumentException)
        {
        }
    }

    private static IEnumerable<string> EnumerateImages(string directory, bool recursive) =>
        Directory.Exists(directory) ? Directory.EnumerateFiles(directory, "*", recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly).Where(IsImage) : [];

    private static bool IsImage(string path) => Path.GetExtension(path).ToLowerInvariant() is ".png" or ".jpg" or ".jpeg" or ".bmp" or ".tga";

    private static string CameraName(string path)
    {
        var stem = Path.GetFileNameWithoutExtension(path);
        var match = Regex.Match(stem, "^(.+?)_(\\d+)$");
        if (!match.Success) return stem;
        var number = int.Parse(match.Groups[2].Value, System.Globalization.CultureInfo.InvariantCulture);
        return number == 0 ? match.Groups[1].Value : $"{match.Groups[1].Value} {number}";
    }

    private void OpenFolder(string? path)
    {
        var folder = path is not null && Directory.Exists(path) ? path : path is not null ? Path.GetDirectoryName(path) : null;
        if (folder is not null && Directory.Exists(folder)) System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(folder) { UseShellExecute = true });
    }

    private async Task RemoveItemAsync(LoadingTreeItem? item)
    {
        if (item is null || !File.Exists(item.FullPath) && !Directory.Exists(item.FullPath)) return;
        if (!await DialogService.ConfirmAsync("Remove screenshot", $"Delete '{item.Name}'?")) return;
        if (Directory.Exists(item.FullPath)) Directory.Delete(item.FullPath, recursive: true);
        else File.Delete(item.FullPath);
        RefreshScreenshots();
        if (SelectedImagePath == item.FullPath) SelectedImagePath = string.Empty;
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
            OnPropertyChanged(nameof(IsLoadingShotPreview));
            OnPropertyChanged(nameof(PreviewCameraName));
            previous?.Dispose();
        }
        catch (Exception ex)
        {
            bitmap?.Dispose();
            Status = $"Could not display screenshot: {ex.Message}";
        }
    }

    public void SetDroppedIcon(string path)
    {
        MapIconPath = path;
        OnPropertyChanged(nameof(MapIconPreviewText));
    }

    public async Task ImportDroppedScreenshotsAsync(bool history, IReadOnlyList<string> paths)
    {
        var addon = AddonService.ActiveAddon;
        if (addon is null || paths.Count == 0) return;
        var directory = history
            ? Path.Combine(addon.ContentPath, "panorama", "history_screenshots", $"Imported_{DateTime.Now:yyyy-MM-dd_HH-mm-ss}")
            : Path.Combine(Directory.GetParent(addon.GamePath)?.FullName ?? addon.GamePath, "screenshots", "Hammer5Tools", "LoadingScreen");
        var count = await LoadingScreenService.ImportScreenshotsAsync(directory, paths);
        RefreshScreenshots();
        Status = $"Imported {count} screenshot{(count == 1 ? string.Empty : "s")}";
    }

    public override void Dispose()
    {
        IsDisposed = true;
        ImagePreview?.Dispose();
        MapIconPreview?.Dispose();
        foreach (var item in ExplorerItems) item.DisposeTree();
        foreach (var item in TimelineItems) item.DisposeTree();
        base.Dispose();
        GC.SuppressFinalize(this);
    }
}

public sealed class LoadingTreeItem(string name, string fullPath, bool isImage) : CommunityToolkit.Mvvm.ComponentModel.ObservableObject
{
    public string Name { get; } = name;
    public string FullPath { get; } = fullPath;
    public bool IsImage { get; } = isImage;
    public ObservableCollection<LoadingTreeItem> Children { get; } = [];
    private Avalonia.Media.Imaging.Bitmap? ThumbnailValue;
    public bool IsDisposed { get; private set; }
    public Avalonia.Media.Imaging.Bitmap? Thumbnail
    {
        get => ThumbnailValue;
        set => SetProperty(ref ThumbnailValue, value);
    }

    public void DisposeTree()
    {
        if (IsDisposed) return;
        IsDisposed = true;
        Thumbnail?.Dispose();
        Thumbnail = null;
        foreach (var child in Children) child.DisposeTree();
    }
}
