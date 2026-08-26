using System.Text;
using System.Text.Json;

using ValveKeyValue;
using ValveResourceFormat.Serialization.KeyValues;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Serializes Hammer5Tools SmartProp documents as Valve KeyValues3 text.
/// </summary>
public static class SmartPropDocumentSerializer
{
    /// <summary>
    /// Serializes a JSON representation of an uncompiled SmartProp document.
    /// </summary>
    public static string SerializeJson(string json)
    {
        ArgumentNullException.ThrowIfNull(json);

        return SmartPropJsonConverter.Convert(json).ToKV3String();
    }

    /// <summary>
    /// Parses a KeyValues3 SmartProp document into a JSON representation.
    /// </summary>
    public static string DeserializeText(string text)
    {
        ArgumentNullException.ThrowIfNull(text);

        using var input = new MemoryStream(Encoding.UTF8.GetBytes(text));
        var document = KVDocumentExtensions.ParseKV3(input);
        using var output = new MemoryStream();
        using (var writer = new Utf8JsonWriter(output))
        {
            WriteValue(writer, document.Root);
        }
        return Encoding.UTF8.GetString(output.ToArray());
    }

    private static void WriteValue(Utf8JsonWriter writer, KVObject value)
    {
        switch (value.ValueType)
        {
            case KVValueType.Null:
                writer.WriteNullValue();
                break;
            case KVValueType.Collection:
                writer.WriteStartObject();
                foreach (var (name, child) in value.Children)
                {
                    writer.WritePropertyName(name);
                    // The KV3 text parser doesn't distinguish a quoted "1" from a bare 1 by
                    // content, so a numeric-looking m_Expression string (e.g. m_Expression = "1")
                    // comes back from it typed as a number. m_Expression is always expression
                    // source text though, so restore the string type here — see the matching
                    // note in SmartPropJsonConverter, which guards the reverse conversion.
                    if (name == "m_Expression" && IsNumeric(child.ValueType))
                        writer.WriteStringValue(child.ToString(null));
                    else
                        WriteValue(writer, child);
                }
                writer.WriteEndObject();
                break;
            case KVValueType.Array:
                writer.WriteStartArray();
                foreach (var child in value.AsArraySpan())
                {
                    WriteValue(writer, child);
                }
                writer.WriteEndArray();
                break;
            case KVValueType.Boolean:
                writer.WriteBooleanValue(value.ToBoolean(null));
                break;
            case KVValueType.String:
                writer.WriteStringValue(value.ToString(null));
                break;
            case KVValueType.Int16:
            case KVValueType.Int32:
            case KVValueType.Pointer:
                writer.WriteNumberValue(value.ToInt32(null));
                break;
            case KVValueType.Int64:
                writer.WriteNumberValue(value.ToInt64(null));
                break;
            case KVValueType.UInt16:
            case KVValueType.UInt32:
                writer.WriteNumberValue(value.ToUInt32(null));
                break;
            case KVValueType.UInt64:
                writer.WriteNumberValue(value.ToUInt64(null));
                break;
            case KVValueType.FloatingPoint:
                writer.WriteNumberValue(value.ToSingle(null));
                break;
            case KVValueType.FloatingPoint64:
                writer.WriteNumberValue(value.ToDouble(null));
                break;
            case KVValueType.BinaryBlob:
                writer.WriteBase64StringValue(value.AsBlob());
                break;
            default:
                throw new InvalidDataException($"Unsupported KV3 value type: {value.ValueType}");
        }
    }

    private static bool IsNumeric(KVValueType type) => type is
        KVValueType.Int16 or KVValueType.Int32 or KVValueType.Int64
        or KVValueType.UInt16 or KVValueType.UInt32 or KVValueType.UInt64
        or KVValueType.FloatingPoint or KVValueType.FloatingPoint64 or KVValueType.Pointer;
}
