using System.Linq;
using System.Text.Json;

using ValveKeyValue;

namespace Hammer5Tools.Core.Format.SmartProps;

internal static class SmartPropJsonConverter
{
    public static KVObject Convert(string json)
    {
        using var document = JsonDocument.Parse(json);
        return ConvertValue(document.RootElement);
    }

    private static KVObject ConvertValue(JsonElement element)
    {
        return element.ValueKind switch
        {
            JsonValueKind.Object => ConvertObject(element),
            JsonValueKind.Array => ConvertArray(element),
            JsonValueKind.String => new KVObject(element.GetString() ?? string.Empty),
            JsonValueKind.Number when element.TryGetInt32(out var value) => new KVObject(value),
            JsonValueKind.Number => new KVObject(element.GetSingle()),
            JsonValueKind.True => new KVObject(true),
            JsonValueKind.False => new KVObject(false),
            _ => new KVObject(string.Empty),
        };
    }

    private static KVObject ConvertObject(JsonElement element)
    {
        var result = KVObject.Collection();
        foreach (var property in element.EnumerateObject())
        {
            // m_Expression is always expression source text, but a numeric-looking one (e.g.
            // "1") can arrive here as a JSON number — the KV3 text parser doesn't distinguish a
            // quoted "1" from a bare 1 by content, only by the surrounding grammar, and that
            // distinction is already lost by the time SmartPropDocumentSerializer hands us JSON.
            // VRF's expression resolver requires m_Expression to be a string and silently no-ops
            // the whole containing value otherwise, so coerce it back here before it reaches VRF.
            result[property.Name] = property.Name == "m_Expression" && property.Value.ValueKind == JsonValueKind.Number
                ? new KVObject(property.Value.GetRawText())
                : ConvertValue(property.Value);
        }
        return result;
    }

    private static KVObject ConvertArray(JsonElement element)
    {
        var result = KVObject.Array(element.GetArrayLength());
        foreach (var item in element.EnumerateArray())
        {
            result.Add(ConvertValue(item));
        }
        return result;
    }

    /// <summary>
    /// Same fix as <see cref="ConvertObject"/>'s m_Expression guard, applied directly to a KV3
    /// document parsed straight from text (<c>SmartPropEvaluator.EvaluateText</c> never goes
    /// through this converter's JSON path, so a numeric-looking m_Expression there is never
    /// coerced back to a string unless this walk does it).
    /// </summary>
    public static void NormalizeExpressionStrings(KVObject node)
    {
        if (node.ValueType is not (KVValueType.Collection or KVValueType.Array))
            return;

        // Snapshot first: reassigning node[name] below (an existing-key overwrite) can
        // invalidate the live Children enumerator mid-walk.
        foreach (var (name, child) in node.Children.ToArray())
        {
            if (node.ValueType == KVValueType.Collection && name == "m_Expression" && IsNumeric(child.ValueType))
                node[name] = new KVObject(child.ToString(null));
            else
                NormalizeExpressionStrings(child);
        }
    }

    private static bool IsNumeric(KVValueType type) => type is
        KVValueType.Int16 or KVValueType.Int32 or KVValueType.Int64
        or KVValueType.UInt16 or KVValueType.UInt32 or KVValueType.UInt64
        or KVValueType.FloatingPoint or KVValueType.FloatingPoint64 or KVValueType.Pointer;
}
