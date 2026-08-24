using System.Text.Json;

using ValveKeyValue;

namespace Hammer5Tools.Core.SmartProps;

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
            result[property.Name] = ConvertValue(property.Value);
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
}
