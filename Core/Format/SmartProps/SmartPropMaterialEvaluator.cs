using Hammer5Tools.Core.Format.SmartProps.Evaluation;
using ValveKeyValue;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Resolves the SmartProp material and tint operations, which VRF's evaluator either ignores
/// outright or handles only partially.
/// </summary>
internal static class SmartPropMaterialEvaluator
{
    /// <summary>
    /// Lowercases a material path and normalizes its separators so an authored
    /// <c>m_Material</c> can be compared against the path a compiled model reports for its
    /// submesh. The <c>_c</c> compiled suffix is dropped: documents name the source
    /// <c>.vmat</c>, models may reference either.
    /// </summary>
    internal static string NormalizeMaterialName(string path)
    {
        var normalized = path.Replace('\\', '/').TrimStart('/').Trim();
        if (normalized.EndsWith("_c", StringComparison.OrdinalIgnoreCase))
            normalized = normalized[..^2];
        return normalized.ToLowerInvariant();
    }

    /// <summary>Folds one element's own enabled material modifiers onto the inherited state.</summary>
    internal static MaterialState Fold(MaterialState state, KVObject node, SmartPropEvaluationContext context)
    {
        if (!node.TryGetValue("m_Modifiers", out var modifiers) || !modifiers.IsArray)
            return state;

        foreach (var modifier in modifiers.AsArraySpan())
        {
            if (!IsEnabled(modifier, context))
                continue;

            var className = SmartPropClass.Read(modifier);
            if (IsOperation(className, "SetTintColor"))
                state = state with { Tint = ResolveTint(modifier, context, state.Tint) };
            else if (IsOperation(className, "MaterialTint"))
                state = ApplyMaterialTint(state, modifier, context);
            else if (IsOperation(className, "MaterialOverride"))
                state = ApplyMaterialOverride(state, modifier);
        }
        return state;
    }

    private static bool IsOperation(string className, string shortName)
        => className.Equals(shortName, StringComparison.Ordinal)
            || className.Equals("CSmartPropOperation_" + shortName, StringComparison.Ordinal);

    /// <summary>
    /// <c>m_bEnabled</c> is not always a literal: real documents gate a modifier on an expression
    /// or a variable, so it is resolved rather than read.
    /// </summary>
    private static bool IsEnabled(KVObject node, SmartPropEvaluationContext context)
        => ReadValue(node, "m_bEnabled") is not { } enabled
            || context.ResolveScalar(enabled, 1f) != 0f;

    private static Vector4 ResolveTint(KVObject modifier, SmartPropEvaluationContext context, Vector4 current)
    {
        var color = SelectColor(modifier, context);
        return ReadString(modifier, "m_Mode", "MULTIPLY_OBJECT") switch
        {
            "REPLACE" => color,
            "MULTIPLY_CURRENT" => current * color,
            // MULTIPLY_OBJECT multiplies the model's own albedo, which is what a consumer does
            // with the tint regardless, so it starts from this operation's colour alone and
            // deliberately discards whatever an ancestor accumulated.
            _ => color,
        };
    }

    private static Vector4 SelectColor(KVObject modifier, SmartPropEvaluationContext context)
    {
        if (!modifier.TryGetValue("m_ColorChoices", out var choices) || !choices.IsArray || choices.AsArraySpan().Length == 0)
            return Vector4.One;

        var index = ReadString(modifier, "m_SelectionMode", "RANDOM") switch
        {
            "SPECIFIC" => (int)context.ResolveScalar(ReadValue(modifier, "m_ColorSelection")),
            _ => (int)(Salt((int)context.ResolveScalar(ReadValue(modifier, "m_nElementID"))) % (uint)choices.AsArraySpan().Length),
        };

        var choice = choices.AsArraySpan()[Math.Clamp(index, 0, choices.AsArraySpan().Length - 1)];
        return new(ResolveColor(ReadValue(choice, "m_Color"), context, Vector3.One), 1f);
    }

    private static MaterialState ApplyMaterialTint(MaterialState state, KVObject modifier, SmartPropEvaluationContext context)
    {
        var material = ReadString(modifier, "m_Material");
        if (material.Length == 0)
            return state;

        // Only SPECIFIC_COLOR is resolvable: the gradient selection modes read a colour ramp
        // whose authored shape this editor does not model, and m_Color is the one field every
        // mode carries.
        var color = ResolveColor(ReadValue(modifier, "m_Color"), context, Vector3.One);
        return state with
        {
            MaterialTints = [.. state.MaterialTints,
                new EvaluatedSmartPropMaterialTint(NormalizeMaterialName(material), new(color, 1f))],
        };
    }

    private static MaterialState ApplyMaterialOverride(MaterialState state, KVObject modifier)
    {
        var cleared = modifier.TryGetValue("m_bClearCurrentOverrides", out var clear)
            && clear.ValueType == KVValueType.Boolean && (bool)clear;
        var overrides = cleared
            ? new List<EvaluatedSmartPropMaterialReplacement>()
            : [.. state.MaterialOverrides];

        if (modifier.TryGetValue("m_MaterialReplacements", out var replacements) && replacements.IsArray)
        {
            foreach (var replacement in replacements.AsArraySpan())
            {
                var original = ReadString(replacement, "m_OriginalMaterial");
                var target = ReadString(replacement, "m_ReplacementMaterial");
                if (original.Length == 0 || target.Length == 0)
                    continue;
                overrides.Add(new(NormalizeMaterialName(original), NormalizeMaterialName(target)));
            }
        }

        return state with { MaterialOverrides = overrides };
    }

    private static KVObject? ReadValue(KVObject node, string name)
        => node.TryGetValue(name, out var value) ? value : null;

    private static string ReadString(KVObject node, string name, string fallback = "")
        => node.TryGetValue(name, out var value) && value.ValueType == KVValueType.String ? (string)value : fallback;

    private static Vector3 ResolveColor(KVObject? value, SmartPropEvaluationContext context, Vector3 fallback)
    {
        var color = context.ResolveVector3(value, fallback);
        if (color.X > 1f || color.Y > 1f || color.Z > 1f)
        {
            color /= 255f;
        }
        return Vector3.Clamp(color, Vector3.Zero, Vector3.One);
    }

    /// <summary>One LCG step, retaining the legacy preview generator, so a
    /// RANDOM swatch pick is stable for an element instead of changing on every redraw.</summary>
    private static uint Salt(int elementId) => ((uint)elementId * 1_664_525u) + 1_013_904_223u;

    internal sealed record MaterialState(
        Vector4 Tint,
        IReadOnlyList<EvaluatedSmartPropMaterialTint> MaterialTints,
        List<EvaluatedSmartPropMaterialReplacement> MaterialOverrides)
    {
        public static readonly MaterialState Empty = new(Vector4.One, [], []);

        public bool IsEmpty => Tint == Vector4.One && MaterialTints.Count == 0 && MaterialOverrides.Count == 0;

        public EvaluatedSmartPropModel ApplyTo(EvaluatedSmartPropModel model) => model with
        {
            TintColor = Tint == Vector4.One ? model.TintColor : Tint,
            MaterialTints = MaterialTints.Count == 0 ? model.MaterialTints : MaterialTints,
            MaterialOverrides = MaterialOverrides.Count == 0 ? model.MaterialOverrides : MaterialOverrides,
        };
    }
}
