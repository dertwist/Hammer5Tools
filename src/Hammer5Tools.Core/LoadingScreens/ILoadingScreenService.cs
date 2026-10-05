namespace Hammer5Tools.Core.LoadingScreens;

public interface ILoadingScreenService
{
    Task<IReadOnlyList<CameraInfo>> ExtractCamerasFromVmapAsync(string vmapPath, CancellationToken cancellationToken = default);

    Task<bool> CaptureCameraScreenshotAsync(CameraInfo camera, string outputPath, CancellationToken cancellationToken = default);

    Task<bool> GenerateLoadingScreenAssetsAsync(LoadingScreenConfig config, string sourceImagePath, CancellationToken cancellationToken = default);

    Task<bool> SaveAddonInfoAsync(string addonContentPath, string mapName, string title, string author, string description, CancellationToken cancellationToken = default);
}
