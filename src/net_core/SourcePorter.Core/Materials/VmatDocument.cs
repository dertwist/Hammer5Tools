using System.Linq;
using System.Text;

namespace SourcePorter.Core.Materials;

/// <summary>
/// An in-memory Source 2 <c>.vmat</c> being built by <see cref="VmtToVmatConverter"/>.
/// Mirrors the <c>VMAT</c> class from materials_import.py: a single <c>Layer0</c> block with a
/// <c>shader</c> plus ordered parameters, an optional <c>SystemAttributes</c> sub-block, and an
/// optional tool-material <c>Attributes</c> sub-block. Keys are written in insertion order (a
/// later write to an existing key overwrites the value but keeps its position), matching the
/// Python dict semantics the converter assumes.
/// </summary>
public sealed class VmatDocument
{
    private readonly List<string> _order = new();
    private readonly Dictionary<string, string> _values = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _systemAttributes = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _attributes = new(StringComparer.Ordinal);
    private readonly List<string> _rawBlocks = new();

    /// <summary>The Source 2 shader, including the <c>.vfx</c> extension (e.g. <c>csgo_lightmappedgeneric.vfx</c>).</summary>
    public string Shader { get; set; } = "error.vfx";

    /// <summary>Sets a Layer0 parameter (overwrites in place if it already exists).</summary>
    public void Set(string key, string value)
    {
        if (!_values.ContainsKey(key))
            _order.Add(key);
        _values[key] = value;
    }

    /// <summary>True if a Layer0 parameter is already present.</summary>
    public bool Has(string key) => _values.ContainsKey(key);

    /// <summary>Gets a Layer0 parameter, or null.</summary>
    public string? Get(string key) => _values.TryGetValue(key, out var v) ? v : null;

    /// <summary>Adds a <c>SystemAttributes { }</c> entry (e.g. PhysicsSurfaceProperties).</summary>
    public void SetSystemAttribute(string key, string value) => _systemAttributes[key] = value;

    /// <summary>Adds a tool-material <c>Attributes { }</c> entry.</summary>
    public void SetAttribute(string key, string value) => _attributes[key] = value;

    /// <summary>Appends a verbatim block inside <c>Layer0</c> (e.g. a preserved <c>legacy_import</c>).</summary>
    public void AddRawBlock(string blockText) => _rawBlocks.Add(blockText);

    /// <summary>Read-only view of the emitted parameters, in order.</summary>
    public IEnumerable<KeyValuePair<string, string>> Parameters
        => _order.Select(k => new KeyValuePair<string, string>(k, _values[k]));

    /// <summary>Serialises to Source 2 <c>.vmat</c> text.</summary>
    public string ToText(string? sourceComment = null)
    {
        var sb = new StringBuilder();
        sb.Append("// THIS FILE IS AUTO-GENERATED\n");
        if (sourceComment is not null)
            sb.Append("// Converted from ").Append(sourceComment).Append(" by SourcePorter\n");
        sb.Append('\n');
        sb.Append("Layer0\n{\n");
        sb.Append("\tshader \"").Append(Shader).Append("\"\n\n");

        foreach (var key in _order)
            sb.Append('\t').Append(key).Append(" \"").Append(_values[key]).Append("\"\n");

        AppendBlock(sb, "SystemAttributes", _systemAttributes);
        AppendBlock(sb, "Attributes", _attributes);

        foreach (var raw in _rawBlocks)
            sb.Append('\n').Append(Indent(raw)).Append('\n');

        sb.Append("}\n");
        return sb.ToString();
    }

    // Indents each line of a verbatim block by one tab so it nests cleanly under Layer0.
    private static string Indent(string block)
        => string.Join('\n', block.Replace("\r\n", "\n").Split('\n').Select(l => l.Length == 0 ? l : "\t" + l));

    private static void AppendBlock(StringBuilder sb, string name, Dictionary<string, string> block)
    {
        if (block.Count == 0)
            return;
        sb.Append('\n').Append('\t').Append(name).Append("\n\t{\n");
        foreach (var (k, v) in block)
            sb.Append("\t\t").Append(k).Append(" \"").Append(v).Append("\"\n");
        sb.Append("\t}\n");
    }
}
