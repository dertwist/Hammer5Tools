namespace Hammer5Tools.Core.LoadingScreens;

public interface ILoadingScreenService
{
    Task<IReadOnlyList<CameraInfo>> ExtractCamerasFromVmapAsync(string vmapPath, CancellationToken cancellationToken = default);

    Task<bool> CaptureCameraScreenshotAsync(CameraInfo camera, string outputPath, CancellationToken cancellationToken = default);

    Task<bool> GenerateLoadingScreenAssetsAsync(LoadingScreenConfig config, string sourceImagePath, CancellationToken cancellationToken = default);

    Task<bool> ApplyMapIconAsync(string addonContentPath, string addonName, string svgPath, CancellationToken cancellationToken = default);

    Task<bool> ApplyMapIconAsync(string addonContentPath, string addonName, string svgPath, bool fitContent, CancellationToken cancellationToken = default);

    /// <summary>Reads existing addon description fields without changing the source.</summary>
    Task<LoadingScreenConfig> LoadAddonInfoAsync(string addonContentPath, CancellationToken cancellationToken = default);

    Task<bool> SaveAddonInfoAsync(string addonContentPath, string mapName, string title, string author, string description, CancellationToken cancellationToken = default);

    Task<bool> CaptureAddonScreenshotsAsync(string vmapPath, string gamePath, string contentPath, bool history, CancellationToken cancellationToken = default);

    Task<bool> ApplyLoadingScreenImagesAsync(string addonName, string sourceDirectory, bool deleteExisting, bool includeCameraName, CancellationToken cancellationToken = default);

    /// <summary>Exports ordered frames at two frames per second; GIF/WebP use ImageSharp and MP4 requires FFmpeg.</summary>
    Task<string> ExportTimelineAsync(IReadOnlyList<string> imagePaths, string outputDirectory, string baseName, string format, string quality, CancellationToken cancellationToken = default);

    Task<string> LoadMapDescriptionAsync(string addonGamePath, string mapName, CancellationToken cancellationToken = default);

    Task<bool> SaveMapDescriptionAsync(string addonGamePath, string mapName, string description, CancellationToken cancellationToken = default);

    Task<int> ImportScreenshotsAsync(string targetDirectory, IReadOnlyList<string> sourcePaths, CancellationToken cancellationToken = default);
}
