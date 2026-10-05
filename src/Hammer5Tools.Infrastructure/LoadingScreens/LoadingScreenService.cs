namespace Hammer5Tools.Infrastructure.LoadingScreens;

using System.Globalization;
using System.Numerics;
using System.Text;
using System.Text.RegularExpressions;
using Datamodel;
using Hammer5Tools.Core.Commands;
using Hammer5Tools.Core.Compiler;
using Hammer5Tools.Core.LoadingScreens;
using Microsoft.Extensions.Logging;
using ValveKeyValue;

public partial class LoadingScreenService : ILoadingScreenService
{
    private static readonly KVSerializer Kv1Serializer = KVSerializer.Create(KVSerializationFormat.KeyValues1Text);

    private readonly ICommandService CommandService;
    private readonly IResourceCompiler ResourceCompiler;
    private readonly ILogger<LoadingScreenService> Logger;
    private readonly Core.Cs2.ICs2Locator Cs2Locator;
    private readonly Core.Settings.ISettingsService SettingsService;

    public LoadingScreenService(
        ICommandService commandService,
        IResourceCompiler resourceCompiler,
        ILogger<LoadingScreenService> logger, Core.Cs2.ICs2Locator cs2Locator, Core.Settings.ISettingsService settingsService)
    {
        CommandService = commandService;
        ResourceCompiler = resourceCompiler;
        Logger = logger;
        Cs2Locator = cs2Locator;
        SettingsService = settingsService;
    }

    public async Task<IReadOnlyList<CameraInfo>> ExtractCamerasFromVmapAsync(string vmapPath, CancellationToken cancellationToken = default)
    {
        var cameras = new List<CameraInfo>();
        if (!File.Exists(vmapPath))
        {
            Logger.LogWarning("Vmap file not found: {Path}", vmapPath);
            return cameras;
        }

        var index = 1;

        // 1. Try DMX / KeyValues2 Datamodel parsing
        try
        {
            await using var fs = new FileStream(vmapPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            var dm = Datamodel.Load(fs);

            foreach (var elem in dm.AllElements)
            {
                cancellationToken.ThrowIfCancellationRequested();
                if (SettingsService.Settings.Editor.LoadingUseSavedCameras ? elem.ClassName == "CMapSavedCamera" : elem.ClassName == "CMapCamera" || elem.ClassName == "point_camera" || elem.ClassName == "info_camera_link")
                {
                    var pos = Vector3.Zero;
                    if (elem.TryGetValue("origin", out var o) && o is System.Numerics.Vector3 v)
                    {
                        pos = v;
                    }

                    var ang = Vector3.Zero;
                    if (elem.TryGetValue("angles", out var a) && a is global::Datamodel.QAngle q)
                    {
                        ang = new Vector3(q.Pitch, q.Yaw, q.Roll);
                    }

                    var fov = elem.TryGetValue("fov", out var f) && f is float fval ? fval : 90f;
                    var name = !string.IsNullOrWhiteSpace(elem.Name) ? elem.Name : $"Camera {index++}";

                    cameras.Add(new CameraInfo(name, pos, ang, fov));
                }
            }

            if (cameras.Count > 0)
            {
                return cameras;
            }
        }
        catch
        {
            // Fallback to text parsing
        }

        // 2. Text / Regex fallback
        try
        {
            var content = await File.ReadAllTextAsync(vmapPath, cancellationToken);
            var entityMatches = CameraEntityRegex().Matches(content);
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

            if (!CommandService.IsConnected)
            {
                return false;
            }

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

            var cs2Root = Cs2Locator.FindCs2Path() ?? throw new InvalidOperationException("CS2 installation not found.");
            var addonPath = Core.Cs2.Cs2Paths.GetAddonContentPath(cs2Root, config.AddonName);
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

            var result = await ResourceCompiler.CompileAssetAsync(targetVtex, addonName: config.AddonName, cancellationToken);
            return result.Success;
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Failed to generate loading screen assets");
            return false;
        }
    }

    public async Task<LoadingScreenConfig> LoadAddonInfoAsync(string addonContentPath, CancellationToken cancellationToken = default)
    {
        var path = Path.Combine(addonContentPath, "addoninfo.txt");
        if (!File.Exists(path))
        {
            return new LoadingScreenConfig();
        }

        var bytes = await File.ReadAllBytesAsync(path, cancellationToken);
        using var stream = new MemoryStream(bytes);
        var root = Kv1Serializer.Deserialize(stream).Root;
        return new LoadingScreenConfig
        {
            Title = root["addonTitle"]?.ToString() ?? string.Empty,
            Author = root["addonAuthor"]?.ToString() ?? string.Empty,
            Description = root["addonDescription"]?.ToString() ?? string.Empty
        };
    }

    public async Task<bool> SaveAddonInfoAsync(string addonContentPath, string mapName, string title, string author, string description, CancellationToken cancellationToken = default)
    {
        try
        {
            var infoPath = Path.Combine(addonContentPath, "addoninfo.txt");
            var root = new KVObject();
            if (File.Exists(infoPath))
            {
                using var existing = File.OpenRead(infoPath);
                root = Kv1Serializer.Deserialize(existing).Root;
            }
            root["addonTitle"] = new KVObject(title);
            root["addonAuthor"] = new KVObject(author);
            root["addonDescription"] = new KVObject(description);
            root["mapName"] = new KVObject(mapName);

            var doc = new KVDocument(new KVHeader(), "AddonInfo", root);

            using var ms = new MemoryStream();
            Kv1Serializer.Serialize(ms, doc);
            cancellationToken.ThrowIfCancellationRequested();
            Hammer5Tools.Core.Formats.DocumentFile.WriteKeyValues1(infoPath, System.Text.Encoding.UTF8.GetString(ms.ToArray()));
            await Task.CompletedTask;
            return true;
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Failed to save addoninfo.txt");
            return false;
        }
    }

    public async Task<bool> ApplyMapIconAsync(string addonContentPath, string addonName, string svgPath, CancellationToken cancellationToken = default)
    {
        var text = await File.ReadAllTextAsync(svgPath, cancellationToken);
        using var reader = System.Xml.XmlReader.Create(new StringReader(text), new System.Xml.XmlReaderSettings { DtdProcessing = System.Xml.DtdProcessing.Prohibit });
        var document = System.Xml.Linq.XDocument.Load(reader);
        if (document.Root?.Name.LocalName != "svg")
        {
            throw new InvalidDataException("Select an SVG document.");
        }

        var target = Path.Combine(addonContentPath, "panorama", "images", "map_icons", $"map_icon_{addonName}.svg");
        Directory.CreateDirectory(Path.GetDirectoryName(target)!);
        var staged = $"{target}.tmp";
        await File.WriteAllTextAsync(staged, document.ToString(), cancellationToken);
        if (File.Exists(target))
        {
            File.Copy(target, $"{target}.bak", overwrite: true);
        }

        File.Move(staged, target, overwrite: true);
        return true;
    }

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
