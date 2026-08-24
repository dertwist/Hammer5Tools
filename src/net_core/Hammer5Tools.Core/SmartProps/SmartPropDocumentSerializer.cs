using ValveResourceFormat.Serialization.KeyValues;

namespace Hammer5Tools.Core.SmartProps;

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
}
