using System.Numerics;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Supplies variable and placement values to a SmartProp expression.
/// </summary>
public sealed class SmartPropContext
{
    private readonly Dictionary<string, float> Variables;
    private readonly Dictionary<string, Vector4> Vectors;
    private readonly Dictionary<string, SmartPropValue> Values;
    private uint RandomState;

    /// <summary>
    /// Initializes a SmartProp expression context.
    /// </summary>
    public SmartPropContext(
        IReadOnlyDictionary<string, float>? variables = null,
        IReadOnlyDictionary<string, Vector4>? vectors = null,
        int instanceIndex = 0,
        int instanceCount = 1,
        int randomSeed = 0,
        float linearScale = 1.0f,
        IReadOnlyDictionary<string, SmartPropValue>? values = null)
    {
        Variables = variables is null
            ? new(StringComparer.OrdinalIgnoreCase)
            : new(variables, StringComparer.OrdinalIgnoreCase);
        Vectors = vectors is null
            ? new(StringComparer.OrdinalIgnoreCase)
            : new(vectors, StringComparer.OrdinalIgnoreCase);
        Values = values is null
            ? new(StringComparer.OrdinalIgnoreCase)
            : new(values, StringComparer.OrdinalIgnoreCase);
        RandomState = (uint)randomSeed;
        InstanceIndex = instanceIndex;
        InstanceCount = instanceCount;
        LinearScale = linearScale;
    }

    /// <summary>
    /// Gets the zero-based placement instance index.
    /// </summary>
    public int InstanceIndex { get; }

    /// <summary>
    /// Gets the number of placement instances.
    /// </summary>
    public int InstanceCount { get; }

    /// <summary>
    /// Gets the placement linear scale.
    /// </summary>
    public float LinearScale { get; }

    internal float GetVariable(string name) => Variables.TryGetValue(name, out var value) ? value : 0.0f;

    /// <summary>
    /// Resolves a numeric literal, variable, expression, or component value.
    /// </summary>
    public float ResolveScalar(SmartPropValue? value, float defaultValue = 0.0f) => ResolveScalar(value, defaultValue, 0);

    /// <summary>
    /// Resolves a SmartProp value to a three-component vector.
    /// </summary>
    public Vector3 ResolveVector(SmartPropValue? value, Vector3 defaultValue = default)
    {
        if (value?.Components is { Count: > 0 } components)
        {
            return new(
                ResolveComponent(components, 0, defaultValue.X),
                ResolveComponent(components, 1, defaultValue.Y),
                ResolveComponent(components, 2, defaultValue.Z));
        }

        var scalar = ResolveScalar(value, defaultValue.X);
        return new(scalar);
    }

    internal float GetVectorComponent(string name, int component)
    {
        if (!Vectors.TryGetValue(name, out var value))
            return GetVariable(name);

        return component switch
        {
            0 => value.X,
            1 => value.Y,
            2 => value.Z,
            3 => value.W,
            _ => 0.0f,
        };
    }

    internal float NextFloat(float minimum, float maximum) => minimum + ((maximum - minimum) * NextUnit());

    internal int NextInteger(float first, float second)
    {
        var minimum = (int)MathF.Min(first, second);
        var maximum = (int)MathF.Max(first, second);
        return minimum + (int)MathF.Floor(NextUnit() * ((maximum - minimum) + 1));
    }

    private float NextUnit()
    {
        RandomState = (RandomState * 1_664_525) + 1_013_904_223;
        return RandomState / (float)uint.MaxValue;
    }

    private float ResolveScalar(SmartPropValue? value, float defaultValue, int depth)
    {
        if (value is null || depth > 32)
            return defaultValue;

        return value.Kind switch
        {
            SmartPropValueKind.Literal => value.Literal,
            SmartPropValueKind.Expression => SmartPropExpression.Evaluate(value.Text, this, defaultValue),
            SmartPropValueKind.Components when value.Components is { Count: > 0 } components => ResolveScalar(components[0], defaultValue, depth + 1),
            SmartPropValueKind.Variable when value.Text is not null => ResolveVariable(value.Text, defaultValue, depth + 1),
            _ => defaultValue,
        };
    }

    private float ResolveComponent(IReadOnlyList<SmartPropValue> components, int index, float defaultValue)
    {
        return index < components.Count ? ResolveScalar(components[index], defaultValue, 0) : defaultValue;
    }

    private float ResolveVariable(string name, float defaultValue, int depth)
    {
        if (Values.TryGetValue(name, out var value))
            return ResolveScalar(value, defaultValue, depth);
        if (Variables.TryGetValue(name, out var scalar))
            return scalar;
        if (Vectors.TryGetValue(name, out var vector))
            return vector.X;
        return defaultValue;
    }
}
