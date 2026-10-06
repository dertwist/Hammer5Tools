using System.Numerics;
using System.Text.Json.Nodes;

using ValveResourceFormat.ResourceTypes;
using ValveResourceFormat.ResourceTypes.SmartProps;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Deforms models placed under a <c>CSmartPropElement_MidpointDeformer</c>.
/// </summary>
/// <remarks>
/// Same gap as <see cref="SmartPropBendDeformerEvaluator"/>: VRF applies a MidpointDeformer's
/// <c>m_Modifiers</c> like any other pass-through group but never reads its own
/// <c>m_vStart</c>/<c>m_vEnd</c>/<c>m_fRadius</c>/<c>m_fFalloff</c>/<c>m_vOffset</c>/<c>m_vAngles</c>/
/// <c>m_vScale</c>/<c>m_bDeformationEnabled</c> fields. This runs as a correction pass over the
/// models VRF already produced.
///
/// There's no editor-time source for Valve's exact formula, so this follows the documented field
/// semantics directly: <c>m_vOffset</c>/<c>m_vAngles</c>/<c>m_vScale</c> describe the deformation
/// at full strength at the segment's midpoint; that strength fades to nothing at <c>m_fRadius</c>
/// away, shaped by <c>m_fFalloff</c> (as an exponent) and smoothed if <c>m_bContinuousSpline</c> is
/// set. <c>m_OutputVariable</c> (presumably the per-point blend weight, for other operations to
/// read) isn't wired up — nothing downstream in a single evaluation pass could consume a
/// per-descendant value like that today.
/// </remarks>
internal static class SmartPropMidpointDeformerEvaluator
{
    private const string ProbeModel = "__hammer5tools_midpoint_probe__.vmdl";
    private const float Epsilon = 1e-4f;

    public static IReadOnlyList<EvaluatedSmartPropModel> ApplyMidpointDeformers(
        string json,
        string? nestedDocumentsJson,
        IReadOnlyList<EvaluatedSmartPropModel> models,
        SmartPropEvaluationOptions options)
    {
        if (JsonNode.Parse(json) is not JsonObject root)
            return models;

        var deformers = SmartPropWidgetEvaluator.CollectElementsWithDescendants(root, "MidpointDeformer");
        if (deformers.Count == 0)
            return models;

        var nestedDocuments = nestedDocumentsJson is null ? null : JsonNode.Parse(nestedDocumentsJson) as JsonObject;
        var context = SmartPropWidgetEvaluator.CreateContext(root);
        var corrected = models.ToList();

        foreach (var deformer in deformers.OrderByDescending(deformer => deformer.Depth))
        {
            options.CancellationToken.ThrowIfCancellationRequested();

            if (deformer.DescendantModelIds.Count == 0)
                continue;

            var deform = ResolveDeformParams(deformer.Node, context);
            if (!deform.Enabled || deform.Radius < Epsilon)
                continue;

            var deformerFrame = SmartPropWidgetEvaluator.ProbeElementFrame(root, nestedDocuments, deformer.Path, options, ProbeModel);
            if (deformerFrame is not { } frame || !Matrix4x4.Invert(frame, out var invFrame))
                continue;

            var midpoint = (deform.Start + deform.End) / 2f;
            var fullRotation = Quaternion.CreateFromRotationMatrix(EntityTransformHelper.EulerAnglesToRotationMatrix(deform.Angles));

            for (var i = 0; i < corrected.Count; i++)
            {
                var model = corrected[i];
                if (!deformer.DescendantModelIds.Contains(model.ElementId))
                    continue;

                var local = model.Transform * invFrame;
                if (!Matrix4x4.Decompose(local, out var scale, out var rotation, out var translation))
                    continue;

                var weight = Weight(Vector3.Distance(translation, midpoint), deform);
                if (weight < Epsilon)
                    continue;

                var blendedRotation = Quaternion.Slerp(Quaternion.Identity, fullRotation, weight);
                var blendedScale = Vector3.Lerp(Vector3.One, deform.Scale, weight);
                var blendedOffset = deform.Offset * weight;

                var newTranslation = midpoint
                    + Vector3.Transform((translation - midpoint) * blendedScale, blendedRotation)
                    + blendedOffset;
                var newRotation = Quaternion.Normalize(blendedRotation * rotation);

                var newLocal = Matrix4x4.CreateScale(scale)
                    * Matrix4x4.CreateFromQuaternion(newRotation)
                    * Matrix4x4.CreateTranslation(newTranslation);
                corrected[i] = model with { Transform = newLocal * frame };
            }
        }

        return corrected;
    }

    /// <summary>Blend weight: 1 at the midpoint, fading to 0 at <see cref="DeformParams.Radius"/>.</summary>
    private static float Weight(float distance, DeformParams deform)
    {
        var raw = Math.Clamp(1f - (distance / deform.Radius), 0f, 1f);
        var shaped = deform.ContinuousSpline ? raw * raw * (3f - (2f * raw)) : raw;
        return MathF.Pow(shaped, MathF.Max(deform.Falloff, 0.01f));
    }

    private static DeformParams ResolveDeformParams(JsonObject node, SmartPropContext context)
    {
        var enabled = SmartPropWidgetEvaluator.ResolveScalar(node["m_bDeformationEnabled"], context, 1f) > 0.5f;
        var start = SmartPropWidgetEvaluator.ResolveVector(node["m_vStart"], context);
        var end = SmartPropWidgetEvaluator.ResolveVector(node["m_vEnd"], context);
        var radius = SmartPropWidgetEvaluator.ResolveScalar(node["m_fRadius"], context);
        var falloff = SmartPropWidgetEvaluator.ResolveScalar(node["m_fFalloff"], context, 1f);
        var continuousSpline = SmartPropWidgetEvaluator.ResolveScalar(node["m_bContinuousSpline"], context, 1f) > 0.5f;
        var offset = SmartPropWidgetEvaluator.ResolveVector(node["m_vOffset"], context);
        var angles = SmartPropWidgetEvaluator.ResolveVector(node["m_vAngles"], context);
        var scale = SmartPropWidgetEvaluator.ResolveVector(node["m_vScale"], context, Vector3.One);

        return new(enabled, start, end, radius, falloff, continuousSpline, offset, angles, scale);
    }

    private readonly record struct DeformParams(
        bool Enabled, Vector3 Start, Vector3 End, float Radius, float Falloff, bool ContinuousSpline,
        Vector3 Offset, Vector3 Angles, Vector3 Scale);
}
