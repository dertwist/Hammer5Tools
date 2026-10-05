namespace Hammer5Tools.Core.Hotkeys;

using System.IO;
using System.Text;
using System.Text.RegularExpressions;

/// <summary>
/// Represents and parses a Source 2 .keybindings KV3 document.
/// </summary>
public partial class HotkeyDocument
{
    public const string DefaultHeader = "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->";

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

        foreach (Match match in MacroRegex().Matches(text))
        {
            var name = match.Groups[1].Value;
            var input = match.Groups[2].Value;
            doc.Macros.Add(new HotkeyMacro(name, input));
        }

        foreach (Match match in BindingRegex().Matches(text))
        {
            var context = match.Groups[1].Value;
            var command = match.Groups[2].Value;
            var input = match.Groups[3].Value;
            doc.Bindings.Add(new HotkeyBinding(context, command, input));
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
