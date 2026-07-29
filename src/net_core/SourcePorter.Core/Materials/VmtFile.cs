using ValveKeyValue;

namespace SourcePorter.Core.Materials;

/// <summary>
/// A parsed Source 1 <c>.vmt</c> material: its shader name plus a case-insensitive bag of
/// scalar parameters. Ported from the <c>VMT</c> class in kristiker/source1import's
/// <c>materials_import.py</c> — the same normalisations the converter relies on:
/// <list type="bullet">
///   <item><c>$bumpmap</c> is folded into <c>$normalmap</c>.</item>
///   <item>shader-name suffixes <c>_dx9</c>/<c>_hdr</c> and prefix <c>sdk_</c> are stripped.</item>
///   <item><c>patch</c> materials resolve their <c>include</c> then apply <c>replace</c>/<c>insert</c>.</item>
/// </list>
/// Only top-level scalar parameters are retained (proxies and other nested blocks are skipped —
/// the VMT→VMAT mapping operates on scalars). Keys are lower-cased; values are trimmed.
/// </summary>
public sealed class VmtFile
{
    private readonly Dictionary<string, string> _kv = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>The resolved shader name, lower-cased (e.g. <c>lightmappedgeneric</c>).</summary>
    public string Shader { get; private set; } = "error";

    /// <summary>Case-insensitive view of the material's scalar parameters.</summary>
    public IReadOnlyDictionary<string, string> Parameters => _kv;

    /// <summary>Gets a parameter value, or empty string if absent (mirrors the Python KV's falsy default).</summary>
    public string this[string key] => _kv.TryGetValue(key, out var v) ? v : string.Empty;

    /// <summary>The material's path (as supplied to <see cref="Load"/>/<see cref="Parse"/>), or null.</summary>
    public string? SourcePath { get; private set; }

    /// <summary>
    /// Whether this is a tool/editor material. Ported from the Python <c>is_tool_material</c>: a
    /// material under <c>materials/tools/</c> whose filename starts with <c>tools</c> (e.g.
    /// <c>toolsnodraw</c>, <c>toolsclip</c>). <b>Not</b> just "has a <c>%compile*</c> key" — real
    /// surfaces like water carry <c>%compilewater</c> yet are not tool materials. Requires
    /// <see cref="SourcePath"/> to be set.
    /// </summary>
    public bool IsToolMaterial => IsToolMaterialPath(SourcePath);

    /// <summary>The path-based tool-material test (see <see cref="IsToolMaterial"/>), usable without a parsed file.</summary>
    public static bool IsToolMaterialPath(string? path)
    {
        if (string.IsNullOrEmpty(path))
            return false;
        var p = path.Replace('\\', '/').ToLowerInvariant();
        var name = p[(p.LastIndexOf('/') + 1)..];
        return p.Contains("/tools/") && name.StartsWith("tools", StringComparison.Ordinal);
    }

    private VmtFile() { }

    /// <summary>Parses a <c>.vmt</c> from disk. <paramref name="includeResolver"/> maps a material-relative
    /// include path (as written in a <c>patch</c>'s <c>include</c> key) to that file's text, enabling
    /// patch resolution; pass null to skip include resolution.</summary>
    public static VmtFile Load(string path, Func<string, string?>? includeResolver = null)
        => Parse(File.ReadAllText(path), includeResolver, path);

    /// <summary>Parses a <c>.vmt</c> from its text content. <paramref name="sourcePath"/> (when known)
    /// drives <see cref="IsToolMaterial"/>.</summary>
    public static VmtFile Parse(string text, Func<string, string?>? includeResolver = null, string? sourcePath = null)
    {
        var root = Deserialize(text);
        var vmt = new VmtFile { SourcePath = sourcePath };
        if (root is null)
            return vmt;

        var shader = NormalizeShader(root.Name);

        // A "patch" material is a thin override of an included base material.
        if (shader == "patch")
        {
            var includePath = ScalarValue(root, "include");
            if (includePath is not null && includeResolver?.Invoke(includePath) is { } includedText)
            {
                var baseVmt = Parse(includedText, includeResolver);
                vmt.Shader = baseVmt.Shader;
                foreach (var (k, v) in baseVmt._kv)
                    vmt._kv[k] = v;
            }

            // "replace" and "insert" blocks both override/add keys on the base.
            foreach (var block in new[] { "replace", "insert" })
                if (FindChild(root, block) is { } overrides)
                    foreach (var entry in overrides)
                        AddScalar(vmt._kv, entry);

            vmt.Normalize();
            return vmt;
        }

        vmt.Shader = shader;
        foreach (var entry in root)
            AddScalar(vmt._kv, entry);

        vmt.Normalize();
        return vmt;
    }

    private void Normalize()
    {
        // $bumpmap is the legacy spelling of $normalmap.
        if (_kv.TryGetValue("$bumpmap", out var bump))
        {
            _kv.TryAdd("$normalmap", bump);
            _kv.Remove("$bumpmap");
        }

        // %compileclip expands to the player/npc clip pair.
        if (_kv.TryGetValue("%compileclip", out var clip))
        {
            _kv["%playerclip"] = clip;
            _kv["%compilenpcclip"] = clip;
            _kv.Remove("%compileclip");
        }
    }

    private static void AddScalar(Dictionary<string, string> kv, KVObject entry)
    {
        // Skip nested blocks (proxies, DirectX-level subkeys, etc.) — the mapping is scalar-only.
        if (entry.Value.ValueType == KVValueType.Collection)
            return;

        var key = entry.Name.ToLowerInvariant();

        // "?$key" platform-conditional keys keep only the key after '?'.
        var q = key.IndexOf('?');
        if (q >= 0)
            key = key[(q + 1)..];

        kv[key] = entry.Value.ToString(System.Globalization.CultureInfo.InvariantCulture)?.Trim() ?? string.Empty;
    }

    private static string NormalizeShader(string? name)
    {
        if (string.IsNullOrEmpty(name))
            return "error";
        var s = name.ToLowerInvariant();
        if (s.StartsWith("sdk_", StringComparison.Ordinal))
            s = s[4..];
        if (s.EndsWith("_dx9", StringComparison.Ordinal))
            s = s[..^4];
        if (s.EndsWith("_hdr", StringComparison.Ordinal))
            s = s[..^4];
        return s;
    }

    private static KVObject? Deserialize(string text)
    {
        try
        {
            using var stream = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(text));
            return KVSerializer.Create(KVSerializationFormat.KeyValues1Text).Deserialize(stream);
        }
        catch (Exception ex) when (ex is KeyValueException or IOException or InvalidDataException)
        {
            return null;
        }
    }

    private static KVObject? FindChild(KVObject parent, string name)
    {
        if (parent.Value.ValueType != KVValueType.Collection)
            return null;
        foreach (var child in parent)
            if (string.Equals(child.Name, name, StringComparison.OrdinalIgnoreCase))
                return child;
        return null;
    }

    private static string? ScalarValue(KVObject parent, string name)
    {
        var child = FindChild(parent, name);
        if (child is null && parent.Value.ValueType == KVValueType.Collection)
            foreach (var c in parent)
                if (string.Equals(c.Name, name, StringComparison.OrdinalIgnoreCase) && c.Value.ValueType != KVValueType.Collection)
                    return c.Value.ToString(System.Globalization.CultureInfo.InvariantCulture);
        return child?.Value.ToString(System.Globalization.CultureInfo.InvariantCulture);
    }
}
