namespace Hammer5Tools.Core.IO.LoadingScreens;

using System.Diagnostics;
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

    public async Task<bool> CaptureAddonScreenshotsAsync(string vmapPath, string gamePath, string contentPath, bool history, CancellationToken cancellationToken = default)
    {
        var cameras = await ExtractCamerasFromVmapAsync(vmapPath, cancellationToken);
        if (cameras.Count == 0 || !CommandService.IsConnected)
        {
            return false;
        }

        var timestamp = DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss", CultureInfo.InvariantCulture);
        var relativeDirectory = history
            ? Path.Combine("screenshots", "Hammer5Tools", "History", timestamp)
            : Path.Combine("screenshots", "Hammer5Tools", "LoadingScreen");
        var screenshotDirectory = Path.Combine(gamePath, relativeDirectory);
        if (!history && Directory.Exists(screenshotDirectory))
        {
            Directory.Delete(screenshotDirectory, recursive: true);
        }

        Directory.CreateDirectory(screenshotDirectory);
        var commands = new List<string>
        {
            "cl_firstperson_legs 0", "sv_cheats 1", "bot_kick", "noclip 1",
            "ent_fire cmd kill", "ent_create point_servercommand {targetname cmd}",
            $"screenshot_subdir {relativeDirectory}"
        };

        const float eyeHeight = 70f;
        var tick = 1f / 64f;
        for (var index = 0; index < cameras.Count; index++)
        {
            var camera = cameras[index];
            var delay = index * tick * 10 + 0.1f;
            var name = Regex.Replace(camera.Name, "[^A-Za-z0-9_.-]", "_").Trim('_');
            if (string.IsNullOrWhiteSpace(name))
            {
                name = $"{Path.GetFileNameWithoutExtension(vmapPath)}_cam{index}";
            }

            var pos = $"{camera.Position.X.ToString("0.####", CultureInfo.InvariantCulture)} {camera.Position.Y.ToString("0.####", CultureInfo.InvariantCulture)} {(camera.Position.Z - eyeHeight).ToString("0.####", CultureInfo.InvariantCulture)}";
            var angles = $"{camera.Angles.X.ToString("0.####", CultureInfo.InvariantCulture)} {camera.Angles.Y.ToString("0.####", CultureInfo.InvariantCulture)} {camera.Angles.Z.ToString("0.####", CultureInfo.InvariantCulture)}";
            commands.Add($"ent_fire worldent addoutput \"OnUser1>cmd>command>screenshot_prefix {name}>{delay:0.####}>1\"");
            commands.Add($"ent_fire worldent addoutput \"OnUser1>cmd>command>setpos {pos}>{delay:0.####}>1\"");
            commands.Add($"ent_fire worldent addoutput \"OnUser1>cmd>command>setang {angles}>{delay:0.####}>1\"");
            commands.Add($"ent_fire worldent addoutput \"OnUser1>cmd>command>r_always_render_all_windows true>{delay:0.####}>1\"");
            commands.Add($"ent_fire worldent addoutput \"OnUser1>cmd>command>png_screenshot>{delay + tick * 2:0.####}>1\"");
        }

        var finalDelay = (cameras.Count - 1) * tick * 10 + 1;
        commands.Add($"ent_fire worldent addoutput \"OnUser1>cmd>command>r_drawviewmodel 1;cl_drawhud 1;r_drawpanorama 1;noclip 0>{finalDelay:0.####}>1\"");
        commands.Add("r_drawviewmodel 0");
        commands.Add("cl_drawhud 0");
        commands.Add("r_drawpanorama 0");
        commands.Add($"ent_fire worldent addoutput \"OnUser1>cmd>command>r_always_render_all_windows false>{finalDelay:0.####}>1\"");
        commands.Add("ent_fire worldent FireUser1");
        if (!await CommandService.SendCommandsAsync(commands, cancellationToken))
        {
            return false;
        }

        await Task.Delay(TimeSpan.FromSeconds(Math.Max(3, cameras.Count * (10d / 64) + 2)), cancellationToken);
        if (history)
        {
            var source = screenshotDirectory;
            var destination = Path.Combine(contentPath, "panorama", "history_screenshots", timestamp);
            Directory.CreateDirectory(destination);
            foreach (var file in Directory.EnumerateFiles(source))
            {
                File.Copy(file, Path.Combine(destination, Path.GetFileName(file)), overwrite: true);
            }
        }

        return true;
    }

    public async Task<bool> ApplyLoadingScreenImagesAsync(string addonName, string sourceDirectory, bool deleteExisting, bool includeCameraName, CancellationToken cancellationToken = default)
    {
        var cs2Root = Cs2Locator.FindCs2Path();
        if (string.IsNullOrWhiteSpace(cs2Root) || !Directory.Exists(sourceDirectory))
        {
            return false;
        }

        var addonContentPath = Core.Cs2.Cs2Paths.GetAddonContentPath(cs2Root, addonName);
        var sourceRoot = Path.Combine(addonContentPath, "panorama", "images", "map_icons", "screenshots");
        var gameRoot = Path.Combine(Core.Cs2.Cs2Paths.GetAddonGamePath(cs2Root, addonName), "panorama", "images", "map_icons", "screenshots");
        var resolutions = new[] { (Name: "1080p", Height: 1080), (Name: "720p", Height: 720), (Name: "360p", Height: 360) };
        var files = Directory.EnumerateFiles(sourceDirectory)
            .Where(file => Path.GetExtension(file).ToLowerInvariant() is ".png" or ".jpg" or ".jpeg" or ".bmp" or ".tga")
            .OrderBy(file => file, StringComparer.OrdinalIgnoreCase)
            .ToArray();
        if (files.Length == 0) return false;
        if (deleteExisting)
        {
            foreach (var resolution in resolutions)
            {
                var sourceDirectoryPath = Path.Combine(sourceRoot, resolution.Name);
                if (Directory.Exists(sourceDirectoryPath)) Directory.Delete(sourceDirectoryPath, recursive: true);
                var gameDirectoryPath = Path.Combine(gameRoot, resolution.Name);
                if (Directory.Exists(gameDirectoryPath)) Directory.Delete(gameDirectoryPath, recursive: true);
            }
        }

        var success = true;
        var compiledCount = 0;
        for (var index = 0; index < files.Length; index++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var file = files[index];
            var outputName = index == 0 ? $"{addonName}_png" : $"{addonName}_{index}_png";
            var cameraName = includeCameraName ? GetCameraName(file, addonName) : string.Empty;
            using var bitmap = SkiaSharp.SKBitmap.Decode(file);
            if (bitmap is null) continue;
            foreach (var resolution in resolutions)
            {
                var targetDirectory = Path.Combine(sourceRoot, resolution.Name);
                Directory.CreateDirectory(targetDirectory);
                var output = Path.Combine(targetDirectory, $"{outputName}.vtex");
                if (!deleteExisting && File.Exists(output)) continue;
                var imageWidth = Math.Max(1, (int)MathF.Round(bitmap.Width * (resolution.Height / (float)bitmap.Height)));
                using var scaled = bitmap.Resize(new SkiaSharp.SKImageInfo(imageWidth, resolution.Height), new SkiaSharp.SKSamplingOptions(SkiaSharp.SKFilterMode.Linear, SkiaSharp.SKMipmapMode.Linear));
                if (scaled is null) continue;
                if (!string.IsNullOrWhiteSpace(cameraName))
                {
                    using var canvas = new SkiaSharp.SKCanvas(scaled);
                    using var paint = new SkiaSharp.SKPaint { Color = SkiaSharp.SKColors.White, IsAntialias = true };
                    using var font = new SkiaSharp.SKFont { Size = Math.Max(8, resolution.Height * 31f / 1080f) };
                    canvas.DrawText(cameraName, resolution.Height * 46f / 1080f, resolution.Height * 1010f / 1080f, SkiaSharp.SKTextAlign.Left, font, paint);
                }
                var imagePath = Path.Combine(targetDirectory, $"{outputName}.png");
                using var image = SkiaSharp.SKImage.FromBitmap(scaled);
                using var data = image.Encode(SkiaSharp.SKEncodedImageFormat.Png, 100);
                await WriteAtomicallyAsync(imagePath, data.ToArray(), cancellationToken);
                var relativeImagePath = Path.GetRelativePath(addonContentPath, imagePath).Replace('\\', '/');
                var vtex = $$"""
                    <!-- dmx encoding keyvalues2_noids 1 format vtex 1 -->
                    "CDmeVtex"
                    {
                        "m_inputTextureArray" "element_array"
                        [
                            "CDmeInputTexture"
                            {
                                "m_name" "string" "SheetTexture"
                                "m_fileName" "string" "{{relativeImagePath}}"
                                "m_colorSpace" "string" "linear"
                                "m_typeString" "string" "2D"
                            }
                        ]
                        "m_outputTypeString" "string" "2D"
                        "m_outputFormat" "string" "BC7"
                        "m_bNoLod" "bool" "1"
                    }
                    """;
                await WriteAtomicallyAsync(output, Encoding.UTF8.GetBytes(vtex), cancellationToken);
                var result = await ResourceCompiler.CompileAssetAsync(output, addonName: addonName, cancellationToken);
                success &= result.Success;
                compiledCount++;
            }
        }

        return compiledCount > 0 && success;
    }

    private static string GetCameraName(string path, string addonName)
    {
        var stem = Path.GetFileNameWithoutExtension(path);
        stem = Regex.Replace(stem, @"_\d+$", string.Empty);
        var cameraMatch = Regex.Match(stem, @"cam(?:era)?[\s_]*\d+", RegexOptions.IgnoreCase);
        if (cameraMatch.Success)
        {
            var camera = cameraMatch.Value.Replace("_", string.Empty);
            return Regex.IsMatch(camera, @"^cam(?:era)?\d*$", RegexOptions.IgnoreCase) ? string.Empty : camera;
        }
        foreach (var prefix in new[] { $"{addonName}_", $"de_{addonName}_", $"cs_{addonName}_", $"ar_{addonName}_" })
        {
            if (stem.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            {
                stem = stem[prefix.Length..];
                break;
            }
        }

        stem = Regex.Replace(stem, @"^(?:de|cs|ar|cp)_[A-Za-z0-9]+_", string.Empty, RegexOptions.IgnoreCase);
        return Regex.IsMatch(stem, @"^cam(?:era)?[\s_]*\d*$", RegexOptions.IgnoreCase) ? string.Empty : stem;
    }

    private static async Task WriteAtomicallyAsync(string path, byte[] content, CancellationToken cancellationToken)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var stagedPath = $"{path}.h5t-{Guid.NewGuid():N}.tmp";
        try
        {
            await File.WriteAllBytesAsync(stagedPath, content, cancellationToken);
            if (File.Exists(path)) File.Copy(path, $"{path}.bak", overwrite: true);
            File.Move(stagedPath, path, overwrite: true);
        }
        finally
        {
            if (File.Exists(stagedPath)) File.Delete(stagedPath);
        }
    }

    public async Task<string> ExportTimelineAsync(IReadOnlyList<string> imagePaths, string outputDirectory, string baseName, string format, string quality, CancellationToken cancellationToken = default)
    {
        if (imagePaths.Count == 0)
        {
            throw new InvalidOperationException("No images are available for export.");
        }

        var executable = OperatingSystem.IsWindows() ? "ffmpeg.exe" : "ffmpeg";
        var listPath = Path.Combine(Path.GetTempPath(), $"h5t-timeline-{Guid.NewGuid():N}.txt");
        Directory.CreateDirectory(outputDirectory);
        var extension = format.ToLowerInvariant() switch { "webp" => ".webp", "mp4" => ".mp4", _ => ".gif" };
        var output = Path.Combine(outputDirectory, $"{baseName}_timeline{extension}");
        try
        {
            var lines = imagePaths.Select(path => $"file '{Path.GetFullPath(path).Replace('\\', '/').Replace("'", "'\\''")}'\nduration 0.5").ToList();
            lines.Add($"file '{Path.GetFullPath(imagePaths[^1]).Replace('\\', '/').Replace("'", "'\\''")}'");
            await File.WriteAllLinesAsync(listPath, lines, cancellationToken);
            var start = new ProcessStartInfo(executable) { UseShellExecute = false, RedirectStandardError = true, CreateNoWindow = true };
            start.ArgumentList.Add("-y");
            start.ArgumentList.Add("-f");
            start.ArgumentList.Add("concat");
            start.ArgumentList.Add("-safe");
            start.ArgumentList.Add("0");
            start.ArgumentList.Add("-i");
            start.ArgumentList.Add(listPath);
            start.ArgumentList.Add("-vf");
            start.ArgumentList.Add("fps=2,scale=trunc(iw/2)*2:trunc(ih/2)*2:flags=lanczos");
            if (extension == ".mp4")
            {
                start.ArgumentList.Add("-c:v"); start.ArgumentList.Add("libx264");
                start.ArgumentList.Add("-crf"); start.ArgumentList.Add(quality switch { "Low" => "32", "Medium" => "23", _ => "18" });
                start.ArgumentList.Add("-pix_fmt"); start.ArgumentList.Add("yuv420p");
            }
            else if (extension == ".webp")
            {
                start.ArgumentList.Add("-c:v"); start.ArgumentList.Add("libwebp");
                start.ArgumentList.Add("-q:v"); start.ArgumentList.Add(quality switch { "Low" => "50", "Medium" => "75", _ => "95" });
                start.ArgumentList.Add("-loop"); start.ArgumentList.Add("0");
            }
            else
            {
                start.ArgumentList.Add("-loop"); start.ArgumentList.Add("0");
            }
            start.ArgumentList.Add(output);
            using var process = Process.Start(start) ?? throw new InvalidOperationException("Could not start ffmpeg.");
            using var cancellationRegistration = cancellationToken.Register(() =>
            {
                try
                {
                    if (!process.HasExited) process.Kill(entireProcessTree: true);
                }
                catch (InvalidOperationException)
                {
                }
            });
            var errorTask = process.StandardError.ReadToEndAsync(cancellationToken);
            await process.WaitForExitAsync(cancellationToken);
            if (process.ExitCode != 0)
            {
                throw new InvalidOperationException((await errorTask).Trim());
            }

            return output;
        }
        finally
        {
            if (File.Exists(listPath)) File.Delete(listPath);
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

    public Task<bool> ApplyMapIconAsync(string addonContentPath, string addonName, string svgPath, CancellationToken cancellationToken = default) =>
        ApplyMapIconAsync(addonContentPath, addonName, svgPath, true, cancellationToken);

    public async Task<bool> ApplyMapIconAsync(string addonContentPath, string addonName, string svgPath, bool fitContent, CancellationToken cancellationToken = default)
    {
        var text = await File.ReadAllTextAsync(svgPath, cancellationToken);
        using var reader = System.Xml.XmlReader.Create(new StringReader(text), new System.Xml.XmlReaderSettings { DtdProcessing = System.Xml.DtdProcessing.Prohibit });
        var document = System.Xml.Linq.XDocument.Load(reader);
        if (document.Root?.Name.LocalName != "svg")
        {
            throw new InvalidDataException("Select an SVG document.");
        }

        if (fitContent) FitSvgContent(document.Root);

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

    private static void FitSvgContent(System.Xml.Linq.XElement root)
    {
        var rawViewBox = root.Attribute("viewBox")?.Value;
        var viewBox = (rawViewBox ?? "0 0 32 32").Split([' ', ','], StringSplitOptions.RemoveEmptyEntries);
        var x = 0f;
        var y = 0f;
        var width = 32f;
        var height = 32f;
        if (rawViewBox is null && float.TryParse((root.Attribute("width")?.Value ?? string.Empty).Replace("px", string.Empty, StringComparison.OrdinalIgnoreCase), CultureInfo.InvariantCulture, out var legacyWidth) && legacyWidth > 0)
        {
            width = height = legacyWidth;
        }
        if (viewBox.Length != 4 || !float.TryParse(viewBox[0], CultureInfo.InvariantCulture, out x) ||
            !float.TryParse(viewBox[1], CultureInfo.InvariantCulture, out y) ||
            !float.TryParse(viewBox[2], CultureInfo.InvariantCulture, out width) ||
            !float.TryParse(viewBox[3], CultureInfo.InvariantCulture, out height) || width <= 0 || height <= 0)
        {
            x = y = 0;
            width = height = 32;
        }

        var sx = 32 / width;
        var sy = 32 / height;
        var ns = root.Name.Namespace;
        var group = new System.Xml.Linq.XElement(ns + "g", new System.Xml.Linq.XAttribute("transform", FormattableString.Invariant($"matrix({sx:0.######},0,0,{sy:0.######},{-x * sx:0.######},{-y * sy:0.######})")));
        var structural = new HashSet<string>(["defs", "style", "title", "desc", "metadata", "script"], StringComparer.OrdinalIgnoreCase);
        foreach (var hidden in root.Descendants().Where(element => element.Attribute("display")?.Value == "none" || (element.Attribute("style")?.Value ?? string.Empty).Replace(" ", string.Empty).Contains("display:none", StringComparison.OrdinalIgnoreCase)).ToArray())
        {
            hidden.Remove();
        }

        foreach (var element in root.Elements().ToArray())
        {
            if (structural.Contains(element.Name.LocalName)) continue;
            element.Remove();
            group.Add(element);
        }

        root.Add(group);
        root.SetAttributeValue("width", "32");
        root.SetAttributeValue("height", "32");
        root.SetAttributeValue("viewBox", "0 0 32 32");
        root.SetAttributeValue("version", "1.1");
    }

    public async Task<string> LoadMapDescriptionAsync(string addonGamePath, string mapName, CancellationToken cancellationToken = default)
    {
        var path = Path.Combine(addonGamePath, "maps", $"{mapName}.txt");
        if (!File.Exists(path)) return string.Empty;
        var lines = await File.ReadAllLinesAsync(path, cancellationToken);
        return lines.Length > 1 ? string.Join(Environment.NewLine, lines.Skip(1)).Trim() : string.Empty;
    }

    public async Task<bool> SaveMapDescriptionAsync(string addonGamePath, string mapName, string description, CancellationToken cancellationToken = default)
    {
        var path = Path.Combine(addonGamePath, "maps", $"{mapName}.txt");
        var directory = Path.GetDirectoryName(path)!;
        Directory.CreateDirectory(directory);
        var staged = $"{path}.tmp";
        try
        {
            await File.WriteAllTextAsync(staged, $"COMMUNITYMAPCREDITS:{Environment.NewLine}{description}", cancellationToken);
            if (File.Exists(path)) File.Copy(path, $"{path}.bak", overwrite: true);
            File.Move(staged, path, overwrite: true);
            return true;
        }
        catch
        {
            if (File.Exists(staged)) File.Delete(staged);
            throw;
        }
    }

    public async Task<int> ImportScreenshotsAsync(string targetDirectory, IReadOnlyList<string> sourcePaths, CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(targetDirectory);
        var count = 0;
        foreach (var source in sourcePaths.Where(IsImageFile))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (!File.Exists(source)) continue;
            var destination = Path.Combine(targetDirectory, Path.GetFileName(source));
            var suffix = 1;
            while (File.Exists(destination))
            {
                destination = Path.Combine(targetDirectory, $"{Path.GetFileNameWithoutExtension(source)} ({suffix++}){Path.GetExtension(source)}");
            }

            await using var input = File.OpenRead(source);
            await using var output = File.Create(destination);
            await input.CopyToAsync(output, cancellationToken);
            count++;
        }

        return count;
    }

    private static bool IsImageFile(string path) => Path.GetExtension(path).ToLowerInvariant() is ".png" or ".jpg" or ".jpeg" or ".bmp" or ".tga";

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
