using System.Text.Json.Nodes;

using ValveResourceFormat.ResourceTypes.SmartProps;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Expands models placed under a <c>CSmartPropElement_PlaceMultiple</c> into <c>m_nCount</c> copies.
/// </summary>
/// <remarks>
/// VRF's evaluator emits exactly one pass-through instance regardless of <c>m_nCount</c>/
/// <c>m_Expression</c>. Unlike the other multiplicity elements, PlaceMultiple has no spatial fields
/// of its own at all — real documents separate instances visually through ordinary child modifiers
/// (<c>RandomOffset</c>/<c>RandomRotation</c>/...), which VRF salts by element id. So instead of
/// inventing placement math, each extra instance is produced by cloning the whole document, shifting
/// every <c>m_nElementID</c> under this element's subtree by a per-instance stride, and letting VRF's
/// real evaluator run again — the same clone-and-reevaluate technique
/// <see cref="SmartPropWidgetEvaluator.ProbeElementFrame"/> uses, just without pinning a single
/// probe model. That gives child randomization modifiers a different salt per instance, so they
/// actually scatter, while everything else about the subtree evaluates exactly as VRF intends.
///
/// ponytail: each instance re-evaluates the *original* document, so PlaceMultiple nested inside a
/// Grid/Sphere/another PlaceMultiple only multiplies at its own level — the combinations don't
/// compose. Upgrade path: re-run the correction passes against each generated clone if that nesting
/// shows up in practice.
/// </remarks>
internal static class SmartPropPlaceMultipleEvaluator
{
    private const long IdStride = 1_000_000;

    public static IReadOnlyList<EvaluatedSmartPropModel> ApplyPlaceMultiple(
        string json,
        string? nestedDocumentsJson,
        IReadOnlyList<EvaluatedSmartPropModel> models,
        SmartPropEvaluationOptions options)
    {
        if (JsonNode.Parse(json) is not JsonObject root)
            return models;

        var elements = SmartPropWidgetEvaluator.CollectElementsWithDescendants(root, "PlaceMultiple");
        if (elements.Count == 0)
            return models;

        var nestedDocuments = nestedDocumentsJson is null ? null : JsonNode.Parse(nestedDocumentsJson) as JsonObject;
        var resolver = nestedDocuments is null ? null : SmartPropWidgetEvaluator.CreateNestedResolver(nestedDocuments);
        var context = SmartPropWidgetEvaluator.CreateContext(root);
        var corrected = models.ToList();

        foreach (var element in elements.OrderByDescending(element => element.Depth))
        {
            options.CancellationToken.ThrowIfCancellationRequested();

            if (element.DescendantModelIds.Count == 0)
                continue;

            var count = ResolveCount(element.Node, context);
            if (count <= 1)
                continue;

            for (var instance = 1; instance < count; instance++)
            {
                options.CancellationToken.ThrowIfCancellationRequested();

                if (root.DeepClone() is not JsonObject clone)
                    continue;
                if (SmartPropWidgetEvaluator.FindObject(clone, element.Path) is not { } cloneElement)
                    continue;

                var delta = instance * IdStride;
                BumpElementIds(cloneElement, delta);

                var evaluated = SmartPropEvaluation.Evaluate(
                    SmartPropJsonConverter.Convert(clone.ToJsonString()),
                    resolver,
                    options.MaximumDepth);

                foreach (var placement in evaluated.Models)
                {
                    if (!element.DescendantModelIds.Contains((int)(placement.ElementId - delta)))
                        continue;

                    corrected.Add(new EvaluatedSmartPropModel(
                        placement.ElementId, placement.ModelName, placement.Transform, placement.MaterialGroup, placement.TintColor));
                }
            }
        }

        return corrected;
    }

    private static int ResolveCount(JsonObject node, SmartPropContext context)
    {
        var count = node["m_nCount"] is { } countNode
            ? (int)SmartPropWidgetEvaluator.ResolveScalar(countNode, context)
            : 0;
        if (count <= 0)
            count = (int)MathF.Round(SmartPropExpression.Evaluate(
                SmartPropWidgetEvaluator.ReadString(node, "m_Expression"), context, 1f));

        // ponytail: caps generated instance count; upgrade to a per-pass MaximumModels-aware budget if this shows up.
        return Math.Clamp(count, 1, 4096);
    }

    private static void BumpElementIds(JsonObject node, long delta)
    {
        if (node["m_nElementID"] is JsonValue value && value.TryGetValue<int>(out var id))
            node["m_nElementID"] = (int)(id + delta);

        foreach (var property in node)
        {
            if (property.Value is JsonObject child)
                BumpElementIds(child, delta);
            else if (property.Value is JsonArray array)
            {
                foreach (var item in array)
                {
                    if (item is JsonObject itemObject)
                        BumpElementIds(itemObject, delta);
                }
            }
        }
    }
}
