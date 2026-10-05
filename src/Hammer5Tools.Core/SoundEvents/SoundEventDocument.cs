namespace Hammer5Tools.Core.SoundEvents;

using System.Collections.ObjectModel;
using System.Text;
using System.Text.RegularExpressions;

public partial class SoundEventDocument
{
    public const string DefaultHeader = "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->";

    public ObservableCollection<SoundEvent> Events { get; } = [];

    public static SoundEventDocument Parse(string kv3Text)
    {
        var doc = new SoundEventDocument();
        if (string.IsNullOrWhiteSpace(kv3Text))
        {
            return doc;
        }

        // Find outermost { ... }, skipping header comment if present
        var searchStart = 0;
        var headerEnd = kv3Text.IndexOf("-->", StringComparison.Ordinal);
        if (headerEnd != -1)
        {
            searchStart = headerEnd + 3;
        }

        var firstBrace = kv3Text.IndexOf('{', searchStart);
        if (firstBrace == -1)
        {
            return doc;
        }

        var lastBrace = kv3Text.LastIndexOf('}');
        if (lastBrace <= firstBrace)
        {
            return doc;
        }

        var inner = kv3Text.Substring(firstBrace + 1, lastBrace - firstBrace - 1);
        var pos = 0;

        while (pos < inner.Length)
        {
            var assignIdx = inner.IndexOf('=', pos);
            if (assignIdx == -1)
            {
                break;
            }

            var leftRaw = inner.Substring(pos, assignIdx - pos).Trim();
            var eventName = leftRaw.Trim('"', '\'', ' ', '\t', '\r', '\n');

            var braceStart = inner.IndexOf('{', assignIdx);
            if (braceStart == -1)
            {
                break;
            }

            var braceEnd = FindMatchingBrace(inner, braceStart);
            if (braceEnd == -1)
            {
                break;
            }

            var body = inner.Substring(braceStart + 1, braceEnd - braceStart - 1);
            var soundEvent = ParseEventBody(eventName, body);
            doc.Events.Add(soundEvent);

            pos = braceEnd + 1;
        }

        return doc;
    }

    private static SoundEvent ParseEventBody(string name, string body)
    {
        var soundEvent = new SoundEvent(name);
        var lines = body.Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries);

        foreach (var line in lines)
        {
            var trimmed = line.Trim();
            if (trimmed.StartsWith("//", StringComparison.Ordinal) || !trimmed.Contains('='))
            {
                continue;
            }

            var eq = trimmed.IndexOf('=');
            var key = trimmed[..eq].Trim().Trim('"', '\'');
            var val = trimmed[(eq + 1)..].Trim().TrimEnd(';');

            if (key.Equals("type", StringComparison.OrdinalIgnoreCase))
            {
                soundEvent.Type = val.Trim('"', '\'');
            }
            else
            {
                soundEvent.Properties.Add(new SoundProperty(key, val));
            }
        }

        return soundEvent;
    }

    public string Serialize()
    {
        var sb = new StringBuilder();
        sb.AppendLine(DefaultHeader);
        sb.AppendLine("{");

        foreach (var ev in Events)
        {
            sb.AppendLine($"\t\"{ev.Name}\" =");
            sb.AppendLine("\t{");
            sb.AppendLine($"\t\ttype = \"{ev.Type}\"");

            foreach (var prop in ev.Properties)
            {
                sb.AppendLine($"\t\t{prop.Key} = {prop.Value}");
            }

            sb.AppendLine("\t}");
        }

        sb.AppendLine("}");
        return sb.ToString();
    }

    private static int FindMatchingBrace(string text, int openIndex)
    {
        var depth = 0;
        var inQuotes = false;
        var quoteChar = '\0';

        for (var i = openIndex; i < text.Length; i++)
        {
            var c = text[i];
            if (inQuotes)
            {
                if (c == '\\')
                {
                    i++;
                }
                else if (c == quoteChar)
                {
                    inQuotes = false;
                }
                continue;
            }

            if (c is '"' or '\'')
            {
                inQuotes = true;
                quoteChar = c;
            }
            else if (c == '{')
            {
                depth++;
            }
            else if (c == '}')
            {
                depth--;
                if (depth == 0)
                {
                    return i;
                }
            }
        }

        return -1;
    }
}
