using System.Text.Json;
using System.Text.RegularExpressions;

namespace Hammer5Tools.Core.Format.AssetGroup;

internal static partial class AssetGroupTemplate
{
    private static readonly string[] MeshPrefixes =
    [
        "phys_", "col_", "hull_", "physics_", "collision_",
        "lod0_", "lod1_", "lod2_", "lod3_", "lod4_",
        "render_", "mesh_", "high_", "low_"
    ];

    private static readonly string[] MeshSuffixes =
    [
        "_phys", "_col", "_hull", "_collision", "_physics",
        "_lod0", "_lod1", "_lod2", "_lod3", "_lod4", "_lod_0", "_lod_1", "_lod_2",
        "_render", "_mesh", "_high", "_low"
    ];

    private static readonly string[] TextureSuffixes =
    [
        "_color", "_albedo", "_basecolor", "_c", "_diffuse", "_bc", "_alb", "_d",
        "_normal", "_norm", "_n", "_nrm", "_rough", "_roughness", "_r",
        "_ao", "_ambient", "_occlusion", "_metal", "_metallic", "_metalness", "_m",
        "_orm", "_rma", "_arm", "_srm", "_srmh", "_packed", "_masks", "_mask",
        "_height", "_disp", "_displacement", "_h", "_emissive", "_emission", "_emi", "_selfillum",
        "_opacity", "_opac", "_alpha", "_trans", "_translucency",
        "_tintmask", "_tint", "_transmission", "_sss", "_blendmask",
        "_color2", "_basecolor2", "_normal2", "_rough2", "_roughness2", "_metal2", "_ao2", "_orm2",
        "_color3", "_basecolor3", "_normal3", "_rough3", "_roughness3", "_metal3", "_ao3"
    ];

    public static string NormalizeName(string baseName, string sourceExtension, int algorithm)
    {
        if (algorithm == 1)
        {
            var separator = baseName.LastIndexOf('_');
            return separator > 0 ? baseName[..separator] : baseName;
        }

        var extension = sourceExtension.TrimStart('.').ToLowerInvariant();
        var cleaned = baseName;
        foreach (var prefix in MeshPrefixes)
        {
            if (cleaned.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            {
                cleaned = cleaned[prefix.Length..];
                break;
            }
        }

        var suffixes = MeshSuffixes.AsEnumerable();
        // Restrict mesh names only; preserve existing texture and standalone-helper grouping.
        if (extension is not ("fbx" or "obj" or "dmx" or "smd" or "vmdl" or "vsmart"))
        {
            suffixes = MeshSuffixes.Concat(TextureSuffixes);
        }

        foreach (var suffix in suffixes)
        {
            if (cleaned.EndsWith(suffix, StringComparison.OrdinalIgnoreCase))
            {
                cleaned = cleaned[..^suffix.Length];
                break;
            }
        }
        return cleaned.Length > 0 ? cleaned : baseName;
    }

    public static string Render(string requestJson)
    {
        using var document = JsonDocument.Parse(requestJson);
        var request = document.RootElement;
        var data = request.GetProperty("content").GetString() ?? "";
        var slots = ReadStrings(request, "slots");
        var skipped = request.TryGetProperty("skippedSlots", out var skippedJson)
            ? skippedJson.EnumerateArray().Select(item => item.GetString() ?? "").ToHashSet(StringComparer.Ordinal)
            : [];

        if (request.TryGetProperty("replacements", out var replacements))
        {
            if (replacements.ValueKind == JsonValueKind.Array)
            {
                foreach (var replacement in replacements.EnumerateArray())
                {
                    if (replacement.ValueKind == JsonValueKind.Object)
                    {
                        data = Replace(data, GetString(replacement, "from"), GetString(replacement, "to"));
                    }
                }
            }
            else if (replacements.ValueKind == JsonValueKind.Object)
            {
                foreach (var replacement in replacements.EnumerateObject())
                {
                    if (replacement.Value.TryGetProperty("replacement", out var pair))
                    {
                        data = Replace(data, pair[0].GetString() ?? "", pair[1].GetString() ?? "");
                    }
                }
            }
        }

        // Fixed reference materials may live outside the batch folder (including game/VPK assets).
        // Restore the entire path before expanding FOLDER_PATH, rather than relocating the material.
        foreach (var (slot, source) in ReadStrings(request, "materialSources"))
        {
            if (slots.TryGetValue(slot, out var assigned) && assigned.Length > 0)
            {
                continue;
            }
            if (source.Length == 0)
            {
                continue;
            }
            var token = slot.ToUpperInvariant();
            var path = source.Replace('\\', '/');
            data = data.Replace($"#$FOLDER_PATH$#/#${token}$#", path, StringComparison.Ordinal);
            data = SubstituteSlot(data, token, path);
        }

        data = data.Replace("#$FOLDER_PATH$#", GetString(request, "folder"), StringComparison.Ordinal);
        data = data.Replace("#$ASSET_NAME$#", GetString(request, "name"), StringComparison.Ordinal);
        foreach (var (slot, path) in slots)
        {
            if (!skipped.Contains(slot))
            {
                data = SubstituteSlot(data, slot.ToUpperInvariant(), path);
            }
        }

        return ConditionalBlock().Replace(data, match =>
        {
            var slot = match.Groups[1].Value.Trim().ToLowerInvariant();
            return !skipped.Contains(slot) && slots.TryGetValue(slot, out var path) && path.Length > 0
                ? match.Groups[2].Value : "";
        });
    }

    private static string SubstituteSlot(string data, string token, string path)
    {
        var normalized = path.Replace('\\', '/');
        var filename = normalized[(normalized.LastIndexOf('/') + 1)..];
        return data.Replace($"#${token}$#", filename, StringComparison.Ordinal)
            .Replace($"#${token}_NAME$#", Path.GetFileNameWithoutExtension(filename), StringComparison.Ordinal)
            .Replace($"#${token}_PATH$#", normalized, StringComparison.Ordinal);
    }

    private static string Replace(string data, string from, string to) =>
        from.Length > 0 ? data.Replace(from, to, StringComparison.Ordinal) : data;

    private static string GetString(JsonElement element, string name) =>
        element.TryGetProperty(name, out var value) ? value.GetString() ?? "" : "";

    private static Dictionary<string, string> ReadStrings(JsonElement root, string name) =>
        root.TryGetProperty(name, out var values)
            ? values.EnumerateObject().ToDictionary(item => item.Name, item => item.Value.GetString() ?? "")
            : [];

    [GeneratedRegex(@"<!--\s*IF\s+([A-Za-z0-9_]+)\s*-->([\s\S]*?)<!--\s*ENDIF\s*-->")]
    private static partial Regex ConditionalBlock();
}
