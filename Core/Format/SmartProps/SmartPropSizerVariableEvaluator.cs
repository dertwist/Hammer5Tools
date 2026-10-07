using System.Globalization;
using ValveKeyValue;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Seeds <c>CSmartPropOperation_CreateSizer</c>-driven variable defaults from the sizer's own
/// initial extent, before VRF evaluates any geometry that reads those variables.
/// </summary>
internal static class SmartPropSizerVariableEvaluator
{
    private static readonly (string Output, string Initial)[] Axes =
    [
        ("m_OutputVariableMinX", "m_flInitialMinX"), ("m_OutputVariableMaxX", "m_flInitialMaxX"),
        ("m_OutputVariableMinY", "m_flInitialMinY"), ("m_OutputVariableMaxY", "m_flInitialMaxY"),
        ("m_OutputVariableMinZ", "m_flInitialMinZ"), ("m_OutputVariableMaxZ", "m_flInitialMaxZ"),
    ];

    public static void SeedSizerVariableDefaults(KVObject root)
    {
        if (!root.TryGetValue("m_Variables", out var variables) || variables.ValueType != KVValueType.Array)
            return;

        var overrides = new Dictionary<string, float>(StringComparer.OrdinalIgnoreCase);
        CollectSizerOverrides(root, overrides);
        if (overrides.Count == 0)
            return;

        foreach (var variable in variables.Values)
        {
            if (variable.ValueType != KVValueType.Collection)
                continue;
            if (!variable.TryGetValue("m_VariableName", out var nameNode) || nameNode.IsNull)
                continue;

            var name = nameNode.ToString(null);
            if (name.Length > 0 && overrides.TryGetValue(name, out var value))
                variable["m_DefaultValue"] = new KVObject(value);
        }
    }

    private static void CollectSizerOverrides(KVObject node, Dictionary<string, float> overrides)
    {
        if (node.ValueType is not (KVValueType.Collection or KVValueType.Array))
            return;

        if (node.ValueType == KVValueType.Collection
            && node.TryGetValue("_class", out var classNode)
            && !classNode.IsNull
            && classNode.ToString(null).EndsWith("CreateSizer", StringComparison.Ordinal))
        {
            foreach (var (output, initial) in Axes)
            {
                if (node.TryGetValue(output, out var outputNode) && !outputNode.IsNull
                    && node.TryGetValue(initial, out var initialNode) && !initialNode.IsNull)
                {
                    var variableName = outputNode.ToString(CultureInfo.InvariantCulture);
                    if (variableName.Length > 0)
                    {
                        var raw = initialNode.ToString(CultureInfo.InvariantCulture).Replace('−', '-');
                        if (float.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var value))
                            overrides[variableName] = value;
                    }
                }
            }
        }

        foreach (var (_, child) in node.Children)
            CollectSizerOverrides(child, overrides);
    }
}
