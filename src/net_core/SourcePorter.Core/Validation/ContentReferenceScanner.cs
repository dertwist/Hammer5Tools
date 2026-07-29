using System.Text;
using System.Text.RegularExpressions;

namespace SourcePorter.Core.Validation;

/// <summary>
/// Extracts the asset dependencies a content file (<c>.vmap</c>/<c>.vmdl</c>/<c>.vmat</c>)
/// references — prefab <c>.vmap</c>s, materials, models, mesh sources, and textures — whether
/// the file is text or binary KV3/DMX. CS2 stores referenced paths as plain strings in both
/// encodings (a main <c>.vmap</c> is text KV2; its prefab <c>.vmap</c>s are binary DMX), so a
/// byte-safe scan for the known asset roots surfaces them reliably. Verified against real
/// binary prefab <c>.vmap</c>s (357 model + 193 material refs extracted cleanly).
/// </summary>
public static partial class ContentReferenceScanner
{
    /// <summary>What an extracted reference points at — drives how its existence is checked.</summary>
    public enum ReferenceKind
    {
        /// <summary>A prefab <c>.vmap</c> the map composes in (from <c>map_asset_references</c>).</summary>
        PrefabMap,

        /// <summary>A material (<c>.vmat</c>).</summary>
        Material,

        /// <summary>A model (<c>.vmdl</c>).</summary>
        Model,

        /// <summary>A model's mesh source (<c>.dmx</c>/<c>.fbx</c>/<c>.smd</c>/<c>.obj</c>) — loose-only.</summary>
        MeshSource,

        /// <summary>A texture a <c>.vmat</c> references (<c>.tga</c>/<c>.png</c>/<c>.psd</c>) — loose-only.</summary>
        Texture,
    }

    /// <summary>One referenced asset path with its kind (forward-slashed, content-relative).</summary>
    public sealed record Reference(string Path, ReferenceKind Kind);

    /// <summary>Scans a content file's bytes for the asset paths it references.</summary>
    public static IReadOnlyList<Reference> Scan(string filePath) =>
        Extract(Encoding.Latin1.GetString(File.ReadAllBytes(filePath)));

    private static ReferenceKind? Classify(ref string p)
    {
        if (p.StartsWith("maps/", StringComparison.OrdinalIgnoreCase) && p.EndsWith(".vmap", StringComparison.OrdinalIgnoreCase))
            return ReferenceKind.PrefabMap;
        if (p.StartsWith("materials/", StringComparison.OrdinalIgnoreCase) && p.EndsWith(".vmat", StringComparison.OrdinalIgnoreCase))
            return ReferenceKind.Material;
        if (p.StartsWith("materials/", StringComparison.OrdinalIgnoreCase) && p.EndsWith(".vmt", StringComparison.OrdinalIgnoreCase))
        {
            p = p[..^4] + ".vmat";
            return ReferenceKind.Material;
        }
        if (p.StartsWith("materials/", StringComparison.OrdinalIgnoreCase) && IsTextureExt(p))
            return ReferenceKind.Texture;
        if (p.StartsWith("models/", StringComparison.OrdinalIgnoreCase) && p.EndsWith(".vmdl", StringComparison.OrdinalIgnoreCase))
            return ReferenceKind.Model;
        if (p.StartsWith("models/", StringComparison.OrdinalIgnoreCase))
            return ReferenceKind.MeshSource; // .dmx/.fbx/.smd/.obj under models/
        return null;
    }

    /// <summary>Extracts the distinct asset references embedded in <paramref name="text"/>.</summary>
    public static IReadOnlyList<Reference> Extract(string text)
    {
        var found = new Dictionary<string, Reference>(StringComparer.OrdinalIgnoreCase);
        foreach (Match m in ReferenceRegex().Matches(text))
        {
            var path = m.Value.Replace('\\', '/');
            var kind = Classify(ref path);
            if (kind is not null)
                found.TryAdd(path, new Reference(path, kind.Value));
        }
        return found.Values.ToList();
    }

    private static bool IsTextureExt(string p) =>
        p.EndsWith(".tga", StringComparison.OrdinalIgnoreCase)
        || p.EndsWith(".png", StringComparison.OrdinalIgnoreCase)
        || p.EndsWith(".psd", StringComparison.OrdinalIgnoreCase);

    // A path under one of the asset roots ending in a known extension. Non-greedy so it
    // stops at the first extension; the asset roots and extensions keep false matches out
    // of binary noise (paths are null/length separated, so the class can't run across them).
    // Ported Source 1 content bakes some paths with backslashes, so the root prefix must
    // accept either separator, not just '/'.
    [GeneratedRegex(@"(?:maps|materials|models)[/\\][\w./\\-]+?\.(?:vmap|vmat|vmdl|vmt|dmx|fbx|smd|obj|tga|png|psd)", RegexOptions.IgnoreCase)]
    private static partial Regex ReferenceRegex();
}
