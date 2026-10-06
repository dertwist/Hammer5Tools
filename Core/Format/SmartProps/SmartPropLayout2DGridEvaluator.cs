using System.Numerics;
using System.Text.Json.Nodes;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Expands models placed under a <c>CSmartPropElement_Layout2DGrid</c> into a full grid.
/// </summary>
/// <remarks>
/// None of this element's fields (<c>m_nCountW</c>/<c>m_nCountL</c>/<c>m_flSpacingWidth</c>/
/// <c>m_flSpacingLength</c>/<c>m_GridOriginMode</c>/<c>m_bAlternateShift</c>/...) appear anywhere in
/// VRF's evaluator — it treats a grid exactly like a plain group and emits one pass-through
/// instance. This runs as a correction pass, cloning that one instance into the full W×L grid.
///
/// Width is treated as the element's local X axis and Length as local Y — the same axis
/// convention <see cref="SmartPropBendDeformerEvaluator"/> uses for its size box. <c>m_flWidth</c>/
/// <c>m_flLength</c>/<c>m_bVerticalLength</c>/<c>m_GridArrangement</c> aren't read: the explicit
/// per-axis spacing fields already fully determine cell placement, and "SEGMENT" vs. other
/// arrangement modes aren't documented well enough to guess at safely — every grid comes out as a
/// plain rectangular lattice regardless of that field's value.
/// </remarks>
internal static class SmartPropLayout2DGridEvaluator
{
    private const string ProbeModel = "__hammer5tools_grid_probe__.vmdl";

    public static IReadOnlyList<EvaluatedSmartPropModel> ApplyGrids(
        string json,
        string? nestedDocumentsJson,
        IReadOnlyList<EvaluatedSmartPropModel> models,
        SmartPropEvaluationOptions options)
    {
        if (JsonNode.Parse(json) is not JsonObject root)
            return models;

        var grids = SmartPropWidgetEvaluator.CollectElementsWithDescendants(root, "Layout2DGrid");
        if (grids.Count == 0)
            return models;

        var nestedDocuments = nestedDocumentsJson is null ? null : JsonNode.Parse(nestedDocumentsJson) as JsonObject;
        var context = SmartPropWidgetEvaluator.CreateContext(root);
        var corrected = models.ToList();

        foreach (var grid in grids.OrderByDescending(grid => grid.Depth))
        {
            options.CancellationToken.ThrowIfCancellationRequested();

            if (grid.DescendantModelIds.Count == 0)
                continue;

            var layout = ResolveLayout(grid.Node, context);
            var total = layout.CountW * layout.CountL;
            if (total <= 1)
                continue;

            var frame = SmartPropWidgetEvaluator.ProbeElementFrame(root, nestedDocuments, grid.Path, options, ProbeModel);
            if (frame is not { } elementFrame || !Matrix4x4.Invert(elementFrame, out var invFrame))
                continue;

            var baseModels = corrected.Where(model => grid.DescendantModelIds.Contains(model.ElementId)).ToArray();
            corrected.RemoveAll(model => grid.DescendantModelIds.Contains(model.ElementId));

            var centerW = layout.CenterOrigin ? (layout.CountW - 1) / 2f : 0f;
            var centerL = layout.CenterOrigin ? (layout.CountL - 1) / 2f : 0f;

            for (var w = 0; w < layout.CountW; w++)
            {
                for (var l = 0; l < layout.CountL; l++)
                {
                    var cellIndex = (w * layout.CountL) + l;
                    var alternateShift = layout.AlternateShift && (l % 2 == 1) ? layout.AlternateShiftWidth : 0f;
                    var offset = new Vector3(
                        (layout.SpacingWidth * (w - centerW)) + alternateShift,
                        layout.SpacingLength * (l - centerL),
                        0f);
                    var offsetMatrix = Matrix4x4.CreateTranslation(offset);

                    foreach (var baseModel in baseModels)
                    {
                        var newTransform = baseModel.Transform * invFrame * offsetMatrix * elementFrame;
                        var newId = cellIndex == 0 ? baseModel.ElementId : baseModel.ElementId + (cellIndex * SmartPropWidgetEvaluator.ElementIdStride);
                        corrected.Add(baseModel with { ElementId = (int)newId, Transform = newTransform });
                    }
                }
            }
        }

        return corrected;
    }

    private static GridLayout ResolveLayout(JsonObject node, SmartPropContext context)
    {
        var countW = Math.Max(1, (int)SmartPropWidgetEvaluator.ResolveScalar(node["m_nCountW"], context, 1f));
        var countL = Math.Max(1, (int)SmartPropWidgetEvaluator.ResolveScalar(node["m_nCountL"], context, 1f));
        var spacingW = SmartPropWidgetEvaluator.ResolveScalar(node["m_flSpacingWidth"], context, 128f);
        var spacingL = SmartPropWidgetEvaluator.ResolveScalar(node["m_flSpacingLength"], context, 128f);
        var originMode = SmartPropWidgetEvaluator.ReadString(node, "m_GridOriginMode", "CENTER");
        var alternateShift = SmartPropWidgetEvaluator.ResolveScalar(node["m_bAlternateShift"], context) > 0.5f;
        var alternateShiftWidth = SmartPropWidgetEvaluator.ResolveScalar(node["m_flAlternateShiftWidth"], context);

        // Bound each grid dimension to limit generated model count.
        countW = Math.Min(countW, 256);
        countL = Math.Min(countL, 256);

        return new(countW, countL, spacingW, spacingL, originMode.Equals("CENTER", StringComparison.OrdinalIgnoreCase), alternateShift, alternateShiftWidth);
    }

    private readonly record struct GridLayout(
        int CountW, int CountL, float SpacingWidth, float SpacingLength, bool CenterOrigin, bool AlternateShift, float AlternateShiftWidth);
}
