using System.Globalization;
using ValveKeyValue;

namespace Hammer5Tools.Core.Format.SmartProps.Evaluation;

internal sealed class SmartPropValueResolver
{
    private readonly SmartPropEvaluationContext Context;
    private readonly Func<string, float>? EvaluateExpression;

    public SmartPropValueResolver(SmartPropEvaluationContext context, Func<string, float>? evaluateExpression = null)
    {
        Context = context;
        EvaluateExpression = evaluateExpression;
    }

    public float ResolveFloat(KVObject? source, float defaultValue = 0f)
    {
        if (!TryResolve(source, out var value))
        {
            return defaultValue;
        }

        if (value.TryGetScalar(out var scalar))
        {
            return scalar;
        }

        return value.TryGetString(out var expression) && EvaluateExpression is not null
            ? EvaluateExpression(expression)
            : defaultValue;
    }

    public string ResolveString(KVObject? source, string defaultValue = "")
        => TryResolve(source, out var value) && value.TryGetString(out var text) ? text : defaultValue;

    public Vector3 ResolveVector3(KVObject? source, Vector3 defaultValue = default)
        => TryResolve(source, out var value) && value.TryGetVector3(out var vector) ? vector : defaultValue;

    public Vector4 ResolveVector4(KVObject? source, Vector4 defaultValue = default)
        => TryResolve(source, out var value) && value.TryGetVector4(out var vector) ? vector : defaultValue;

    public bool TryResolve(KVObject? source, out SmartPropValue value)
    {
        value = default;
        if (source is null || source.IsNull)
        {
            return false;
        }

        if (source.ValueType == KVValueType.Collection)
        {
            return TryResolveBinding(source, out value);
        }

        if (source.IsArray)
        {
            return TryResolveArray(source.AsArraySpan(), out value);
        }

        switch (source.ValueType)
        {
            case KVValueType.Boolean:
                value = SmartPropValue.FromBoolean((bool)source);
                return true;
            case KVValueType.String:
                var text = (string)source;
                value = float.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out var number)
                    ? SmartPropValue.FromFloat(number)
                    : SmartPropValue.FromString(text);
                return true;
            case KVValueType.Int16:
            case KVValueType.UInt16:
            case KVValueType.Int32:
            case KVValueType.UInt32:
            case KVValueType.Int64:
            case KVValueType.UInt64:
                value = SmartPropValue.FromInteger((int)(float)source);
                return true;
            case KVValueType.FloatingPoint:
            case KVValueType.FloatingPoint64:
                value = SmartPropValue.FromFloat((float)source);
                return true;
            default:
                return false;
        }
    }

    private bool TryResolveBinding(KVObject source, out SmartPropValue value)
    {
        if (source.TryGetValue("m_SourceName", out var variable)
            && variable.ValueType == KVValueType.String
            && Context.TryGetValue((string)variable, out value))
        {
            return true;
        }

        if (source.TryGetValue("m_Expression", out var expression)
            && expression.ValueType == KVValueType.String
            && EvaluateExpression is not null)
        {
            value = SmartPropValue.FromFloat(EvaluateExpression((string)expression));
            return true;
        }

        if (source.TryGetValue("m_Components", out var components) && components.IsArray)
        {
            return TryResolveArray(components.AsArraySpan(), out value);
        }

        value = default;
        return false;
    }

    private bool TryResolveArray(ReadOnlySpan<KVObject> components, out SmartPropValue value)
    {
        Span<float> resolved = stackalloc float[4];
        var count = Math.Min(components.Length, resolved.Length);
        for (var i = 0; i < count; i++)
        {
            if (!TryResolve(components[i], out var component) || !component.TryGetScalar(out resolved[i]))
            {
                value = default;
                return false;
            }
        }

        value = count switch
        {
            1 => SmartPropValue.FromFloat(resolved[0]),
            2 => SmartPropValue.FromVector2(new Vector2(resolved[0], resolved[1])),
            3 => SmartPropValue.FromVector3(new Vector3(resolved[0], resolved[1], resolved[2])),
            _ when count >= 4 => SmartPropValue.FromVector4(new Vector4(resolved[0], resolved[1], resolved[2], resolved[3])),
            _ => default,
        };

        return count > 0;
    }
}
