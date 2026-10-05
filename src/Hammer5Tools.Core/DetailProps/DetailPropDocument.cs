namespace Hammer5Tools.Core.DetailProps;

using System.Globalization;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

/// <summary>
/// Document managing the reading, modification, and serialization of scripts/detail_prop_types.vdata.
/// </summary>
public partial class DetailPropDocument
{
    public const string DefaultHeader = "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->";

    [GeneratedRegex(@"m_flDensity\s*=\s*([0-9.]+)", RegexOptions.IgnoreCase)]
    private static partial Regex DensityRegex();

    [GeneratedRegex(@"m_ModelName\s*=\s*""([^""]*)""", RegexOptions.IgnoreCase)]
    private static partial Regex ModelNameRegex();

    [GeneratedRegex(@"m_flMinScale\s*=\s*([0-9.]+)", RegexOptions.IgnoreCase)]
    private static partial Regex MinScaleRegex();

    [GeneratedRegex(@"m_flMaxScale\s*=\s*([0-9.]+)", RegexOptions.IgnoreCase)]
    private static partial Regex MaxScaleRegex();

    [GeneratedRegex(@"m_bRandomYaw\s*=\s*(true|false)", RegexOptions.IgnoreCase)]
    private static partial Regex RandomYawRegex();

    [GeneratedRegex(@"m_bRandomPitch\s*=\s*(true|false)", RegexOptions.IgnoreCase)]
    private static partial Regex RandomPitchRegex();

    [GeneratedRegex(@"m_bRandomRoll\s*=\s*(true|false)", RegexOptions.IgnoreCase)]
    private static partial Regex RandomRollRegex();

    [GeneratedRegex(@"m_bAlignToSurface\s*=\s*(true|false)", RegexOptions.IgnoreCase)]
    private static partial Regex AlignToSurfaceRegex();

    [GeneratedRegex(@"m_bUpright\s*=\s*(true|false)", RegexOptions.IgnoreCase)]
    private static partial Regex UprightRegex();

    public List<DetailPropType> Types { get; } = [];

    public static DetailPropDocument Parse(string kv3Text)
    {
        var doc = new DetailPropDocument();
        if (string.IsNullOrWhiteSpace(kv3Text))
        {
            return doc;
        }

        // Find root object bounds
        var firstBrace = kv3Text.IndexOf('{');
        var lastBrace = kv3Text.LastIndexOf('}');
        if (firstBrace == -1 || lastBrace <= firstBrace)
        {
            return doc;
        }

        var inner = kv3Text.Substring(firstBrace + 1, lastBrace - firstBrace - 1);
        var typeBlocks = ExtractObjectBlocks(inner);

        foreach (var (typeName, body) in typeBlocks)
        {
            var propType = new DetailPropType(typeName);

            var densityMatch = DensityRegex().Match(body);
            if (densityMatch.Success && float.TryParse(densityMatch.Groups[1].Value, CultureInfo.InvariantCulture, out var density))
            {
                propType.Density = density;
            }

            // Extract models from m_Models array inside body
            var modelsIndex = body.IndexOf("m_Models", StringComparison.OrdinalIgnoreCase);
            if (modelsIndex != -1)
            {
                var bracketOpen = body.IndexOf('[', modelsIndex);
                var bracketClose = FindMatchingBracket(body, bracketOpen, '[', ']');
                if (bracketOpen != -1 && bracketClose > bracketOpen)
                {
                    var modelsContent = body.Substring(bracketOpen + 1, bracketClose - bracketOpen - 1);
                    var modelBlocks = ExtractBraceBlocks(modelsContent);

                    foreach (var modelBody in modelBlocks)
                    {
                        var model = new DetailPropModel();

                        var nameMatch = ModelNameRegex().Match(modelBody);
                        if (nameMatch.Success)
                        {
                            model.ModelName = nameMatch.Groups[1].Value;
                        }

                        var minScaleMatch = MinScaleRegex().Match(modelBody);
                        if (minScaleMatch.Success && float.TryParse(minScaleMatch.Groups[1].Value, CultureInfo.InvariantCulture, out var minScale))
                        {
                            model.MinScale = minScale;
                        }

                        var maxScaleMatch = MaxScaleRegex().Match(modelBody);
                        if (maxScaleMatch.Success && float.TryParse(maxScaleMatch.Groups[1].Value, CultureInfo.InvariantCulture, out var maxScale))
                        {
                            model.MaxScale = maxScale;
                        }

                        var yawMatch = RandomYawRegex().Match(modelBody);
                        if (yawMatch.Success)
                        {
                            model.RandomYaw = bool.Parse(yawMatch.Groups[1].Value);
                        }

                        var pitchMatch = RandomPitchRegex().Match(modelBody);
                        if (pitchMatch.Success)
                        {
                            model.RandomPitch = bool.Parse(pitchMatch.Groups[1].Value);
                        }

                        var rollMatch = RandomRollRegex().Match(modelBody);
                        if (rollMatch.Success)
                        {
                            model.RandomRoll = bool.Parse(rollMatch.Groups[1].Value);
                        }

                        var alignMatch = AlignToSurfaceRegex().Match(modelBody);
                        if (alignMatch.Success)
                        {
                            model.AlignToSurface = bool.Parse(alignMatch.Groups[1].Value);
                        }

                        var uprightMatch = UprightRegex().Match(modelBody);
                        if (uprightMatch.Success)
                        {
                            model.Upright = bool.Parse(uprightMatch.Groups[1].Value);
                        }

                        propType.Models.Add(model);
                    }
                }
            }

            doc.Types.Add(propType);
        }

        return doc;
    }

    private static List<(string Name, string Body)> ExtractObjectBlocks(string text)
    {
        var blocks = new List<(string Name, string Body)>();
        var pos = 0;

        while (pos < text.Length)
        {
            var eq = text.IndexOf('=', pos);
            if (eq == -1)
            {
                break;
            }

            // Extract name before '='
            var namePart = text[pos..eq].Trim();
            // Handle comments or whitespace
            var lastLine = namePart.Split('\n').LastOrDefault()?.Trim() ?? string.Empty;
            var name = lastLine.Trim();

            var openBrace = text.IndexOf('{', eq);
            if (openBrace == -1)
            {
                break;
            }

            var closeBrace = FindMatchingBracket(text, openBrace, '{', '}');
            if (closeBrace == -1)
            {
                break;
            }

            if (!string.IsNullOrWhiteSpace(name))
            {
                var body = text.Substring(openBrace + 1, closeBrace - openBrace - 1);
                blocks.Add((name, body));
            }

            pos = closeBrace + 1;
        }

        return blocks;
    }

    private static List<string> ExtractBraceBlocks(string text)
    {
        var list = new List<string>();
        var pos = 0;

        while (pos < text.Length)
        {
            var open = text.IndexOf('{', pos);
            if (open == -1)
            {
                break;
            }

            var close = FindMatchingBracket(text, open, '{', '}');
            if (close == -1)
            {
                break;
            }

            list.Add(text.Substring(open + 1, close - open - 1));
            pos = close + 1;
        }

        return list;
    }

    private static int FindMatchingBracket(string text, int openPos, char openChar, char closeChar)
    {
        if (openPos == -1 || openPos >= text.Length || text[openPos] != openChar)
        {
            return -1;
        }

        var depth = 0;
        var inQuotes = false;

        for (var i = openPos; i < text.Length; i++)
        {
            var c = text[i];
            if (c == '"' && (i == 0 || text[i - 1] != '\\'))
            {
                inQuotes = !inQuotes;
                continue;
            }

            if (inQuotes)
            {
                continue;
            }

            if (c == openChar)
            {
                depth++;
            }
            else if (c == closeChar)
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

    public static DetailPropDocument Load(string filePath)
    {
        var text = File.ReadAllText(filePath);
        return Parse(text);
    }

    public void Save(string filePath)
    {
        var dir = Path.GetDirectoryName(filePath);
        if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
        {
            Directory.CreateDirectory(dir);
        }

        var text = Serialize();
        File.WriteAllText(filePath, text);
    }

    public string Serialize()
    {
        var sb = new StringBuilder();
        sb.AppendLine(DefaultHeader);
        sb.AppendLine("{");

        foreach (var type in Types)
        {
            sb.AppendLine($"\t{type.Name} =");
            sb.AppendLine("\t{");
            sb.AppendLine(string.Create(CultureInfo.InvariantCulture, $"\t\tm_flDensity = {type.Density:0.000000}"));
            sb.AppendLine("\t\tm_Models =");
            sb.AppendLine("\t\t[");

            foreach (var model in type.Models)
            {
                sb.AppendLine("\t\t\t{");
                sb.AppendLine($"\t\t\t\tm_ModelName = \"{model.ModelName}\"");
                sb.AppendLine(string.Create(CultureInfo.InvariantCulture, $"\t\t\t\tm_flMinScale = {model.MinScale:0.000000}"));
                sb.AppendLine(string.Create(CultureInfo.InvariantCulture, $"\t\t\t\tm_flMaxScale = {model.MaxScale:0.000000}"));
                sb.AppendLine($"\t\t\t\tm_bRandomYaw = {model.RandomYaw.ToString().ToLowerInvariant()}");
                sb.AppendLine($"\t\t\t\tm_bRandomPitch = {model.RandomPitch.ToString().ToLowerInvariant()}");
                sb.AppendLine($"\t\t\t\tm_bRandomRoll = {model.RandomRoll.ToString().ToLowerInvariant()}");
                sb.AppendLine($"\t\t\t\tm_bAlignToSurface = {model.AlignToSurface.ToString().ToLowerInvariant()}");
                sb.AppendLine($"\t\t\t\tm_bUpright = {model.Upright.ToString().ToLowerInvariant()}");
                sb.AppendLine(string.Create(CultureInfo.InvariantCulture, $"\t\t\t\tm_flDensity = {model.Density:0.000000}"));
                sb.AppendLine("\t\t\t},");
            }

            sb.AppendLine("\t\t]");
            sb.AppendLine("\t}");
        }

        sb.AppendLine("}");
        return sb.ToString();
    }
}
