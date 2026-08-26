using ValveKeyValue;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Seeds <c>CSmartPropOperation_CreateSizer</c>-driven variable defaults from the sizer's own
/// initial extent, before VRF evaluates any geometry that reads those variables.
/// </summary>
/// <remarks>
/// Hammer's editor always leaves a sizer-driven variable's own <c>m_DefaultValue</c> at 0 (or
/// <c>""</c>) — the sizer's <c>m_flInitial*</c> fields are the only place the real starting value
/// lives, normally supplied live by the interactive handle. <see cref="SmartPropWidgetEvaluator"/>
/// already reads that initial value, but only to position the editor's sizer gizmo; it never
/// feeds it back into <c>m_Variables</c>, so a headless evaluation (this tool's viewport preview)
/// sees the variable's raw 0 default instead — collapsing e.g. a FitOnLine line built from a
/// sizer-driven length down to zero. Every shipped preset that uses CreateSizer follows this same
/// authoring convention, so the override below always applies rather than only filling in an
/// already-zero value.
/// </remarks>
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
                    var variableName = outputNode.ToString(null);
                    if (variableName.Length > 0)
                        overrides[variableName] = initialNode.ToSingle();
                }
            }
        }

        foreach (var (_, child) in node.Children)
            CollectSizerOverrides(child, overrides);
    }
}
