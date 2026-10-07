namespace Hammer5Tools.Core.Hotkeys;

using System.Text;
using System.Text.RegularExpressions;
using ValveKeyValue;

/// <summary>
/// Represents and parses a Source 2 .keybindings KV3 document using ValveKeyValue.
/// </summary>
public partial class HotkeyDocument
{
    public const string DefaultHeader = "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->";

    private static readonly KVSerializer Kv3Serializer = KVSerializer.Create(KVSerializationFormat.KeyValues3Text);

    [GeneratedRegex(@"\{\s*m_Name\s*=\s*""([^""]*)""\s+m_Input\s*=\s*""([^""]*)""\s*\}", RegexOptions.IgnoreCase)]
    private static partial Regex MacroRegex();

    [GeneratedRegex(@"\{\s*m_CO?ntext\s*=\s*""([^""]*)""\s+m_Command\s*=\s*""([^""]*)""\s+m_Input\s*=\s*""([^""]*)""\s*\}", RegexOptions.IgnoreCase)]
    private static partial Regex BindingRegex();

    private KVObject Original = new();
    private KVHeader Header = new();

    public List<HotkeyMacro> Macros { get; } = [];

    public List<HotkeyBinding> Bindings { get; } = [];

    public IEnumerable<string> Contexts => Bindings.Select(b => b.Context).Distinct(StringComparer.OrdinalIgnoreCase);

    public static HotkeyDocument Parse(string text)
    {
        var doc = new HotkeyDocument();
        if (string.IsNullOrWhiteSpace(text))
        {
            return doc;
        }

        try
        {
            using var ms = new MemoryStream(Encoding.UTF8.GetBytes(text));
            var kvDoc = Kv3Serializer.Deserialize(ms);
            doc.Original = kvDoc.Root;
            doc.Header = kvDoc.Header ?? new KVHeader();

            // Read macros
            if (kvDoc.Root.TryGetValue("m_InputMacros", out var macrosObj) || kvDoc.Root.TryGetValue("m_Macros", out macrosObj))
            {
                if (macrosObj is not null)
                {
                    foreach (var item in macrosObj.Children)
                    {
                        var name = item.Value.TryGetValue("m_Name", out var n) ? n.ToString() : string.Empty;
                        var input = item.Value.TryGetValue("m_Input", out var inp) ? inp.ToString() : string.Empty;
                        if (!string.IsNullOrEmpty(name))
                        {
                            doc.Macros.Add(new HotkeyMacro(name, input) { Original = item.Value });
                        }
                    }
                }
            }

            // Read bindings
            if (kvDoc.Root.TryGetValue("m_Bindings", out var bindingsObj) && bindingsObj is not null)
            {
                foreach (var item in bindingsObj.Children)
                {
                    var ctx = item.Value.TryGetValue("m_Context", out var c) ? c.ToString()
                        : item.Value.TryGetValue("m_COntext", out var c2) ? c2.ToString() : string.Empty;
                    var cmd = item.Value.TryGetValue("m_Command", out var cm) ? cm.ToString() : string.Empty;
                    var inp = item.Value.TryGetValue("m_Input", out var i) ? i.ToString() : string.Empty;
                    if (!string.IsNullOrEmpty(cmd))
                    {
                        doc.Bindings.Add(new HotkeyBinding(ctx, cmd, inp) { Original = item.Value });
                    }
                }
            }

            if (doc.Bindings.Count > 0 || doc.Macros.Count > 0)
            {
                return doc;
            }
        }
        catch
        {
            // Graceful fallback for non-standard fragments
        }

        // Fallback for fragmented text
        foreach (Match match in MacroRegex().Matches(text))
        {
            doc.Macros.Add(new HotkeyMacro(match.Groups[1].Value, match.Groups[2].Value));
        }

        foreach (Match match in BindingRegex().Matches(text))
        {
            doc.Bindings.Add(new HotkeyBinding(match.Groups[1].Value, match.Groups[2].Value, match.Groups[3].Value));
        }

        return doc;
    }

    public static HotkeyDocument Load(string filePath)
    {
        var text = File.ReadAllText(filePath);
        return Parse(text);
    }

    public void Save(string filePath)
    {
        Formats.DocumentFile.Write(filePath, Serialize());
    }

    public string Serialize()
    {
        var root = Copy(Original);
        var macros = KVObject.Array();
        foreach (var macro in Macros)
        {
            var item = Copy(macro.Original);
            item["m_Name"] = new KVObject(macro.Name);
            item["m_Input"] = new KVObject(macro.Input);
            macros.Add(item);
        }

        if (Macros.Count > 0 || root.ContainsKey("m_InputMacros") || root.ContainsKey("m_Macros"))
        {
            root[root.ContainsKey("m_Macros") ? "m_Macros" : "m_InputMacros"] = macros;
        }

        var bindings = KVObject.Array();
        foreach (var binding in Bindings)
        {
            var item = Copy(binding.Original);
            item["m_Context"] = new KVObject(binding.Context);
            item["m_Command"] = new KVObject(binding.Command);
            item["m_Input"] = new KVObject(binding.Input);
            bindings.Add(item);
        }

        root["m_Bindings"] = bindings;
        using var output = new MemoryStream();
        Kv3Serializer.Serialize(output, new KVDocument(Header, string.Empty, root));
        return Encoding.UTF8.GetString(output.ToArray());
    }

    private static KVObject Copy(KVObject value)
    {
        var copy = new KVObject();
        foreach (var (key, child) in value.Children)
        {
            copy[key] = child;
        }

        return copy;
    }

    public HotkeyBinding? FindBinding(string context, string command) =>
        Bindings.FirstOrDefault(b =>
            string.Equals(b.Context, context, StringComparison.OrdinalIgnoreCase) &&
            string.Equals(b.Command, command, StringComparison.OrdinalIgnoreCase));

    public HotkeyBinding EnsureBinding(string context, string command)
    {
        var existing = FindBinding(context, command);
        if (existing is not null)
        {
            return existing;
        }

        var binding = new HotkeyBinding(context, command, string.Empty);
        Bindings.Add(binding);
        return binding;
    }

    public bool RemoveBinding(string context, string command)
    {
        var existing = FindBinding(context, command);
        return existing is not null && Bindings.Remove(existing);
    }

    public void SetBinding(string context, string command, string input)
    {
        var existing = FindBinding(context, command);
        if (existing is not null)
        {
            existing.Input = input;
        }
        else
        {
            Bindings.Add(new HotkeyBinding(context, command, input));
        }
    }
}
