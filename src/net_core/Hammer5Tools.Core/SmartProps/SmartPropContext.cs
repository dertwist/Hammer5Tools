using System.Numerics;

namespace Hammer5Tools.Core.SmartProps;

/// <summary>
/// Supplies variable and placement values to a SmartProp expression.
/// </summary>
public sealed class SmartPropContext
{
    private readonly Dictionary<string, float> Variables;
    private readonly Dictionary<string, Vector4> Vectors;
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
        float linearScale = 1.0f)
    {
        Variables = variables is null
            ? new(StringComparer.OrdinalIgnoreCase)
            : new(variables, StringComparer.OrdinalIgnoreCase);
        Vectors = vectors is null
            ? new(StringComparer.OrdinalIgnoreCase)
            : new(vectors, StringComparer.OrdinalIgnoreCase);
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
}
