using System.Numerics;
using System.Text.Json.Nodes;

using ValveResourceFormat.ResourceTypes;
using ValveResourceFormat.ResourceTypes.SmartProps;
using ValveResourceFormat.Utils;

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
///
/// The deformation itself is expressed as an 8-corner lattice cage with a cubic-Bezier curve
/// along each of the 4 edges running along local X — the same shape CS2 bakes into a compiled
/// VMAP's SmartProp deformation data (<c>m_ControlPointPositions</c> / <c>m_CurveSegmentMidpointPositions</c>,
/// consumed by a lerp-of-Bezier-edges scheme). There's no live editor-time source for Valve's own
/// cage-building formula (a compiled VMAP only carries the baked *result*), so the cage here is
/// built from the documented bend semantics — a constant-curvature circular arc, hinged at
/// <c>m_flBendPoint</c> — approximated per edge with the standard tangent-matched cubic-Bezier fit
/// (handle length <c>(4/3) * radius * tan(sweep/4)</c>), then evaluated with the same edge-lerp
/// scheme so the shape this preview computes is structurally the one CS2 would bake.
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
        var modelNodes = new Dictionary<int, JsonObject>();
        CollectDeformers(root, [], deformers, [], modelNodes, underPlaceOnPath: false);
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
            if (!bend.Enabled || MathF.Abs(bend.ThetaTotal) < 1e-5f || bend.Size.X < Epsilon || MathF.Abs(bend.Radius) < Epsilon)
                continue;

            var deformerFrame = SmartPropWidgetEvaluator.ProbeElementFrame(root, nestedDocuments, deformer.Path, options, BendProbeModel);
            if (deformerFrame is not { } frame || !Matrix4x4.Invert(frame, out var invFrame))
                continue;

            var volumeFrame = EntityTransformHelper.EulerAnglesToRotationMatrix(bend.Angles) * Matrix4x4.CreateTranslation(bend.Origin);
            if (!Matrix4x4.Invert(volumeFrame, out var invVolumeFrame))
                continue;

            var cage = BuildCage(bend);

            for (var i = 0; i < corrected.Count; i++)
            {
                var model = corrected[i];
                if (!deformer.DescendantModelIds.Contains(model.ElementId))
                    continue;

                var isRigid = modelNodes.TryGetValue(model.ElementId, out var modelNode)
                    && IsRigidDeformation(modelNode, context);
                if (!isRigid)
                {
                    // Default: only the mesh warps, the instance keeps its undeformed placement —
                    // the viewport (which owns the mesh data Core doesn't have) does the vertex warp.
                    corrected[i] = model with { Deformer = new(cage.Size, cage.ControlPoints, cage.Midpoints, frame, volumeFrame) };
                    continue;
                }

                var volumeLocal = model.Transform * invFrame * invVolumeFrame;
                if (!Matrix4x4.Decompose(volumeLocal, out var scale, out var rotation, out var translation))
                    continue;

                var newRotation = Quaternion.Normalize(rotation * CageOrientation(cage, translation));
                var newVolumeLocal =
                    Matrix4x4.CreateScale(scale)
                    * Matrix4x4.CreateFromQuaternion(newRotation)
                    * Matrix4x4.CreateTranslation(EvaluateCagePosition(cage, translation));

                corrected[i] = model with { Transform = newVolumeLocal * volumeFrame * frame };
            }
        }

        return corrected;
    }

    // Cage building — one lattice per deformer, evaluated for every descendant point.

    private readonly record struct BendCage(Vector3 Size, Vector3[] ControlPoints, Vector3[] Midpoints);

    /// <summary>
    /// Builds the 8-corner deformation cage for one BendDeformer: each corner is the exact bent
    /// position of that corner of the undeformed box, and each of the 4 longitudinal (local-X)
    /// edges gets a cubic-Bezier handle pair fitted to the true circular arc at that edge's
    /// effective radius (<c>Radius - y</c>).
    /// </summary>
    private static BendCage BuildCage(BendParams bend)
    {
        // A bend volume is routinely authored with zero thickness perpendicular to the bend axis
        // (only the X length is meaningful to the tool that drags this box — see BendParams'
        // remarks); Core has no mesh data to size Y/Z to instead. Substituting a nominal 1-unit
        // reference for a ~0 axis (rather than leaving it 0) keeps the lattice non-degenerate:
        // BendPosition is exactly linear in Y and a pure pass-through in Z, so trilinear-
        // interpolating between corners 1 unit apart still reproduces the exact analytic
        // position at any real vertex offset. Leaving the axis at 0 instead forces every vertex
        // onto the single y=0/z=0 edge (see XFraction/YFraction/ZFraction's own zero-size guard),
        // discarding its real offset and collapsing the whole mesh onto that curve — which is
        // exactly the "model vanishes" bug this fixes.
        var sizeY = EffectiveAxisSize(bend.Size.Y);
        var sizeZ = EffectiveAxisSize(bend.Size.Z);

        var controlPoints = new Vector3[8];
        for (var i = 0; i < 8; i++)
        {
            var x = (i & 4) != 0 ? bend.Size.X : 0f;
            var z = (i & 2) != 0 ? sizeZ : 0f;
            var y = (i & 1) != 0 ? sizeY : 0f;
            controlPoints[i] = BendPosition(new Vector3(x, y, z), bend);
        }

        var midpoints = new Vector3[8];
        BuildEdgeHandles(bend, 0f, controlPoints[0], controlPoints[4], midpoints, 0);
        BuildEdgeHandles(bend, sizeY, controlPoints[1], controlPoints[5], midpoints, 2);
        BuildEdgeHandles(bend, 0f, controlPoints[2], controlPoints[6], midpoints, 4);
        BuildEdgeHandles(bend, sizeY, controlPoints[3], controlPoints[7], midpoints, 6);

        return new(new Vector3(bend.Size.X, sizeY, sizeZ), controlPoints, midpoints);
    }

    private static float EffectiveAxisSize(float size) => MathF.Abs(size) > Epsilon ? size : 1f;

    private static void BuildEdgeHandles(BendParams bend, float y, Vector3 start, Vector3 end, Vector3[] midpoints, int index)
    {
        // Standard single-cubic-Bezier fit to a circular arc: handle length (4/3)*r*tan(sweep/4),
        // exact tangent direction at each endpoint. Clamped just short of a full turn so tan()
        // can't blow up — a single Bezier segment per edge (matching the baked-cage format's own
        // shape) can't represent a multi-turn bend exactly regardless; this keeps it well-behaved
        // instead of degenerate at the high end of the authored [0, 720] degree range.
        var effectiveRadius = bend.Radius - y;
        var sweep = Math.Clamp(bend.ThetaTotal, -MathF.PI * 1.9f, MathF.PI * 1.9f);
        var handleLength = (4f / 3f) * MathF.Abs(effectiveRadius) * MathF.Tan(sweep / 4f);

        var tangentStart = SafeNormalize(BendTangentX(0f, y, bend));
        var tangentEnd = SafeNormalize(BendTangentX(bend.Size.X, y, bend));
        midpoints[index] = start + (tangentStart * handleLength);
        midpoints[index + 1] = end - (tangentEnd * handleLength);
    }

    /// <summary>
    /// Exact position of a point in volume-local space under the circular-arc bend. The swept
    /// angle is always <c>bendAngle * (x/sizeX - bendPoint)</c> — a fraction of the full box
    /// length, independent of radius — matching the schema: an explicit radius changes the
    /// curve's tightness (and so its arc length), not how much of <c>m_flBendAngle</c> the box
    /// sweeps. Auto radius (<c>sizeX / bendAngle</c>) is exactly the radius that makes this
    /// coincide with the "raw x over radius" parameterization, which is why it reproduces the
    /// classic arc-length-preserving construction.
    /// </summary>
    private static Vector3 BendPosition(Vector3 local, BendParams bend)
    {
        var t = bend.Size.X > Epsilon ? local.X / bend.Size.X : 0f;
        var phi = bend.ThetaTotal * (t - bend.PivotFraction);
        var effectiveRadius = bend.Radius - local.Y;
        return new(
            bend.PivotX + (effectiveRadius * MathF.Sin(phi)),
            bend.Radius - (effectiveRadius * MathF.Cos(phi)),
            local.Z);
    }

    /// <summary>Exact derivative of <see cref="BendPosition"/> with respect to local X.</summary>
    private static Vector3 BendTangentX(float x, float y, BendParams bend)
    {
        var dPhiDx = bend.Size.X > Epsilon ? bend.ThetaTotal / bend.Size.X : 0f;
        var t = bend.Size.X > Epsilon ? x / bend.Size.X : 0f;
        var phi = bend.ThetaTotal * (t - bend.PivotFraction);
        var effectiveRadius = bend.Radius - y;
        return new(effectiveRadius * MathF.Cos(phi) * dPhiDx, effectiveRadius * MathF.Sin(phi) * dPhiDx, 0f);
    }

    /// <summary>Position of a volume-local point, read through the deformation cage.</summary>
    private static Vector3 EvaluateCagePosition(BendCage cage, Vector3 local)
    {
        var (edge00, edge10, edge01, edge11) = EvaluateEdgePositions(cage, XFraction(cage, local));
        var lower = Vector3.Lerp(edge00, edge10, YFraction(cage, local));
        var upper = Vector3.Lerp(edge01, edge11, YFraction(cage, local));
        return Vector3.Lerp(lower, upper, ZFraction(cage, local));
    }

    /// <summary>
    /// Orientation change induced by the cage at a volume-local point, as the rotation carrying
    /// the undeformed local frame onto the deformed one — derived from the cage's own exact
    /// analytic tangent (X, from the Bezier derivative) and shear (Y, from the edge-to-edge lerp
    /// direction), matching the same edge-lerp scheme <see cref="EvaluateCagePosition"/> uses.
    /// </summary>
    private static Quaternion CageOrientation(BendCage cage, Vector3 local)
    {
        var xFrac = XFraction(cage, local);
        var yFrac = YFraction(cage, local);
        var zFrac = ZFraction(cage, local);

        var (edge00, edge10, edge01, edge11) = EvaluateEdgePositions(cage, xFrac);
        var (tangent00, tangent10, tangent01, tangent11) = EvaluateEdgeTangents(cage, xFrac);

        var lowerTangent = Vector3.Lerp(tangent00, tangent10, yFrac);
        var upperTangent = Vector3.Lerp(tangent01, tangent11, yFrac);
        var tangentX = Vector3.Lerp(lowerTangent, upperTangent, zFrac) / MathF.Max(cage.Size.X, Epsilon);

        var tangentY = Vector3.Lerp(edge10 - edge00, edge11 - edge01, zFrac) / MathF.Max(cage.Size.Y, Epsilon);

        var xAxis = SafeNormalize(tangentX, Vector3.UnitX);
        var yAxisRaw = tangentY - (Vector3.Dot(tangentY, xAxis) * xAxis);
        var yAxis = SafeNormalize(yAxisRaw, Vector3.Cross(Vector3.UnitZ, xAxis));
        var zAxis = Vector3.Cross(xAxis, yAxis);

        var jacobian = new Matrix4x4(
            xAxis.X, xAxis.Y, xAxis.Z, 0f,
            yAxis.X, yAxis.Y, yAxis.Z, 0f,
            zAxis.X, zAxis.Y, zAxis.Z, 0f,
            0f, 0f, 0f, 1f);
        return Quaternion.CreateFromRotationMatrix(jacobian);
    }

    private static (Vector3 Edge00, Vector3 Edge10, Vector3 Edge01, Vector3 Edge11) EvaluateEdgePositions(BendCage cage, float xFrac)
    {
        var cp = cage.ControlPoints;
        var mp = cage.Midpoints;
        return (
            MathUtils.CubicBezier(cp[0], mp[0], mp[1], cp[4], xFrac),
            MathUtils.CubicBezier(cp[1], mp[2], mp[3], cp[5], xFrac),
            MathUtils.CubicBezier(cp[2], mp[4], mp[5], cp[6], xFrac),
            MathUtils.CubicBezier(cp[3], mp[6], mp[7], cp[7], xFrac));
    }

    private static (Vector3 Edge00, Vector3 Edge10, Vector3 Edge01, Vector3 Edge11) EvaluateEdgeTangents(BendCage cage, float xFrac)
    {
        var cp = cage.ControlPoints;
        var mp = cage.Midpoints;
        return (
            CubicBezierDerivative(cp[0], mp[0], mp[1], cp[4], xFrac),
            CubicBezierDerivative(cp[1], mp[2], mp[3], cp[5], xFrac),
            CubicBezierDerivative(cp[2], mp[4], mp[5], cp[6], xFrac),
            CubicBezierDerivative(cp[3], mp[6], mp[7], cp[7], xFrac));
    }

    private static Vector3 CubicBezierDerivative(Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3, float t)
    {
        var oneMinusT = 1f - t;
        return (3f * oneMinusT * oneMinusT * (p1 - p0))
            + (6f * oneMinusT * t * (p2 - p1))
            + (3f * t * t * (p3 - p2));
    }

    private static float XFraction(BendCage cage, Vector3 local) => cage.Size.X > Epsilon ? local.X / cage.Size.X : 0f;
    private static float YFraction(BendCage cage, Vector3 local) => cage.Size.Y > Epsilon ? local.Y / cage.Size.Y : 0f;
    private static float ZFraction(BendCage cage, Vector3 local) => cage.Size.Z > Epsilon ? local.Z / cage.Size.Z : 0f;

    private static Vector3 SafeNormalize(Vector3 value)
        => SafeNormalize(value, Vector3.UnitX);

    private static Vector3 SafeNormalize(Vector3 value, Vector3 fallback)
        => value.LengthSquared() > 1e-10f ? Vector3.Normalize(value) : fallback;

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
        var pivotFraction = Math.Clamp(bendPoint, 0f, 1f);
        var radius = MathF.Abs(bendRadius) > Epsilon
            ? bendRadius
            : (MathF.Abs(thetaTotal) > 1e-5f ? size.X / thetaTotal : 0f);

        return new(enabled, origin, angles, size, thetaTotal, pivotFraction * size.X, pivotFraction, radius);
    }

    private static void CollectDeformers(
        JsonNode? node,
        List<SmartPropWidgetEvaluator.PathPart> path,
        List<DeformerInfo> deformers,
        List<int> activeDeformerIndexes,
        Dictionary<int, JsonObject> modelNodes,
        bool underPlaceOnPath)
    {
        if (node is JsonObject obj)
        {
            var className = SmartPropWidgetEvaluator.ReadString(obj, "_class");
            var pushedDeformer = false;

            if (SmartPropWidgetEvaluator.ClassIs(className, "BendDeformer"))
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
            else if (SmartPropWidgetEvaluator.IsModelClass(className))
            {
                var elementId = SmartPropWidgetEvaluator.ReadInt32(obj, "m_nElementID");
                modelNodes[elementId] = obj;
                foreach (var index in activeDeformerIndexes)
                    deformers[index].DescendantModelIds.Add(elementId);
            }

            var nextUnderPlaceOnPath = underPlaceOnPath || SmartPropWidgetEvaluator.ClassIs(className, "PlaceOnPath");
            foreach (var property in obj)
            {
                path.Add(new(property.Key, null));
                CollectDeformers(property.Value, path, deformers, activeDeformerIndexes, modelNodes, nextUnderPlaceOnPath);
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
                CollectDeformers(array[index], path, deformers, activeDeformerIndexes, modelNodes, underPlaceOnPath);
                path.RemoveAt(path.Count - 1);
            }
        }
    }

    /// <summary>
    /// True when this model opts out of mesh-level deformation — Valve's own
    /// <c>Model.m_bRigidDeformation</c> flag, or an enabled <c>CSmartPropOperation_RigidDeformation</c>
    /// modifier ("Apply the active deformer to the current transform as a rigid deformation and
    /// disable the deformer") — in which case only its instance transform bends.
    /// </summary>
    private static bool IsRigidDeformation(JsonObject modelNode, SmartPropContext context)
    {
        if (SmartPropWidgetEvaluator.ResolveScalar(modelNode["m_bRigidDeformation"], context) > 0.5f)
            return true;

        if (modelNode["m_Modifiers"] is not JsonArray modifiers)
            return false;

        foreach (var modifier in modifiers)
        {
            if (modifier is not JsonObject modifierObject)
                continue;

            var className = SmartPropWidgetEvaluator.ReadString(modifierObject, "_class");
            var isRigidOperation = className.Equals("RigidDeformation", StringComparison.Ordinal)
                || className.Equals("CSmartPropOperation_RigidDeformation", StringComparison.Ordinal);
            if (isRigidOperation && SmartPropWidgetEvaluator.ResolveScalar(modifierObject["m_bEnabled"], context, 1f) > 0.5f)
                return true;
        }

        return false;
    }

    private readonly record struct BendParams(
        bool Enabled, Vector3 Origin, Vector3 Angles, Vector3 Size, float ThetaTotal, float PivotX, float PivotFraction, float Radius);

    private sealed record DeformerInfo(
        SmartPropWidgetEvaluator.PathPart[] Path,
        int ElementId,
        JsonObject Node,
        int Depth,
        bool SkipRepeated,
        HashSet<int> DescendantModelIds);
}
