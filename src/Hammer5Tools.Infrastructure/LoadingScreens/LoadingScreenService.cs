namespace Hammer5Tools.Infrastructure.LoadingScreens;

using System.Globalization;
using System.Numerics;
using System.Text;
using System.Text.RegularExpressions;
using Hammer5Tools.Core.Commands;
using Hammer5Tools.Core.Compiler;
using Hammer5Tools.Core.LoadingScreens;
using Microsoft.Extensions.Logging;

public partial class LoadingScreenService : ILoadingScreenService
{
    private readonly ICommandService CommandService;
    private readonly IResourceCompiler ResourceCompiler;
    private readonly ILogger<LoadingScreenService> Logger;

    public LoadingScreenService(
        ICommandService commandService,
        IResourceCompiler resourceCompiler,
        ILogger<LoadingScreenService> logger)
    {
        CommandService = commandService;
        ResourceCompiler = resourceCompiler;
        Logger = logger;
    }

    public async Task<IReadOnlyList<CameraInfo>> ExtractCamerasFromVmapAsync(string vmapPath, CancellationToken cancellationToken = default)
    {
        var cameras = new List<CameraInfo>();
        if (!File.Exists(vmapPath))
        {
            Logger.LogWarning("Vmap file not found: {Path}", vmapPath);
            return cameras;
        }

        try
        {
            var content = await File.ReadAllTextAsync(vmapPath, cancellationToken);
            // Search for camera blocks or point_camera entities
            var entityMatches = CameraEntityRegex().Matches(content);
            var index = 1;
            foreach (Match match in entityMatches)
            {
                var block = match.Value;
                var origin = ParseVector(OriginRegex().Match(block).Groups[1].Value);
                var angles = ParseVector(AnglesRegex().Match(block).Groups[1].Value);
                var fovMatch = FovRegex().Match(block);
                var fov = fovMatch.Success && float.TryParse(fovMatch.Groups[1].Value, NumberStyles.Float, CultureInfo.InvariantCulture, out var f) ? f : 90f;

                var nameMatch = TargetnameRegex().Match(block);
                var name = nameMatch.Success && !string.IsNullOrWhiteSpace(nameMatch.Groups[1].Value)
                    ? nameMatch.Groups[1].Value
                    : $"Camera {index++}";

                cameras.Add(new CameraInfo(name, origin, angles, fov));
            }

            // Fallback default camera if none found
            if (cameras.Count == 0)
            {
                cameras.Add(new CameraInfo("Default Spawn View", new Vector3(0, 0, 64), new Vector3(0, 0, 0), 90f));
            }
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Failed to parse cameras from vmap: {Path}", vmapPath);
        }

        return cameras;
    }

    public async Task<bool> CaptureCameraScreenshotAsync(CameraInfo camera, string outputPath, CancellationToken cancellationToken = default)
    {
        try
        {
            var posCmd = string.Format(CultureInfo.InvariantCulture, "setpos {0} {1} {2}", camera.Position.X, camera.Position.Y, camera.Position.Z);
            var angCmd = string.Format(CultureInfo.InvariantCulture, "setang {0} {1} {2}", camera.Angles.X, camera.Angles.Y, camera.Angles.Z);

            await CommandService.SendCommandAsync("r_drawviewmodel 0", cancellationToken);
            await CommandService.SendCommandAsync(posCmd, cancellationToken);
            await CommandService.SendCommandAsync(angCmd, cancellationToken);
            await Task.Delay(200, cancellationToken);
            await CommandService.SendCommandAsync("screenshot", cancellationToken);
            await CommandService.SendCommandAsync("r_drawviewmodel 1", cancellationToken);

            Logger.LogInformation("Dispatched screenshot capture for camera {Name} to {Path}", camera.Name, outputPath);
            return true;
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Failed to capture camera screenshot");
            return false;
        }
    }

    public async Task<bool> GenerateLoadingScreenAssetsAsync(LoadingScreenConfig config, string sourceImagePath, CancellationToken cancellationToken = default)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(config.AddonName) || string.IsNullOrWhiteSpace(config.MapName))
            {
                return false;
            }

            // Create panorama/images/map_icons/screenshots/1080p/
            var addonPath = Path.Combine(Directory.GetCurrentDirectory(), "content", "csgo_addons", config.AddonName);
            var targetDir = Path.Combine(addonPath, "panorama", "images", "map_icons", "screenshots", "1080p");
            Directory.CreateDirectory(targetDir);

            var targetVtex = Path.Combine(targetDir, $"{config.MapName}.vtex");
            var vtexContent = $$"""
                <!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
                {
                    m_inputTextureArray = 
                    [
                        {
                            m_name = "InputTexture0"
                            m_imageFileName = "{{sourceImagePath.Replace("\\", "/")}}"
                        }
                    ]
                    m_outputTypeString = "2D"
                    m_outputFormat = "BC7"
                }
                """;

            await File.WriteAllTextAsync(targetVtex, vtexContent, cancellationToken);

            // Trigger compilation
            var result = await ResourceCompiler.CompileAssetAsync(targetVtex, addonName: config.AddonName, cancellationToken);
            return result.Success;
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Failed to generate loading screen assets");
            return false;
        }
    }

    public async Task<bool> SaveAddonInfoAsync(string addonContentPath, string mapName, string title, string author, string description, CancellationToken cancellationToken = default)
    {
        try
        {
            var infoPath = Path.Combine(addonContentPath, "addoninfo.txt");
            var sb = new StringBuilder();
            sb.AppendLine("\"AddonInfo\"");
            sb.AppendLine("{");
            sb.AppendLine($"\t\"addonTitle\"\t\t\"{Escape(title)}\"");
            sb.AppendLine($"\t\"addonAuthor\"\t\t\"{Escape(author)}\"");
            sb.AppendLine($"\t\"addonDescription\"\t\"{Escape(description)}\"");
            sb.AppendLine($"\t\"mapName\"\t\t\"{Escape(mapName)}\"");
            sb.AppendLine("}");

            await File.WriteAllTextAsync(infoPath, sb.ToString(), cancellationToken);
            return true;
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Failed to save addoninfo.txt");
            return false;
        }
    }

    private static string Escape(string val) => val.Replace("\"", "\\\"");

    private static Vector3 ParseVector(string str)
    {
        if (string.IsNullOrWhiteSpace(str))
        {
            return Vector3.Zero;
        }

        var parts = str.Split([' ', ','], StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length >= 3 &&
            float.TryParse(parts[0], NumberStyles.Float, CultureInfo.InvariantCulture, out var x) &&
            float.TryParse(parts[1], NumberStyles.Float, CultureInfo.InvariantCulture, out var y) &&
            float.TryParse(parts[2], NumberStyles.Float, CultureInfo.InvariantCulture, out var z))
        {
            return new Vector3(x, y, z);
        }

        return Vector3.Zero;
    }

    [GeneratedRegex(@"(?:entity|CMapEntity|CMapCamera)[\s\S]*?(?:point_camera|info_camera_link|CMapCamera)[\s\S]*?\}", RegexOptions.Compiled)]
    private static partial Regex CameraEntityRegex();

    [GeneratedRegex(@"""origin""\s+""([^""]+)""", RegexOptions.Compiled)]
    private static partial Regex OriginRegex();

    [GeneratedRegex(@"""angles""\s+""([^""]+)""", RegexOptions.Compiled)]
    private static partial Regex AnglesRegex();

    [GeneratedRegex(@"""fov""\s+""?([0-9.]+)""?", RegexOptions.Compiled)]
    private static partial Regex FovRegex();

    [GeneratedRegex(@"""targetname""\s+""([^""]+)""", RegexOptions.Compiled)]
    private static partial Regex TargetnameRegex();
}
