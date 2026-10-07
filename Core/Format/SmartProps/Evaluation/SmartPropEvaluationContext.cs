using ValveKeyValue;

namespace Hammer5Tools.Core.Format.SmartProps.Evaluation;

internal readonly record struct SmartPropPlacement(int InstanceIndex = 0, int InstanceCount = 1, float LinearScale = 1f);

internal sealed class SmartPropEvaluationContext
{
    private readonly Dictionary<string, SmartPropValue> Variables;
    private readonly Dictionary<string, SmartPropValue> Overrides;
    private readonly Dictionary<int, int> PickOneSelections;

    public SmartPropEvaluationContext(
        IReadOnlyDictionary<string, SmartPropValue>? variables = null,
        IReadOnlyDictionary<string, SmartPropValue>? overrides = null,
        SmartPropPlacement placement = default,
        int seed = 0,
        IReadOnlyDictionary<int, int>? pickOneSelections = null)
    {
        Variables = CopyValues(variables);
        Overrides = CopyValues(overrides);
        PickOneSelections = pickOneSelections is null ? [] : new Dictionary<int, int>(pickOneSelections);
        Placement = placement == default ? new SmartPropPlacement(0, 1, 1f) : placement;
        Seed = seed;
    }

    private SmartPropEvaluationContext(SmartPropEvaluationContext parent, SmartPropPlacement placement)
    {
        Variables = parent.Variables;
        Overrides = parent.Overrides;
        PickOneSelections = parent.PickOneSelections;
        Placement = placement;
        Seed = unchecked(parent.Seed ^ (parent.InstanceIndex * 1_664_525));
    }

    public SmartPropPlacement Placement { get; }

    public int InstanceIndex => Placement.InstanceIndex;

    public int InstanceCount => Placement.InstanceCount;

    public float LinearScale => Placement.LinearScale;

    public int Seed { get; }

    public bool TryGetValue(string name, out SmartPropValue value)
    {
        ArgumentException.ThrowIfNullOrEmpty(name);

        return Overrides.TryGetValue(name, out value)
            || Variables.TryGetValue(name, out value);
    }

    public SmartPropEvaluationContext WithPlacement(SmartPropPlacement placement)
        => new(this, placement);

    public SmartPropEvaluationContext WithOverride(string name, SmartPropValue value)
    {
        ArgumentException.ThrowIfNullOrEmpty(name);

        var overrides = new Dictionary<string, SmartPropValue>(Overrides, StringComparer.OrdinalIgnoreCase)
        {
            [name] = value,
        };

        return new SmartPropEvaluationContext(Variables, overrides, Placement, Seed, PickOneSelections);
    }

    public bool TryGetPickOneSelection(int elementId, out int childIndex)
        => PickOneSelections.TryGetValue(elementId, out childIndex);

    public SmartPropEvaluationContext WithPickOneSelection(int elementId, int childIndex)
    {
        var selections = new Dictionary<int, int>(PickOneSelections)
        {
            [elementId] = childIndex,
        };
        return new SmartPropEvaluationContext(Variables, Overrides, Placement, Seed, selections);
    }

    public float RandomFloat(int salt)
    {
        var value = unchecked((uint)Seed);
        value ^= unchecked((uint)InstanceIndex) * 0x9E3779B9u;
        value ^= unchecked((uint)salt) * 0x85EBCA6Bu;
        value ^= value >> 16;
        value *= 0x7FEB352Du;
        value ^= value >> 15;
        value *= 0x846CA68Bu;
        value ^= value >> 16;
        return (value >> 8) * (1f / 16777216f);
    }

    public float ResolveScalar(KVObject? source, float defaultValue = 0f)
        => CreateResolver().ResolveFloat(source, defaultValue);

    public string ResolveString(KVObject? source, string defaultValue = "")
        => CreateResolver().ResolveString(source, defaultValue);

    public Vector3 ResolveVector3(KVObject? source, Vector3 defaultValue = default)
        => CreateResolver().ResolveVector3(source, defaultValue);

    public Vector4 ResolveVector4(KVObject? source, Vector4 defaultValue = default)
        => CreateResolver().ResolveVector4(source, defaultValue);

    private SmartPropValueResolver CreateResolver()
        => new(this, expression => SmartPropExpressionEvaluator.Evaluate(expression, this));

    private static Dictionary<string, SmartPropValue> CopyValues(IReadOnlyDictionary<string, SmartPropValue>? values)
        => values is null
            ? new Dictionary<string, SmartPropValue>(StringComparer.OrdinalIgnoreCase)
            : new Dictionary<string, SmartPropValue>(values, StringComparer.OrdinalIgnoreCase);
}
