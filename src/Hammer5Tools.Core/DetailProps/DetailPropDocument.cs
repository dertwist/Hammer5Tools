namespace Hammer5Tools.Core.DetailProps;

using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;
using ValveKeyValue;

/// <summary>
/// Document managing the reading, modification, and serialization of scripts/detail_prop_types.vdata using ValveKeyValue.
/// </summary>
public partial class DetailPropDocument
{
    public const string DefaultHeader = "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->";

    private static readonly KVSerializer Kv3Serializer = KVSerializer.Create(KVSerializationFormat.KeyValues3Text);

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

        try
        {
            using var ms = new MemoryStream(Encoding.UTF8.GetBytes(kv3Text));
            var kvDoc = Kv3Serializer.Deserialize(ms);

            foreach (var (typeName, typeObj) in kvDoc.Root.Children)
            {
                var propType = new DetailPropType(typeName);

                if (typeObj.TryGetValue("m_flDensity", out var densityObj) && densityObj is not null)
                {
                    propType.Density = densityObj.ToSingle(CultureInfo.InvariantCulture);
                }

                if (typeObj.TryGetValue("m_Models", out var modelsObj) && modelsObj is not null)
                {
                    foreach (var modelItem in modelsObj.Children)
                    {
                        var modelObj = modelItem.Value;
                        var model = new DetailPropModel();

                        if (modelObj.TryGetValue("m_ModelName", out var nameObj) && nameObj is not null)
                        {
                            model.ModelName = nameObj.ToString();
                        }
                        if (modelObj.TryGetValue("m_flMinScale", out var minScaleObj) && minScaleObj is not null)
                        {
                            model.MinScale = minScaleObj.ToSingle(CultureInfo.InvariantCulture);
                        }
                        if (modelObj.TryGetValue("m_flMaxScale", out var maxScaleObj) && maxScaleObj is not null)
                        {
                            model.MaxScale = maxScaleObj.ToSingle(CultureInfo.InvariantCulture);
                        }
                        if (modelObj.TryGetValue("m_flDensity", out var modelDensityObj) && modelDensityObj is not null)
                        {
                            model.Density = modelDensityObj.ToSingle(CultureInfo.InvariantCulture);
                        }
                        if (modelObj.TryGetValue("m_bRandomYaw", out var yawObj) && yawObj is not null)
                        {
                            model.RandomYaw = yawObj.ToBoolean(CultureInfo.InvariantCulture);
                        }
                        if (modelObj.TryGetValue("m_bRandomPitch", out var pitchObj) && pitchObj is not null)
                        {
                            model.RandomPitch = pitchObj.ToBoolean(CultureInfo.InvariantCulture);
                        }
                        if (modelObj.TryGetValue("m_bRandomRoll", out var rollObj) && rollObj is not null)
                        {
                            model.RandomRoll = rollObj.ToBoolean(CultureInfo.InvariantCulture);
                        }
                        if (modelObj.TryGetValue("m_bAlignToSurface", out var alignObj) && alignObj is not null)
                        {
                            model.AlignToSurface = alignObj.ToBoolean(CultureInfo.InvariantCulture);
                        }
                        if (modelObj.TryGetValue("m_bUpright", out var uprightObj) && uprightObj is not null)
                        {
                            model.Upright = uprightObj.ToBoolean(CultureInfo.InvariantCulture);
                        }

                        propType.Models.Add(model);
                    }
                }

                doc.Types.Add(propType);
            }

            if (doc.Types.Count > 0)
            {
                return doc;
            }
        }
        catch
        {
            // Fallback for non-standard fragments
        }

        // Fallback for partial/manual snippets
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

    public static DetailPropDocument Load(string filePath)
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

        foreach (var type in Types)
        {
            sb.AppendLine($"\t{type.Name} =");
            sb.AppendLine("\t{");
            sb.AppendLine(string.Format(CultureInfo.InvariantCulture, "\t\tm_flDensity = {0:F1}", type.Density));
            sb.AppendLine("\t\tm_Models =");
            sb.AppendLine("\t\t[");

            foreach (var model in type.Models)
            {
                sb.AppendLine("\t\t\t{");
                sb.AppendLine($"\t\t\t\tm_ModelName = \"{model.ModelName}\"");
                sb.AppendLine(string.Format(CultureInfo.InvariantCulture, "\t\t\t\tm_flMinScale = {0:F2}", model.MinScale));
                sb.AppendLine(string.Format(CultureInfo.InvariantCulture, "\t\t\t\tm_flMaxScale = {0:F2}", model.MaxScale));
                sb.AppendLine(string.Format(CultureInfo.InvariantCulture, "\t\t\t\tm_flDensity = {0:F1}", model.Density));
                sb.AppendLine($"\t\t\t\tm_bRandomYaw = {model.RandomYaw.ToString().ToLowerInvariant()}");
                sb.AppendLine($"\t\t\t\tm_bRandomPitch = {model.RandomPitch.ToString().ToLowerInvariant()}");
                sb.AppendLine($"\t\t\t\tm_bRandomRoll = {model.RandomRoll.ToString().ToLowerInvariant()}");
                sb.AppendLine($"\t\t\t\tm_bAlignToSurface = {model.AlignToSurface.ToString().ToLowerInvariant()}");
                sb.AppendLine($"\t\t\t\tm_bUpright = {model.Upright.ToString().ToLowerInvariant()}");
                sb.AppendLine("\t\t\t},");
            }

            sb.AppendLine("\t\t]");
            sb.AppendLine("\t}");
        }

        sb.AppendLine("}");
        return sb.ToString();
    }

    public DetailPropType AddType(string name, float density = 1.0f)
    {
        var type = new DetailPropType(name, density);
        Types.Add(type);
        return type;
    }

    public bool RemoveType(string name)
    {
        var existing = Types.FirstOrDefault(t => t.Name.Equals(name, StringComparison.OrdinalIgnoreCase));
        return existing is not null && Types.Remove(existing);
    }

    private static List<(string TypeName, string Body)> ExtractObjectBlocks(string innerText)
    {
        var list = new List<(string, string)>();
        var pos = 0;

        while (pos < innerText.Length)
        {
            var assignIndex = innerText.IndexOf('=', pos);
            if (assignIndex == -1)
            {
                break;
            }

            var leftPart = innerText.Substring(pos, assignIndex - pos).Trim();
            var lines = leftPart.Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries);
            var typeName = lines.Length > 0 ? lines[^1].Trim() : string.Empty;

            var openBrace = innerText.IndexOf('{', assignIndex);
            if (openBrace == -1)
            {
                break;
            }

            var closeBrace = FindMatchingBracket(innerText, openBrace, '{', '}');
            if (closeBrace == -1)
            {
                break;
            }

            var body = innerText.Substring(openBrace + 1, closeBrace - openBrace - 1);
            if (!string.IsNullOrWhiteSpace(typeName))
            {
                list.Add((typeName, body));
            }

            pos = closeBrace + 1;
        }

        return list;
    }

    private static List<string> ExtractBraceBlocks(string arrayContent)
    {
        var blocks = new List<string>();
        var pos = 0;

        while (pos < arrayContent.Length)
        {
            var open = arrayContent.IndexOf('{', pos);
            if (open == -1)
            {
                break;
            }

            var close = FindMatchingBracket(arrayContent, open, '{', '}');
            if (close == -1)
            {
                break;
            }

            blocks.Add(arrayContent.Substring(open + 1, close - open - 1));
            pos = close + 1;
        }

        return blocks;
    }

    private static int FindMatchingBracket(string text, int openIndex, char openChar, char closeChar)
    {
        if (openIndex < 0 || openIndex >= text.Length || text[openIndex] != openChar)
        {
            return -1;
        }

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
            else if (c == openChar)
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
}
