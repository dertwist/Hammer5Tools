using System.Numerics;
using System.Text.Json.Nodes;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Expands models placed under a <c>CSmartPropElement_PlaceInSphere</c> into a scattered set.
/// </summary>
/// <remarks>
/// None of this element's fields (<c>m_nCountMin</c>/<c>m_nCountMax</c>/
/// <c>m_flPositionRadiusInner</c>/<c>m_flPositionRadiusOuter</c>/...) appear anywhere in VRF's
/// evaluator — it emits one pass-through instance regardless of count. This runs as a correction
/// pass, cloning that instance into a scattered set within the radius shell.
///
/// Deterministic per-element PRNG (seeded from <c>m_nElementID</c>) so the same document always
/// previews the same scatter. Instance count is fixed at <c>m_nCountMax</c> (falling back to
/// <c>m_nCountMin</c>) rather than genuinely randomized within [min, max] — a stable editor
/// preview matters more here than reproducing play-time count variance.
/// <c>m_flRandomness</c>, <c>m_PlacementMode</c> (non-"SPHERE"), <c>m_DistributionMode</c>
/// (non-"RANDOM"), and orientation alignment (<c>m_bAlignOrientation</c> / <c>m_vAlignDirection</c> /
/// <c>m_vPlaneUpDirection</c>) aren't implemented — every instance keeps its parent orientation.
/// </remarks>
internal static class SmartPropPlaceInSphereEvaluator
{
    private const string ProbeModel = "__hammer5tools_sphere_probe__.vmdl";
    private const long IdStride = 1_000_000;

    public static IReadOnlyList<EvaluatedSmartPropModel> ApplyPlaceInSphere(
        string json,
        string? nestedDocumentsJson,
        IReadOnlyList<EvaluatedSmartPropModel> models,
        SmartPropEvaluationOptions options)
    {
        if (JsonNode.Parse(json) is not JsonObject root)
            return models;

        var spheres = SmartPropWidgetEvaluator.CollectElementsWithDescendants(root, "PlaceInSphere");
        if (spheres.Count == 0)
            return models;

        var nestedDocuments = nestedDocumentsJson is null ? null : JsonNode.Parse(nestedDocumentsJson) as JsonObject;
        var context = SmartPropWidgetEvaluator.CreateContext(root);
        var corrected = models.ToList();

        foreach (var sphere in spheres.OrderByDescending(sphere => sphere.Depth))
        {
            options.CancellationToken.ThrowIfCancellationRequested();

            if (sphere.DescendantModelIds.Count == 0)
                continue;

            var elementId = SmartPropWidgetEvaluator.ReadInt32(sphere.Node, "m_nElementID");
            var scatter = ResolveScatter(sphere.Node, context, elementId);
            if (scatter.Count <= 1)
                continue;

            var frame = SmartPropWidgetEvaluator.ProbeElementFrame(root, nestedDocuments, sphere.Path, options, ProbeModel);
            if (frame is not { } elementFrame || !Matrix4x4.Invert(elementFrame, out var invFrame))
                continue;

            var baseModels = corrected.Where(model => sphere.DescendantModelIds.Contains(model.ElementId)).ToArray();
            corrected.RemoveAll(model => sphere.DescendantModelIds.Contains(model.ElementId));

            var random = new SmartPropContext(randomSeed: elementId);
            for (var instance = 0; instance < scatter.Count; instance++)
            {
                var offset = RandomPointInShell(random, scatter.RadiusInner, scatter.RadiusOuter);
                var offsetMatrix = Matrix4x4.CreateTranslation(offset);

                foreach (var baseModel in baseModels)
                {
                    var newTransform = baseModel.Transform * invFrame * offsetMatrix * elementFrame;
                    var newId = instance == 0 ? baseModel.ElementId : baseModel.ElementId + (instance * IdStride);
                    corrected.Add(baseModel with { ElementId = (int)newId, Transform = newTransform });
                }
            }
        }

        return corrected;
    }

    /// <summary>Uniform random point in the spherical shell between the inner and outer radii.</summary>
    private static Vector3 RandomPointInShell(SmartPropContext random, float radiusInner, float radiusOuter)
    {
        var z = random.NextFloat(-1f, 1f);
        var planarRadius = MathF.Sqrt(MathF.Max(0f, 1f - (z * z)));
        var azimuth = random.NextFloat(0f, MathF.Tau);
        var direction = new Vector3(planarRadius * MathF.Cos(azimuth), planarRadius * MathF.Sin(azimuth), z);

        // Cube root keeps the distribution volumetrically uniform rather than biased toward the center.
        var unit = random.NextFloat(0f, 1f);
        var radius = radiusInner + ((radiusOuter - radiusInner) * MathF.Cbrt(unit));
        return direction * radius;
    }

    private static ScatterParams ResolveScatter(JsonObject node, SmartPropContext context, int elementId)
    {
        var countMax = (int)SmartPropWidgetEvaluator.ResolveScalar(node["m_nCountMax"], context, 1f);
        var countMin = (int)SmartPropWidgetEvaluator.ResolveScalar(node["m_nCountMin"], context, 1f);
        var count = Math.Max(1, countMax > 0 ? countMax : countMin);
        // ponytail: caps scatter count; upgrade to a per-pass MaximumModels-aware budget if this shows up.
        count = Math.Min(count, 4096);

        var inner = SmartPropWidgetEvaluator.ResolveScalar(node["m_flPositionRadiusInner"], context);
        var outer = SmartPropWidgetEvaluator.ResolveScalar(node["m_flPositionRadiusOuter"], context);
        if (outer < inner)
            (inner, outer) = (outer, inner);

        return new(count, inner, outer);
    }

    private readonly record struct ScatterParams(int Count, float RadiusInner, float RadiusOuter);
}
