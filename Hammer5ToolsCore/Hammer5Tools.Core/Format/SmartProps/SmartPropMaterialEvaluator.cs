using System.Text.Json.Nodes;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Resolves the SmartProp material and tint operations, which VRF's evaluator either ignores
/// outright or handles only partially.
/// </summary>
/// <remarks>
/// VRF reads <c>CSmartPropOperation_SetTintColor</c>'s <c>m_ColorChoices</c> but not its
/// <c>m_SelectionMode</c>, <c>m_ColorSelection</c> or <c>m_Mode</c>, so a document that picks a
/// specific swatch by variable, or multiplies rather than replaces, previewed with the wrong
/// colour. It has no notion of <c>MaterialTint</c> or <c>MaterialOverride</c> at all. This pass
/// re-derives all three by walking the document itself and inheriting each element's operations
/// down to the models beneath it, exactly as the modifier stack does, then rewrites the affected
/// placements. It runs last, after the multiplicity passes, so cloned placements pick up the same
/// state as the model they were cloned from.
///
/// Material names are matched by path, so an operation whose <c>m_Material</c> (or replacement
/// pair) is a variable reference rather than a literal string is skipped: resolving a *string*
/// variable is not something <see cref="SmartPropContext"/> can do — it carries scalars and
/// vectors only.
/// </remarks>
internal static class SmartPropMaterialEvaluator
{
    public static IReadOnlyList<EvaluatedSmartPropModel> ApplyMaterialOperations(
        string json,
        IReadOnlyList<EvaluatedSmartPropModel> models,
        SmartPropEvaluationOptions options)
    {
        if (models.Count == 0 || JsonNode.Parse(json) is not JsonObject root)
            return models;

        var context = SmartPropWidgetEvaluator.CreateContext(root);
        var states = new Dictionary<int, MaterialState>();
        Collect(root, MaterialState.Empty, context, states, options);
        if (states.Count == 0)
            return models;

        var corrected = new List<EvaluatedSmartPropModel>(models.Count);
        foreach (var model in models)
        {
            options.CancellationToken.ThrowIfCancellationRequested();
            corrected.Add(ResolveState(states, model.ElementId) is { IsEmpty: false } state
                ? state.ApplyTo(model)
                : model);
        }
        return corrected;
    }

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

    /// <summary>
    /// Finds the state authored for a placement, falling back to the element it was cloned from.
    /// The multiplicity passes number their copies <c>id + k * stride</c>, and a copy inherits the
    /// original's materials.
    /// </summary>
    private static MaterialState? ResolveState(Dictionary<int, MaterialState> states, int elementId)
    {
        if (states.TryGetValue(elementId, out var state))
            return state;
        var originalId = (int)(elementId % SmartPropWidgetEvaluator.ElementIdStride);
        return states.TryGetValue(originalId, out state) ? state : null;
    }

    private static void Collect(
        JsonNode? node,
        MaterialState inherited,
        SmartPropContext context,
        Dictionary<int, MaterialState> states,
        SmartPropEvaluationOptions options)
    {
        options.CancellationToken.ThrowIfCancellationRequested();

        if (node is JsonArray array)
        {
            foreach (var item in array)
                Collect(item, inherited, context, states, options);
            return;
        }

        if (node is not JsonObject obj)
            return;

        var state = Fold(inherited, obj, context);
        var className = SmartPropWidgetEvaluator.ReadString(obj, "_class");
        if (SmartPropWidgetEvaluator.IsModelClass(className) && !state.IsEmpty)
            states[SmartPropWidgetEvaluator.ReadInt32(obj, "m_nElementID")] = state;

        foreach (var property in obj)
            Collect(property.Value, state, context, states, options);
    }

    /// <summary>Folds one element's own enabled material modifiers onto the inherited state.</summary>
    private static MaterialState Fold(MaterialState state, JsonObject node, SmartPropContext context)
    {
        if (node["m_Modifiers"] is not JsonArray modifiers)
            return state;

        foreach (var modifier in modifiers.OfType<JsonObject>())
        {
            if (!IsEnabled(modifier, context))
                continue;

            var className = SmartPropWidgetEvaluator.ReadString(modifier, "_class");
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
    private static bool IsEnabled(JsonObject node, SmartPropContext context)
        => node["m_bEnabled"] is not { } enabled
            || SmartPropWidgetEvaluator.ResolveScalar(enabled, context, 1f) != 0f;

    private static Vector4 ResolveTint(JsonObject modifier, SmartPropContext context, Vector4 current)
    {
        var color = SelectColor(modifier, context);
        return SmartPropWidgetEvaluator.ReadString(modifier, "m_Mode", "MULTIPLY_OBJECT") switch
        {
            "REPLACE" => color,
            "MULTIPLY_CURRENT" => current * color,
            // MULTIPLY_OBJECT multiplies the model's own albedo, which is what a consumer does
            // with the tint regardless, so it starts from this operation's colour alone and
            // deliberately discards whatever an ancestor accumulated.
            _ => color,
        };
    }

    private static Vector4 SelectColor(JsonObject modifier, SmartPropContext context)
    {
        if (modifier["m_ColorChoices"] is not JsonArray choices || choices.Count == 0)
            return Vector4.One;

        var index = SmartPropWidgetEvaluator.ReadString(modifier, "m_SelectionMode", "RANDOM") switch
        {
            "SPECIFIC" => (int)SmartPropWidgetEvaluator.ResolveScalar(modifier["m_ColorSelection"], context),
            _ => (int)(Salt(SmartPropWidgetEvaluator.ReadInt32(modifier, "m_nElementID")) % (uint)choices.Count),
        };

        var choice = choices[Math.Clamp(index, 0, choices.Count - 1)] as JsonObject;
        return new(SmartPropWidgetEvaluator.ResolveColor(choice?["m_Color"], context, Vector3.One), 1f);
    }

    private static MaterialState ApplyMaterialTint(MaterialState state, JsonObject modifier, SmartPropContext context)
    {
        var material = SmartPropWidgetEvaluator.ReadString(modifier, "m_Material");
        if (material.Length == 0)
            return state;

        // Only SPECIFIC_COLOR is resolvable: the gradient selection modes read a colour ramp
        // whose authored shape this editor does not model, and m_Color is the one field every
        // mode carries.
        var color = SmartPropWidgetEvaluator.ResolveColor(modifier["m_Color"], context, Vector3.One);
        return state with
        {
            MaterialTints = [.. state.MaterialTints,
                new EvaluatedSmartPropMaterialTint(NormalizeMaterialName(material), new(color, 1f))],
        };
    }

    private static MaterialState ApplyMaterialOverride(MaterialState state, JsonObject modifier)
    {
        var cleared = modifier["m_bClearCurrentOverrides"] is JsonValue clear
            && clear.TryGetValue<bool>(out var value) && value;
        var overrides = cleared
            ? new List<EvaluatedSmartPropMaterialReplacement>()
            : [.. state.MaterialOverrides];

        if (modifier["m_MaterialReplacements"] is JsonArray replacements)
        {
            foreach (var replacement in replacements.OfType<JsonObject>())
            {
                var original = SmartPropWidgetEvaluator.ReadString(replacement, "m_OriginalMaterial");
                var target = SmartPropWidgetEvaluator.ReadString(replacement, "m_ReplacementMaterial");
                if (original.Length == 0 || target.Length == 0)
                    continue;
                overrides.Add(new(NormalizeMaterialName(original), NormalizeMaterialName(target)));
            }
        }

        return state with { MaterialOverrides = overrides };
    }

    /// <summary>One LCG step, matching <see cref="SmartPropContext"/>'s own generator, so a
    /// RANDOM swatch pick is stable for an element instead of changing on every redraw.</summary>
    private static uint Salt(int elementId) => ((uint)elementId * 1_664_525u) + 1_013_904_223u;

    private sealed record MaterialState(
        Vector4 Tint,
        IReadOnlyList<EvaluatedSmartPropMaterialTint> MaterialTints,
        IReadOnlyList<EvaluatedSmartPropMaterialReplacement> MaterialOverrides)
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
