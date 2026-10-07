using System.Numerics;
using Hammer5Tools.Core.Format.SmartProps.Evaluation;
using ValveKeyValue;
using ValveResourceFormat.ResourceTypes;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Deforms models placed under a <c>CSmartPropElement_MidpointDeformer</c>.
/// </summary>
internal static class SmartPropMidpointDeformerEvaluator
{
    private const float Epsilon = 1e-4f;

    internal static Func<EvaluatedSmartPropModel, KVObject, SmartPropEvaluationContext, EvaluatedSmartPropModel>? Create(
        KVObject element, Matrix4x4 frame, SmartPropEvaluationContext context)
    {
        var deform = ResolveDeformParams(element, context);
        if (!deform.Enabled || deform.Radius < Epsilon || !Matrix4x4.Invert(frame, out var invFrame))
        {
            return null;
        }
        var midpoint = (deform.Start + deform.End) / 2f;
        var fullRotation = Quaternion.CreateFromRotationMatrix(SmartPropTransformMath.EulerAnglesToRotationMatrix(deform.Angles));
        return (model, _, _) =>
        {
            var local = model.Transform * invFrame;
            if (!Matrix4x4.Decompose(local, out var scale, out var rotation, out var translation))
                return model;

            var weight = Weight(Vector3.Distance(translation, midpoint), deform);
            if (weight < Epsilon)
                return model;

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
            return model with { Transform = newLocal * frame };
        };
    }

    /// <summary>Blend weight: 1 at the midpoint, fading to 0 at <see cref="DeformParams.Radius"/>.</summary>
    private static float Weight(float distance, DeformParams deform)
    {
        var raw = Math.Clamp(1f - (distance / deform.Radius), 0f, 1f);
        var shaped = deform.ContinuousSpline ? raw * raw * (3f - (2f * raw)) : raw;
        return MathF.Pow(shaped, MathF.Max(deform.Falloff, 0.01f));
    }

    private static DeformParams ResolveDeformParams(KVObject node, SmartPropEvaluationContext context)
    {
        var enabled = context.ResolveScalar(ReadValue(node, "m_bDeformationEnabled"), 1f) > 0.5f;
        var start = context.ResolveVector3(ReadValue(node, "m_vStart"));
        var end = context.ResolveVector3(ReadValue(node, "m_vEnd"));
        var radius = context.ResolveScalar(ReadValue(node, "m_fRadius"));
        var falloff = context.ResolveScalar(ReadValue(node, "m_fFalloff"), 1f);
        var continuousSpline = context.ResolveScalar(ReadValue(node, "m_bContinuousSpline"), 1f) > 0.5f;
        var offset = context.ResolveVector3(ReadValue(node, "m_vOffset"));
        var angles = context.ResolveVector3(ReadValue(node, "m_vAngles"));
        var scale = context.ResolveVector3(ReadValue(node, "m_vScale"), Vector3.One);

        return new(enabled, start, end, radius, falloff, continuousSpline, offset, angles, scale);
    }

    private static KVObject? ReadValue(KVObject node, string name)
        => node.TryGetValue(name, out var value) ? value : null;

    private readonly record struct DeformParams(
        bool Enabled, Vector3 Start, Vector3 End, float Radius, float Falloff, bool ContinuousSpline,
        Vector3 Offset, Vector3 Angles, Vector3 Scale);
}
