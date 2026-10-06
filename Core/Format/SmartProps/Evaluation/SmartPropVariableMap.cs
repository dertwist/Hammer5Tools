using System.Diagnostics.CodeAnalysis;
using System.Globalization;
using ValveKeyValue;

namespace Hammer5Tools.Core.Format.SmartProps.Evaluation;

internal sealed record SmartPropVariableDefinition(
    string Name,
    string Type,
    SmartPropValue DefaultValue,
    bool ExposeAsParameter,
    float? MinValue,
    float? MaxValue,
    string? ModelName,
    string? DisplayName,
    int ElementId);

internal static class SmartPropVariableMap
{
    private const string VariableClassPrefix = "CSmartPropVariable_";

    public static IReadOnlyList<SmartPropVariableDefinition> ReadDefinitions(KVObject? root)
    {
        if (root is null
            || !root.TryGetValue("m_Variables", out var variables)
            || !variables.IsArray)
        {
            return [];
        }

        var definitions = new List<SmartPropVariableDefinition>();
        foreach (var variable in variables.AsArraySpan())
        {
            if (TryReadDefinition(variable, out var definition))
            {
                definitions.Add(definition);
            }
        }

        return definitions;
    }

    public static Dictionary<string, SmartPropValue> ReadDefaults(KVObject? root)
    {
        var defaults = new Dictionary<string, SmartPropValue>(StringComparer.OrdinalIgnoreCase);
        foreach (var definition in ReadDefinitions(root))
        {
            defaults[definition.Name] = definition.DefaultValue;
        }

        return defaults;
    }

    private static bool TryReadDefinition(KVObject variable, [NotNullWhen(true)] out SmartPropVariableDefinition? definition)
    {
        definition = null;

        if (variable.ValueType != KVValueType.Collection
            || !variable.TryGetValue("m_VariableName", out var nameValue)
            || nameValue.ValueType != KVValueType.String)
        {
            return false;
        }

        var name = (string)nameValue;
        if (string.IsNullOrEmpty(name))
        {
            return false;
        }

        variable.TryGetValue("m_DefaultValue", out var defaultValue);
        var type = ReadVariableType(variable);
        var exposeAsParameter = !variable.TryGetValue("m_bExposeAsParameter", out var exposeValue)
            || exposeValue.ValueType != KVValueType.Boolean
            || (bool)exposeValue;

        definition = new SmartPropVariableDefinition(
            name,
            type,
            ReadValue(type, defaultValue),
            exposeAsParameter,
            ReadOptionalFloat(variable, "m_nParamaterMinValue", "m_flParamaterMinValue", "m_nMinValue", "m_flMinValue"),
            ReadOptionalFloat(variable, "m_nParamaterMaxValue", "m_flParamaterMaxValue", "m_nMaxValue", "m_flMaxValue"),
            ReadOptionalString(variable, "m_sModelName"),
            ReadOptionalString(variable, "m_DisplayName"),
            ReadOptionalInt32(variable, "m_nElementID"));

        return true;
    }

    private static string ReadVariableType(KVObject variable)
    {
        if ((!variable.TryGetValue("generic_data_type", out var classValue) || classValue.ValueType != KVValueType.String)
            && (!variable.TryGetValue("_class", out classValue) || classValue.ValueType != KVValueType.String))
        {
            return string.Empty;
        }

        var className = (string)classValue;
        return className.StartsWith(VariableClassPrefix, StringComparison.Ordinal)
            ? className[VariableClassPrefix.Length..]
            : className;
    }

    internal static SmartPropValue ReadValue(string type, KVObject? value)
    {
        var normalizedType = type.ToLowerInvariant();
        if (normalizedType.Contains("bool", StringComparison.Ordinal))
        {
            return SmartPropValue.FromBoolean(ReadBoolean(value));
        }

        if (normalizedType == "int")
        {
            return SmartPropValue.FromInteger(ReadInt32(value));
        }

        if (normalizedType == "float")
        {
            return SmartPropValue.FromFloat(ReadFloat(value));
        }

        if (normalizedType.Contains("vector2", StringComparison.Ordinal))
        {
            var vector = ReadVector(value);
            return SmartPropValue.FromVector2(new Vector2(vector.X, vector.Y));
        }

        if (normalizedType.Contains("vector4", StringComparison.Ordinal)
            || normalizedType.Contains("color", StringComparison.Ordinal))
        {
            return SmartPropValue.FromVector4(ReadVector(value));
        }

        if (normalizedType.Contains("vector", StringComparison.Ordinal)
            || normalizedType.Contains("angle", StringComparison.Ordinal))
        {
            var vector = ReadVector(value);
            return SmartPropValue.FromVector3(new Vector3(vector.X, vector.Y, vector.Z));
        }

        return SmartPropValue.FromString(ReadString(value));
    }

    private static bool ReadBoolean(KVObject? value)
    {
        if (value is null || value.IsNull)
        {
            return false;
        }

        if (value.ValueType == KVValueType.Boolean)
        {
            return (bool)value;
        }

        if (value.ValueType == KVValueType.String)
        {
            return ((string)value).Trim().ToLowerInvariant() is "1" or "true" or "yes";
        }

        return TryReadFloat(value, out var number) && number != 0f;
    }

    private static int ReadInt32(KVObject? value)
        => TryReadFloat(value, out var number) ? (int)number : 0;

    private static float ReadFloat(KVObject? value)
        => TryReadFloat(value, out var number) ? number : 0f;

    private static bool TryReadFloat(KVObject? value, out float number)
    {
        number = default;
        if (value is null || value.IsNull)
        {
            return false;
        }

        if (value.ValueType == KVValueType.String)
        {
            return float.TryParse((string)value, NumberStyles.Float, CultureInfo.InvariantCulture, out number);
        }

        if (value.ValueType == KVValueType.Boolean)
        {
            number = (bool)value ? 1f : 0f;
            return true;
        }

        if (value.ValueType is KVValueType.Int16
            or KVValueType.UInt16
            or KVValueType.Int32
            or KVValueType.UInt32
            or KVValueType.Int64
            or KVValueType.UInt64
            or KVValueType.FloatingPoint
            or KVValueType.FloatingPoint64)
        {
            number = (float)value;
            return true;
        }

        return false;
    }

    private static Vector4 ReadVector(KVObject? value)
    {
        if (value is null || !value.IsArray)
        {
            return default;
        }

        var components = value.AsArraySpan();
        return new Vector4(
            ReadComponent(components, 0),
            ReadComponent(components, 1),
            ReadComponent(components, 2),
            ReadComponent(components, 3));
    }

    private static float ReadComponent(ReadOnlySpan<KVObject> components, int index)
        => index < components.Length ? ReadFloat(components[index]) : 0f;

    private static string ReadString(KVObject? value)
        => value is { ValueType: KVValueType.String } ? (string)value : string.Empty;

    private static float? ReadOptionalFloat(KVObject source, params string[] names)
    {
        foreach (var name in names)
        {
            if (source.TryGetValue(name, out var value) && TryReadFloat(value, out var number))
            {
                return number;
            }
        }

        return null;
    }

    private static string? ReadOptionalString(KVObject source, string name)
        => source.TryGetValue(name, out var value) && value.ValueType == KVValueType.String
            ? (string)value
            : null;

    private static int ReadOptionalInt32(KVObject source, string name)
        => source.TryGetValue(name, out var value) ? ReadInt32(value) : 0;
}
