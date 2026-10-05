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

    [GeneratedRegex(@"\{\s*m_Context\s*=\s*""([^""]*)""\s+m_Command\s*=\s*""([^""]*)""\s+m_Input\s*=\s*""([^""]*)""\s*\}", RegexOptions.IgnoreCase)]
    private static partial Regex BindingRegex();

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
                            doc.Macros.Add(new HotkeyMacro(name, input));
                        }
                    }
                }
            }

            // Read bindings
            if (kvDoc.Root.TryGetValue("m_Bindings", out var bindingsObj) && bindingsObj is not null)
            {
                foreach (var item in bindingsObj.Children)
                {
                    var ctx = item.Value.TryGetValue("m_Context", out var c) ? c.ToString() : string.Empty;
                    var cmd = item.Value.TryGetValue("m_Command", out var cm) ? cm.ToString() : string.Empty;
                    var inp = item.Value.TryGetValue("m_Input", out var i) ? i.ToString() : string.Empty;
                    if (!string.IsNullOrEmpty(cmd))
                    {
                        doc.Bindings.Add(new HotkeyBinding(ctx, cmd, inp));
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
        var text = Serialize();
        var dir = Path.GetDirectoryName(filePath);
        if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
        {
            Directory.CreateDirectory(dir);
        }

        File.WriteAllText(filePath, text);
    }

    public string Serialize()
    {
        var sb = new StringBuilder();
        sb.AppendLine(DefaultHeader);
        sb.AppendLine("{");

        if (Macros.Count > 0)
        {
            sb.AppendLine("\tm_InputMacros =");
            sb.AppendLine("\t[");
            foreach (var macro in Macros)
            {
                sb.AppendLine($"\t\t{{ m_Name = \"{macro.Name}\"\t\tm_Input = \"{macro.Input}\"\t}},");
            }

            sb.AppendLine("\t]");
            sb.AppendLine();
        }

        sb.AppendLine("\tm_Bindings =");
        sb.AppendLine("\t[");
        foreach (var binding in Bindings)
        {
            sb.AppendLine($"\t\t{{ m_Context = \"{binding.Context}\"\tm_Command = \"{binding.Command}\"\tm_Input = \"{binding.Input}\"\t}},");
        }

        sb.AppendLine("\t]");
        sb.AppendLine("}");

        return sb.ToString();
    }

    public void SetBinding(string context, string command, string input)
    {
        var existing = Bindings.FirstOrDefault(b =>
            string.Equals(b.Context, context, StringComparison.OrdinalIgnoreCase) &&
            string.Equals(b.Command, command, StringComparison.OrdinalIgnoreCase));

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
