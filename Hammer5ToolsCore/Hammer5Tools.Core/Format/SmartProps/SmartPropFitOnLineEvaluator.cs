using System.Numerics;
using System.Text.Json.Nodes;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Expands models placed under a <c>CSmartPropElement_FitOnLine</c> into the repeated,
/// scaled-to-fit sequence VRF's evaluator doesn't build.
/// </summary>
/// <remarks>
/// VRF resolves <c>LinearScale()</c> and places exactly one instance, its scale clamped to the
/// child's <c>CSmartPropSelectionCriteria_LinearLength</c> min/max — but it never repeats that
/// piece to actually cover the line, and <c>m_nScaleMode</c> is never read at all (every mode
/// produces the same single clamped instance). This runs as a correction pass: it re-derives how
/// many copies belong on the line and how much each is scaled, per <c>m_nScaleMode</c>, then
/// re-evaluates each copy's own scale expression independently of VRF (via this project's own
/// <see cref="SmartPropExpression"/>/<see cref="SmartPropContext"/> — VRF's LinearScale() context is
/// internal to its single-instance evaluation and isn't reachable per-copy) and places it along
/// the line, starting at <c>m_vStart</c> and stacking piece-by-piece toward <c>m_vEnd</c>.
///
/// Scale-mode semantics aren't documented anywhere reachable from here, so they're inferred from
/// the field's own description ("how scale is applied ... to fit them to the line") and the
/// standard tiling interpretation: <c>NONE</c> repeats pieces at their authored length and leaves
/// any remainder as a gap; <c>SCALE_END_TO_FIT</c> repeats at authored length and stretches only
/// the last piece to close the exact remainder; <c>SCALE_EQUALLY</c> picks the piece count whose
/// even split lands closest to the authored (unscaled) length; <c>SCALE_MAXIMIZE</c> picks the
/// fewest pieces possible (each stretched toward its criteria's maximum). A piece whose criteria
/// disallows scaling (<c>m_bAllowScale = false</c>) always behaves like <c>NONE</c>.
///
/// Only the common single-slot authoring shape is handled — one wrapper (Group/PickOne) with a
/// single LinearLength criteria beneath a FitOnLine, matching every shipped preset. A PickOne
/// choosing between differently-sized sibling pieces per repeat isn't attempted: VRF's own single
/// selection is trusted and simply repeated at its own criteria.
/// </remarks>
internal static class SmartPropFitOnLineEvaluator
{
    private const string ProbeModel = "__hammer5tools_fitonline_probe__.vmdl";
    private const long IdStride = 1_000_000;
    // Bounds generated model count for a single FitOnLine widget.
    private const int MaxPieces = 256;

    public static IReadOnlyList<EvaluatedSmartPropModel> ApplyFitOnLine(
        string json,
        string? nestedDocumentsJson,
        IReadOnlyList<EvaluatedSmartPropModel> models,
        SmartPropEvaluationOptions options)
    {
        if (JsonNode.Parse(json) is not JsonObject root)
            return models;

        var context = SmartPropWidgetEvaluator.CreateContext(root);
        var lines = new List<FitOnLineInfo>();
        var modelNodes = new Dictionary<int, JsonObject>();
        CollectFitOnLines(root, [], lines, [], modelNodes, context, underPlaceOnPath: false);
        if (lines.Count == 0)
            return models;

        var nestedDocuments = nestedDocumentsJson is null ? null : JsonNode.Parse(nestedDocumentsJson) as JsonObject;
        var corrected = models.ToList();

        foreach (var line in lines.OrderByDescending(line => line.Depth))
        {
            options.CancellationToken.ThrowIfCancellationRequested();

            if (line.DescendantModelIds.Count == 0 || line.Criteria is not { Length: > 1e-4f } criteria)
                continue;

            var start = SmartPropWidgetEvaluator.ResolveVector(line.Node["m_vStart"], context);
            var end = SmartPropWidgetEvaluator.ResolveVector(line.Node["m_vEnd"], context);
            var totalLength = Vector3.Distance(start, end);
            if (totalLength <= 1e-4f)
                continue;
            var direction = (end - start) / totalLength;

            var scaleMode = SmartPropWidgetEvaluator.ReadString(line.Node, "m_nScaleMode", "NONE");
            var pieceScales = BuildPieceScales(totalLength, criteria, scaleMode);
            if (pieceScales.Count == 0)
                continue;

            var frame = SmartPropWidgetEvaluator.ProbeElementFrame(root, nestedDocuments, line.Path, options, ProbeModel);
            if (frame is not { } elementFrame || !Matrix4x4.Invert(elementFrame, out var invFrame))
                continue;

            var baseModels = corrected.Where(model => line.DescendantModelIds.Contains(model.ElementId)).ToArray();
            corrected.RemoveAll(model => line.DescendantModelIds.Contains(model.ElementId));

            var cumulative = 0f;
            for (var pieceIndex = 0; pieceIndex < pieceScales.Count; pieceIndex++)
            {
                var scale = pieceScales[pieceIndex];
                var pieceOffset = direction * cumulative;
                cumulative += criteria.Length * scale;

                foreach (var baseModel in baseModels)
                {
                    if (!modelNodes.TryGetValue(baseModel.ElementId, out var modelNode))
                        continue;
                    if (!Matrix4x4.Decompose(baseModel.Transform * invFrame, out _, out var localRotation, out var localTranslation))
                        continue;

                    var pieceContext = SmartPropWidgetEvaluator.CreateContext(root, scale);
                    var newLocal =
                        Matrix4x4.CreateScale(ResolveModelScale(modelNode, pieceContext))
                        * Matrix4x4.CreateFromQuaternion(localRotation)
                        * Matrix4x4.CreateTranslation(localTranslation + pieceOffset);

                    var newId = pieceIndex == 0 ? baseModel.ElementId : baseModel.ElementId + (pieceIndex * IdStride);
                    corrected.Add(baseModel with { ElementId = (int)newId, Transform = newLocal * elementFrame });
                }
            }
        }

        return corrected;
    }

    /// <summary>Per-piece scale factors (multiples of the criteria's authored length) covering the line.</summary>
    private static List<float> BuildPieceScales(float totalLength, LinearLengthCriteria criteria, string scaleMode)
    {
        var authored = criteria.Length;

        if (!criteria.AllowScale || scaleMode.Equals("NONE", StringComparison.OrdinalIgnoreCase))
        {
            var naturalCount = Math.Clamp((int)MathF.Floor((totalLength / authored) + 1e-4f), 1, MaxPieces);
            return [.. Enumerable.Repeat(1f, naturalCount)];
        }

        var minScale = criteria.MinLength > 1e-4f ? criteria.MinLength / authored : 0.1f;
        var maxScale = criteria.MaxLength > 1e-4f ? criteria.MaxLength / authored : totalLength / authored;
        if (minScale > maxScale)
            (minScale, maxScale) = (maxScale, minScale);

        var idealCount = totalLength / authored;
        var minCount = Math.Max(1, (int)MathF.Ceiling((totalLength / (authored * maxScale)) - 1e-4f));
        var maxCount = Math.Clamp((int)MathF.Floor((totalLength / (authored * minScale)) + 1e-4f), minCount, MaxPieces);

        if (scaleMode.Equals("SCALE_END_TO_FIT", StringComparison.OrdinalIgnoreCase))
        {
            var count = Math.Clamp((int)MathF.Round(idealCount), minCount, maxCount);
            if (count <= 1)
                return [Math.Clamp(idealCount, minScale, maxScale)];

            var pieces = new List<float>(Enumerable.Repeat(1f, count - 1));
            var remainder = totalLength - ((count - 1) * authored);
            pieces.Add(Math.Clamp(remainder / authored, minScale, maxScale));
            return pieces;
        }

        var chosenCount = scaleMode.Equals("SCALE_MAXIMIZE", StringComparison.OrdinalIgnoreCase)
            ? minCount
            : ClosestToIdeal(minCount, maxCount, idealCount); // SCALE_EQUALLY, and the default fallback.

        var uniformScale = Math.Clamp(totalLength / (chosenCount * authored), minScale, maxScale);
        return [.. Enumerable.Repeat(uniformScale, chosenCount)];
    }

    private static int ClosestToIdeal(int minCount, int maxCount, float idealCount)
    {
        var best = minCount;
        var bestDelta = float.MaxValue;
        for (var count = minCount; count <= maxCount; count++)
        {
            var delta = MathF.Abs(count - idealCount);
            if (delta < bestDelta)
            {
                bestDelta = delta;
                best = count;
            }
        }
        return best;
    }

    private static Vector3 ResolveModelScale(JsonObject modelNode, SmartPropContext context)
    {
        if (modelNode["m_vModelScale"] is { } vector)
            return SmartPropWidgetEvaluator.ResolveVector(vector, context, Vector3.One);
        if (modelNode["m_flUniformModelScale"] is { } uniform)
            return new(SmartPropWidgetEvaluator.ResolveScalar(uniform, context, 1f));
        if (modelNode["m_flModelScale"] is { } scale)
            return new(SmartPropWidgetEvaluator.ResolveScalar(scale, context, 1f));
        return Vector3.One;
    }

    private static void CollectFitOnLines(
        JsonNode? node,
        List<SmartPropWidgetEvaluator.PathPart> path,
        List<FitOnLineInfo> lines,
        List<int> activeLineIndexes,
        Dictionary<int, JsonObject> modelNodes,
        SmartPropContext context,
        bool underPlaceOnPath)
    {
        if (node is JsonObject obj)
        {
            var className = SmartPropWidgetEvaluator.ReadString(obj, "_class");
            var pushed = false;

            if (SmartPropWidgetEvaluator.ClassIs(className, "FitOnLine") && !underPlaceOnPath)
            {
                lines.Add(new(path.ToArray(), obj, activeLineIndexes.Count, null, []));
                activeLineIndexes.Add(lines.Count - 1);
                pushed = true;
            }
            else if (SmartPropWidgetEvaluator.IsModelClass(className))
            {
                var elementId = SmartPropWidgetEvaluator.ReadInt32(obj, "m_nElementID");
                modelNodes[elementId] = obj;
                foreach (var index in activeLineIndexes)
                    lines[index].DescendantModelIds.Add(elementId);
            }
            else if (activeLineIndexes.Count > 0 && className.Equals("CSmartPropSelectionCriteria_LinearLength", StringComparison.Ordinal))
            {
                var innermost = activeLineIndexes[^1];
                if (lines[innermost].Criteria is null)
                    lines[innermost] = lines[innermost] with { Criteria = ReadCriteria(obj, context) };
            }

            var nextUnderPlaceOnPath = underPlaceOnPath || SmartPropWidgetEvaluator.ClassIs(className, "PlaceOnPath");
            foreach (var property in obj)
            {
                path.Add(new(property.Key, null));
                CollectFitOnLines(property.Value, path, lines, activeLineIndexes, modelNodes, context, nextUnderPlaceOnPath);
                path.RemoveAt(path.Count - 1);
            }

            if (pushed)
                activeLineIndexes.RemoveAt(activeLineIndexes.Count - 1);
        }
        else if (node is JsonArray array)
        {
            for (var index = 0; index < array.Count; index++)
            {
                path.Add(new(null, index));
                CollectFitOnLines(array[index], path, lines, activeLineIndexes, modelNodes, context, underPlaceOnPath);
                path.RemoveAt(path.Count - 1);
            }
        }
    }

    private static LinearLengthCriteria ReadCriteria(JsonObject node, SmartPropContext context) => new(
        SmartPropWidgetEvaluator.ResolveScalar(node["m_flLength"], context),
        SmartPropWidgetEvaluator.ResolveScalar(node["m_flMinLength"], context),
        SmartPropWidgetEvaluator.ResolveScalar(node["m_flMaxLength"], context),
        SmartPropWidgetEvaluator.ResolveScalar(node["m_bAllowScale"], context, 1f) > 0.5f);

    private readonly record struct LinearLengthCriteria(float Length, float MinLength, float MaxLength, bool AllowScale);

    private sealed record FitOnLineInfo(
        SmartPropWidgetEvaluator.PathPart[] Path, JsonObject Node, int Depth, LinearLengthCriteria? Criteria, HashSet<int> DescendantModelIds);
}
