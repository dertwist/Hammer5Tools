using System.Diagnostics.CodeAnalysis;

namespace Hammer5Tools.Core.Format.SmartProps.Evaluation;

internal enum SmartPropValueKind
{
    None,
    Boolean,
    Integer,
    Float,
    String,
    Vector2,
    Vector3,
    Vector4,
}

internal readonly record struct SmartPropValue
{
    private SmartPropValue(SmartPropValueKind kind, bool booleanValue, int integerValue, float floatValue, string? stringValue, Vector4 vectorValue)
    {
        Kind = kind;
        BooleanValue = booleanValue;
        IntegerValue = integerValue;
        FloatValue = floatValue;
        StringValue = stringValue;
        VectorValue = vectorValue;
    }

    public SmartPropValueKind Kind { get; }

    private bool BooleanValue { get; }

    private int IntegerValue { get; }

    private float FloatValue { get; }

    private string? StringValue { get; }

    private Vector4 VectorValue { get; }

    public static SmartPropValue FromBoolean(bool value) => new(SmartPropValueKind.Boolean, value, default, default, null, default);

    public static SmartPropValue FromInteger(int value) => new(SmartPropValueKind.Integer, default, value, default, null, default);

    public static SmartPropValue FromFloat(float value) => new(SmartPropValueKind.Float, default, default, value, null, default);

    public static SmartPropValue FromString(string value) => new(SmartPropValueKind.String, default, default, default, value, default);

    public static SmartPropValue FromVector2(Vector2 value) => new(SmartPropValueKind.Vector2, default, default, default, null, new Vector4(value, default, default));

    public static SmartPropValue FromVector3(Vector3 value) => new(SmartPropValueKind.Vector3, default, default, default, null, new Vector4(value, default));

    public static SmartPropValue FromVector4(Vector4 value) => new(SmartPropValueKind.Vector4, default, default, default, null, value);

    public bool TryGetScalar(out float value)
    {
        value = Kind switch
        {
            SmartPropValueKind.Boolean => BooleanValue ? 1f : 0f,
            SmartPropValueKind.Integer => IntegerValue,
            SmartPropValueKind.Float => FloatValue,
            SmartPropValueKind.Vector2 or SmartPropValueKind.Vector3 or SmartPropValueKind.Vector4 => VectorValue.X,
            _ => default,
        };

        return Kind is SmartPropValueKind.Boolean
            or SmartPropValueKind.Integer
            or SmartPropValueKind.Float
            or SmartPropValueKind.Vector2
            or SmartPropValueKind.Vector3
            or SmartPropValueKind.Vector4;
    }

    public bool TryGetString([NotNullWhen(true)] out string? value)
    {
        value = StringValue;
        return Kind == SmartPropValueKind.String;
    }

    public bool TryGetVector3(out Vector3 value)
    {
        if (Kind is SmartPropValueKind.Vector2 or SmartPropValueKind.Vector3 or SmartPropValueKind.Vector4)
        {
            value = new Vector3(VectorValue.X, VectorValue.Y, VectorValue.Z);
            return true;
        }

        if (TryGetScalar(out var scalar))
        {
            value = new Vector3(scalar);
            return true;
        }

        value = default;
        return false;
    }

    public bool TryGetVector4(out Vector4 value)
    {
        if (Kind is SmartPropValueKind.Vector2 or SmartPropValueKind.Vector3 or SmartPropValueKind.Vector4)
        {
            value = VectorValue;
            return true;
        }

        if (TryGetScalar(out var scalar))
        {
            value = new Vector4(scalar);
            return true;
        }

        value = default;
        return false;
    }

    public bool TryGetComponent(int index, out float value)
    {
        if (index is < 0 or > 3)
        {
            value = default;
            return false;
        }

        if (Kind is SmartPropValueKind.Vector2 && index >= 2
            || Kind is SmartPropValueKind.Vector3 && index >= 3
            || Kind is not (SmartPropValueKind.Vector2 or SmartPropValueKind.Vector3 or SmartPropValueKind.Vector4))
        {
            return TryGetScalar(out value) && index == 0;
        }

        value = index switch
        {
            0 => VectorValue.X,
            1 => VectorValue.Y,
            2 => VectorValue.Z,
            _ => VectorValue.W,
        };
        return true;
    }
}
