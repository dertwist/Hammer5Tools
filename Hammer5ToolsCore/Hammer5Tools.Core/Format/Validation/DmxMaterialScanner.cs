using System.Text;
using System.Text.RegularExpressions;
using DM = Datamodel.Datamodel;

namespace Hammer5Tools.Core.Format.Validation;

/// <summary>
/// Extracts the material references a Source 2 model <c>.dmx</c> mesh file uses, by
/// <b>structurally</b> walking its DMX element graph with the <c>Datamodel.NET</c> library
/// and performing deep text/binary regex scanning.
/// </summary>
public static partial class DmxMaterialScanner
{
    private static readonly string[] MaterialAttrKeys = [
        "material", "mtlName", "materialName", "name", "mtl",
        "m_material", "material_name", "m_strMaterial", "m_pMaterial"
    ];

    /// <summary>
    /// Loads <paramref name="dmxPath"/> and returns distinct material paths
    /// (<c>materials/…/foo.vmat</c>) referenced by its model meshes — normalized, forward-slashed.
    /// </summary>
    public static IReadOnlyList<string> Scan(string dmxPath)
    {
        var found = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (!File.Exists(dmxPath))
            return [];

        byte[] rawBytes;
        try
        {
            rawBytes = File.ReadAllBytes(dmxPath);
        }
        catch
        {
            return [];
        }

        // 1. Structural Datamodel.NET scan
        try
        {
            var model = DM.Load(rawBytes, Datamodel.Codecs.DeferredMode.Disabled);
            if (model.Root is not null)
            {
                var visited = new HashSet<Datamodel.Element>();
                Walk(model.Root, found, visited);
            }
        }
        catch
        {
            // Fall back to regex scan below
        }

        // 2. Text/binary regex scan fallback to ensure any embedded material paths are captured
        var rawText = Encoding.Latin1.GetString(rawBytes);
        foreach (Match m in DmxMaterialRegex().Matches(rawText))
        {
            var norm = NormalizeMaterialPath(m.Value);
            if (norm is not null)
                found.Add(norm);
        }

        return found.ToList();
    }

    /// <summary>Extracts the distinct material paths from a loaded DMX model graph.</summary>
    public static IReadOnlyList<string> Extract(DM model)
    {
        var found = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var visited = new HashSet<Datamodel.Element>();
        if (model.Root is not null)
            Walk(model.Root, found, visited);
        return found.ToList();
    }

    private static void Walk(Datamodel.Element e, HashSet<string> found, HashSet<Datamodel.Element> visited)
    {
        if (!visited.Add(e))
            return;

        // Check attributes on current element
        InspectElementAttributes(e, found);

        foreach (var kv in e)
        {
            if (kv.Value is string s)
            {
                var norm = NormalizeMaterialPath(s);
                if (norm is not null)
                    found.Add(norm);
            }
            else if (kv.Value is Datamodel.Element child)
            {
                Walk(child, found, visited);
            }
            else if (kv.Value is Datamodel.ElementArray arr)
            {
                foreach (var x in arr)
                {
                    if (x is not null)
                        Walk(x, found, visited);
                }
            }
        }
    }

    private static void InspectElementAttributes(Datamodel.Element e, HashSet<string> found)
    {
        foreach (var key in MaterialAttrKeys)
        {
            if (!e.ContainsKey(key))
                continue;

            var val = e[key];
            if (val is string s)
            {
                var norm = NormalizeMaterialPath(s);
                if (norm is not null)
                    found.Add(norm);
            }
            else if (val is Datamodel.Element matElem)
            {
                foreach (var matKey in MaterialAttrKeys)
                {
                    if (matElem.ContainsKey(matKey) && matElem[matKey] is string matStr)
                    {
                        var norm = NormalizeMaterialPath(matStr);
                        if (norm is not null)
                            found.Add(norm);
                    }
                }
            }
        }
    }

    /// <summary>Normalizes raw material strings into standard materials/…/foo.vmat paths.</summary>
    public static string? NormalizeMaterialPath(string raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;

        var path = raw.Replace('\\', '/').Trim();
        path = path.TrimStart('/', '.');

        // Physics tags like "solid$default" are skipped
        if (path.Contains('$') || path.Contains('#'))
            return null;

        var hasMatRoot = path.StartsWith("materials/", StringComparison.OrdinalIgnoreCase);

        // Require either materials/ prefix or .vmat/.vmt extension or multi-segment path
        if (!hasMatRoot && !path.EndsWith(".vmat", StringComparison.OrdinalIgnoreCase) && !path.EndsWith(".vmt", StringComparison.OrdinalIgnoreCase))
        {
            if (!path.Contains('/'))
                return null;
        }

        if (path.EndsWith(".vmt", StringComparison.OrdinalIgnoreCase))
            path = path[..^4] + ".vmat";
        else if (!path.EndsWith(".vmat", StringComparison.OrdinalIgnoreCase))
            path += ".vmat";

        if (!path.StartsWith("materials/", StringComparison.OrdinalIgnoreCase))
            path = "materials/" + path;

        return path;
    }

    // Ported Source 1 meshes bake material paths with backslashes (e.g.
    // "materials\anubis\models\foliage\ivy01.vmat"); the binary_seqids DMX encoding
    // these compile to also has no Datamodel.NET codec, so the structural walk above
    // always throws and every mesh falls through to this regex — it must accept both
    // separators or these never get caught at all.
    [GeneratedRegex(@"(?:materials|models)[/\\][\w./\\-]+?\.(?:vmat|vmt)", RegexOptions.IgnoreCase)]
    private static partial Regex DmxMaterialRegex();
}
