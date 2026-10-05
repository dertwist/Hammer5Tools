using System.Text.Json.Nodes;
using Hammer5Tools.Core.Format.Resources;
using Hammer5Tools.Core.Format.SmartProps;
using Hammer5Tools.Core.Format.Vmap;
using Hammer5Tools.Core.IO.CompiledResource;

namespace Hammer5Tools.Core.IO;

internal static class SmartPropPreviewService
{
    public static string Load(string resource, string gameDirectory, string addon)
    {
        var contentRoot = ContentRoot(gameDirectory, addon);
        using var files = new VmapContentFiles(Path.Combine(contentRoot, resource), contentRoot, gameDirectory, addon);
        var root = files.ReadSmartProp(resource, out _);
        // Compiled resources may omit the source-only generic data type marker.
        if (root["generic_data_type"] is null && root["_class"] is null)
        {
            root["generic_data_type"] = "CSmartPropRoot";
        }
        return SmartPropEditorDocument.Validate(root.ToJsonString(VmapImportJsonContext.Default.Options));
    }

    public static SmartPropPreviewScene Build(string json, string gameDirectory, string addon, string? sourcePath, CancellationToken cancellationToken)
    {
        var root = JsonNode.Parse(SmartPropEditorDocument.Validate(json))!.AsObject();
        var contentRoot = ContentRoot(gameDirectory, addon);
        using var files = new VmapContentFiles(sourcePath ?? Path.Combine(contentRoot, "preview.vsmart"), contentRoot, gameDirectory, addon);
        var nested = files.ReadSmartPropDependencies(root);
        var result = SmartPropEvaluator.EvaluateJson(json, nested.ToJsonString(VmapImportJsonContext.Default.Options),
            new SmartPropEvaluationOptions(maximumModels: 10_000, cancellationToken: cancellationToken));
        using var reader = new CompiledModelReader(gameDirectory, addon);
        var cache = new Dictionary<(string Path, string? Group), CompiledModel?>();
        List<SmartPropPreviewInstance> instances = [];
        List<string> diagnostics = [.. files.Diagnostics, .. result.Diagnostics.Select(item => $"{item.Severity}: {item.Message}")];
        foreach (var model in result.Models)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var key = (model.ModelName, model.MaterialGroup);
            if (!cache.TryGetValue(key, out var geometry))
            {
                if (!string.IsNullOrWhiteSpace(gameDirectory) && !string.IsNullOrWhiteSpace(model.ModelName))
                {
                    var skin = 0;
                    if (model.MaterialGroup is { Length: > 0 } group)
                    {
                        var groups = reader.ReadMaterialGroups(model.ModelName);
                        if (groups.Value is { } names)
                        {
                            skin = Math.Max(0, names.ToList().IndexOf(group));
                        }
                    }
                    var loaded = reader.Read(model.ModelName, skin: skin);
                    geometry = loaded.Value;
                    diagnostics.AddRange(loaded.Diagnostics.Select(item => item.Message));
                }
                cache[key] = geometry;
            }
            instances.Add(new(model, geometry));
        }
        if (result.Models.Any(model => model.Deformer is not null))
        {
            diagnostics.Add("Mesh deformation is not yet rendered in the C# preview.");
        }
        return new(instances, diagnostics);
    }

    private static string ContentRoot(string gameDirectory, string addon)
    {
        var cleaned = string.IsNullOrWhiteSpace(gameDirectory) ? "." : gameDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        var install = Path.GetDirectoryName(Path.GetFullPath(cleaned))!;
        return string.IsNullOrWhiteSpace(addon) ? Path.Combine(install, "content", "csgo") : Path.Combine(install, "content", "csgo_addons", addon);
    }
}
