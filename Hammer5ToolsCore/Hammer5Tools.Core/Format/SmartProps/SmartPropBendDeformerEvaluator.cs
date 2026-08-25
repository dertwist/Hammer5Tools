using System.Numerics;
using System.Text.Json.Nodes;

using ValveResourceFormat.ResourceTypes;
using ValveResourceFormat.ResourceTypes.SmartProps;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Bends models placed under a <c>CSmartPropElement_BendDeformer</c>.
/// </summary>
/// <remarks>
/// VRF's own evaluator (<see cref="SmartPropEvaluation"/>, wrapped by <see cref="SmartPropEvaluator"/>)
/// treats a BendDeformer as a transparent pass-through group: it applies the element's
/// <c>m_Modifiers</c> like any other element, but never reads its own
/// <c>m_vOrigin</c>/<c>m_vAngles</c>/<c>m_vSize</c>/<c>m_flBendAngle</c>/<c>m_flBendPoint</c>/
/// <c>m_flBendRadius</c>/<c>m_bDeformationEnabled</c> fields, so descendants come out straight.
/// This runs as a correction pass over the models VRF already produced.
/// </remarks>
internal static class SmartPropBendDeformerEvaluator
{
    private const string BendProbeModel = "__hammer5tools_bend_probe__.vmdl";
    private const float Epsilon = 1e-4f;

    public static IReadOnlyList<EvaluatedSmartPropModel> ApplyBendDeformers(
        string json,
        string? nestedDocumentsJson,
        IReadOnlyList<EvaluatedSmartPropModel> models,
        SmartPropEvaluationOptions options)
    {
        if (JsonNode.Parse(json) is not JsonObject root)
            return models;

        var deformers = new List<DeformerInfo>();
        CollectDeformers(root, [], deformers, [], underPlaceOnPath: false);
        if (deformers.Count == 0)
            return models;

        var nestedDocuments = nestedDocumentsJson is null ? null : JsonNode.Parse(nestedDocumentsJson) as JsonObject;
        var context = SmartPropWidgetEvaluator.CreateContext(root);
        var corrected = models.ToList();

        foreach (var deformer in deformers.OrderByDescending(deformer => deformer.Depth))
        {
            options.CancellationToken.ThrowIfCancellationRequested();

            if (deformer.SkipRepeated || deformer.DescendantModelIds.Count == 0)
                continue;

            var bend = ResolveBendParams(deformer.Node, context);
            if (!bend.Enabled || MathF.Abs(bend.ThetaTotal) < 1e-5f || bend.SizeX < Epsilon || MathF.Abs(bend.Radius) < Epsilon)
                continue;

            var deformerFrame = ProbeDeformerFrame(root, nestedDocuments, deformer.Path, options);
            if (deformerFrame is not { } frame || !Matrix4x4.Invert(frame, out var invFrame))
                continue;

            var volumeFrame = EntityTransformHelper.EulerAnglesToRotationMatrix(bend.Angles) * Matrix4x4.CreateTranslation(bend.Origin);
            if (!Matrix4x4.Invert(volumeFrame, out var invVolumeFrame))
                continue;

            for (var i = 0; i < corrected.Count; i++)
            {
                var model = corrected[i];
                if (!deformer.DescendantModelIds.Contains(model.ElementId))
                    continue;

                var volumeLocal = model.Transform * invFrame * invVolumeFrame;
                if (!Matrix4x4.Decompose(volumeLocal, out var scale, out var rotation, out var translation))
                    continue;

                var (newPosition, newRotation) = BendLocalPoint(translation, rotation, bend);
                var newVolumeLocal =
                    Matrix4x4.CreateScale(scale)
                    * Matrix4x4.CreateFromQuaternion(newRotation)
                    * Matrix4x4.CreateTranslation(newPosition);

                corrected[i] = model with { Transform = newVolumeLocal * volumeFrame * frame };
            }
        }

        return corrected;
    }

    /// <summary>
    /// Bends one point/orientation, expressed in the deformer's volume-local space, along a
    /// constant-curvature arc: local X sweeps around local Z, hinged at <see cref="BendParams.PivotX"/>.
    /// Valve's exact internal formula isn't published; this follows the documented field semantics
    /// (auto radius keeps the y=0 edge's arc length equal to the unbent size; an explicit radius
    /// overrides that and the length changes instead, matching the schema's own wording).
    /// </summary>
    private static (Vector3 Position, Quaternion Rotation) BendLocalPoint(Vector3 position, Quaternion rotation, BendParams bend)
    {
        var phi = (position.X - bend.PivotX) / bend.Radius;
        var effectiveRadius = bend.Radius - position.Y;
        var newPosition = new Vector3(
            bend.PivotX + (effectiveRadius * MathF.Sin(phi)),
            bend.Radius - (effectiveRadius * MathF.Cos(phi)),
            position.Z);
        var newRotation = rotation * Quaternion.CreateFromAxisAngle(Vector3.UnitZ, phi);
        return (newPosition, newRotation);
    }

    private static BendParams ResolveBendParams(JsonObject node, SmartPropContext context)
    {
        var enabled = SmartPropWidgetEvaluator.ResolveScalar(node["m_bDeformationEnabled"], context, 1f) > 0.5f;
        var origin = SmartPropWidgetEvaluator.ResolveVector(node["m_vOrigin"], context);
        var angles = SmartPropWidgetEvaluator.ResolveVector(node["m_vAngles"], context);
        var size = SmartPropWidgetEvaluator.ResolveVector(node["m_vSize"], context);
        var bendAngleDegrees = SmartPropWidgetEvaluator.ResolveScalar(node["m_flBendAngle"], context);
        var bendPoint = SmartPropWidgetEvaluator.ResolveScalar(node["m_flBendPoint"], context);
        var bendRadius = SmartPropWidgetEvaluator.ResolveScalar(node["m_flBendRadius"], context);

        var thetaTotal = bendAngleDegrees * (MathF.PI / 180f);
        var pivotX = Math.Clamp(bendPoint, 0f, 1f) * size.X;
        var radius = MathF.Abs(bendRadius) > Epsilon
            ? bendRadius
            : (MathF.Abs(thetaTotal) > 1e-5f ? size.X / thetaTotal : 0f);

        return new(enabled, origin, angles, size.X, thetaTotal, pivotX, radius);
    }

    /// <summary>
    /// Resolves the deformer element's own accumulated world transform by rigging a clone of it
    /// as a <c>CSmartPropElement_Model</c> (keeping its real <c>m_Modifiers</c> and ancestor chain)
    /// and letting VRF's real evaluator compute the placement — the same technique
    /// <see cref="SmartPropWidgetEvaluator"/> uses to probe modifier positions, since
    /// <c>SmartPropModifierEvaluator</c>'s modifier/transform composition is internal to VRF.
    /// </summary>
    private static Matrix4x4? ProbeDeformerFrame(
        JsonObject root, JsonObject? nestedDocuments, IReadOnlyList<SmartPropWidgetEvaluator.PathPart> path, SmartPropEvaluationOptions options)
    {
        if (root.DeepClone() is not JsonObject clone)
            return null;
        if (SmartPropWidgetEvaluator.FindObject(clone, path) is not { } element)
            return null;

        element["_class"] = "CSmartPropElement_Model";
        element["m_sModelName"] = BendProbeModel;
        element.Remove("m_vModelScale");
        element.Remove("m_flModelScale");
        element.Remove("m_flUniformModelScale");

        var resolver = nestedDocuments is null ? null : SmartPropWidgetEvaluator.CreateNestedResolver(nestedDocuments);
        var evaluated = SmartPropEvaluation.Evaluate(
            SmartPropJsonConverter.Convert(clone.ToJsonString()),
            resolver,
            options.MaximumDepth);

        foreach (var placement in evaluated.Models)
        {
            if (placement.ModelName == BendProbeModel)
                return placement.Transform;
        }

        return null;
    }

    private static void CollectDeformers(
        JsonNode? node,
        List<SmartPropWidgetEvaluator.PathPart> path,
        List<DeformerInfo> deformers,
        List<int> activeDeformerIndexes,
        bool underPlaceOnPath)
    {
        if (node is JsonObject obj)
        {
            var className = SmartPropWidgetEvaluator.ReadString(obj, "_class");
            var pushedDeformer = false;

            if (ClassIs(className, "BendDeformer"))
            {
                deformers.Add(new DeformerInfo(
                    path.ToArray(),
                    SmartPropWidgetEvaluator.ReadInt32(obj, "m_nElementID"),
                    obj,
                    activeDeformerIndexes.Count,
                    underPlaceOnPath,
                    []));
                activeDeformerIndexes.Add(deformers.Count - 1);
                pushedDeformer = true;
            }
            else if (IsModelClass(className))
            {
                var elementId = SmartPropWidgetEvaluator.ReadInt32(obj, "m_nElementID");
                foreach (var index in activeDeformerIndexes)
                    deformers[index].DescendantModelIds.Add(elementId);
            }

            var nextUnderPlaceOnPath = underPlaceOnPath || ClassIs(className, "PlaceOnPath");
            foreach (var property in obj)
            {
                path.Add(new(property.Key, null));
                CollectDeformers(property.Value, path, deformers, activeDeformerIndexes, nextUnderPlaceOnPath);
                path.RemoveAt(path.Count - 1);
            }

            if (pushedDeformer)
                activeDeformerIndexes.RemoveAt(activeDeformerIndexes.Count - 1);
        }
        else if (node is JsonArray array)
        {
            for (var index = 0; index < array.Count; index++)
            {
                path.Add(new(null, index));
                CollectDeformers(array[index], path, deformers, activeDeformerIndexes, underPlaceOnPath);
                path.RemoveAt(path.Count - 1);
            }
        }
    }

    private static bool IsModelClass(string className)
        => ClassIs(className, "Model") || ClassIs(className, "ModelEntity")
            || ClassIs(className, "PropPhysics") || ClassIs(className, "PropDynamic");

    private static bool ClassIs(string className, string shortName)
        => className.Equals(shortName, StringComparison.Ordinal)
            || className.Equals("CSmartPropElement_" + shortName, StringComparison.Ordinal);

    private readonly record struct BendParams(
        bool Enabled, Vector3 Origin, Vector3 Angles, float SizeX, float ThetaTotal, float PivotX, float Radius);

    private sealed record DeformerInfo(
        SmartPropWidgetEvaluator.PathPart[] Path,
        int ElementId,
        JsonObject Node,
        int Depth,
        bool SkipRepeated,
        HashSet<int> DescendantModelIds);
}
