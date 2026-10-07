using ValveKeyValue;

namespace Hammer5Tools.Core.Format.SmartProps.Evaluation;

internal sealed record SmartPropEvaluationResult(
    IReadOnlyList<EvaluatedSmartPropModel> Models,
    IReadOnlyList<EvaluatedSmartPropWidget> Widgets);

internal static class SmartPropEvaluator
{
    public const int DefaultMaxDepth = 32;
    public const int DefaultMaxModels = 100_000;
    private const int MaxPathInstances = 4096;

    private static readonly Vector3[] DefaultPathPoints =
    [
        new(-400f, 0f, 0f),
        new(-200f, 32f, 0f),
        new(200f, -32f, 0f),
        new(400f, 0f, 0f),
    ];

    public static SmartPropEvaluationResult Evaluate(
        KVObject root,
        SmartPropEvaluationContext? context = null,
        Func<string, KVObject?>? nestedPropResolver = null,
        int maxDepth = DefaultMaxDepth,
        int maxModels = DefaultMaxModels,
        CancellationToken cancellationToken = default)
    {
        context ??= CreateContext(root);
        var output = new EvaluationOutput(maxModels, cancellationToken);
        Traverse(root, Matrix4x4.Identity, context, output, null, null, nestedPropResolver, [], 0, maxDepth);
        return new SmartPropEvaluationResult(output.Models, output.Widgets);
    }

    private static SmartPropEvaluationContext CreateContext(KVObject root)
    {
        var variables = SmartPropVariableMap.ReadDefaults(root);
        SmartPropChoiceMap.ApplyChoices(variables, SmartPropChoiceMap.ReadChoices(root));
        return new SmartPropEvaluationContext(variables);
    }

    private static void Traverse(
        KVObject element,
        Matrix4x4 parentTransform,
        SmartPropEvaluationContext context,
        EvaluationOutput output,
        Vector4? inheritedTint,
        string? inheritedMaterialGroup,
        Func<string, KVObject?>? nestedPropResolver,
        HashSet<string> activeNestedProps,
        int depth,
        int maxDepth)
    {
        output.CancellationToken.ThrowIfCancellationRequested();
        if (++output.Visits > output.MaximumVisits)
        {
            throw new InvalidDataException("SmartProp traversal exceeded its evaluation budget.");
        }

        if (output.Models.Count > output.MaximumModels
            || element.ValueType != KVValueType.Collection
            || IsDisabled(element))
        {
            return;
        }

        var modifierResult = SmartPropModifierEvaluator.Evaluate(
            element,
            context,
            parentTransform,
            inheritedTint,
            inheritedMaterialGroup,
            output.Widgets);
        if (modifierResult.IsFilteredOut)
        {
            return;
        }

        var className = SmartPropClass.Read(element);
        var deformer = className switch
        {
            "BendDeformer" => SmartPropBendDeformerEvaluator.Create(element, modifierResult.WorldTransform, context),
            "MidpointDeformer" => SmartPropMidpointDeformerEvaluator.Create(element, modifierResult.WorldTransform, context),
            _ => null,
        };
        if (deformer is not null)
        {
            output.Deformers.Add(deformer);
        }
        var inheritedMaterials = output.Materials;
        output.Materials = SmartPropMaterialEvaluator.Fold(inheritedMaterials, element, context);
        try
        {
            if (IsModel(className))
            {
                var modelName = context.ResolveString(ReadValue(element, "m_sModelName"));
                if (!string.IsNullOrEmpty(modelName))
                {
                    var model = new EvaluatedSmartPropModel(
                        ReadInt32(element, "m_nElementID"),
                        modelName,
                        modifierResult.ModelTransform,
                        ResolveMaterialGroup(element, context) ?? modifierResult.MaterialGroup,
                        modifierResult.TintColor);
                    for (var index = output.Deformers.Count - 1; index >= 0; index--)
                    {
                        model = output.Deformers[index](model, element, context);
                    }
                    output.Models.Add(output.Materials.ApplyTo(model));
                }
            }

            if (!string.IsNullOrEmpty(className) && className != "CSmartPropRoot" && !IsModel(className))
            {
                output.Widgets.Add(CreateWidget(element, className == "Group" ? "group" : "element",
                    ReadInt32(element, "m_nElementID"), modifierResult.WorldTransform, context));
                if (className == "PickOne")
                {
                    output.Widgets.Add(CreateWidget(element, "pickone", ReadInt32(element, "m_nElementID"),
                        modifierResult.WorldTransform, context));
                }
            }

            if (className == "SmartProp")
            {
                TraverseNested(
                    element,
                    modifierResult.WorldTransform,
                    context,
                    output,
                    modifierResult.TintColor,
                    modifierResult.MaterialGroup,
                    nestedPropResolver,
                    activeNestedProps,
                    depth,
                    maxDepth);
                return;
            }

            if (className == "PlaceOnPath")
            {
                TraversePath(element, modifierResult.WorldTransform, context, output, modifierResult.TintColor,
                    modifierResult.MaterialGroup, nestedPropResolver, activeNestedProps, depth, maxDepth);
                return;
            }

            if (!element.TryGetValue("m_Children", out var children) || !children.IsArray)
            {
                return;
            }

            if (className is "PlaceMultiple" or "PlaceInSphere" or "Layout2DGrid" or "FitOnLine")
            {
                TraversePlacements(element, className, modifierResult.WorldTransform, context, output,
                    modifierResult.TintColor, modifierResult.MaterialGroup, nestedPropResolver, activeNestedProps, depth, maxDepth);
                return;
            }

            var childValues = children.AsArraySpan();
            if (className == "PickOne")
            {
                var selectedIndex = SelectPickOneChild(element, childValues, context);
                if (selectedIndex >= 0)
                {
                    TraverseChild(childValues[selectedIndex]);
                }

                return;
            }

            foreach (var child in childValues)
            {
                TraverseChild(child);
            }

            void TraverseChild(KVObject child)
            {
                if (!SmartPropSelectionCriteria.MatchesSelectionCriteria(child, context.InstanceIndex, context.InstanceCount, context))
                {
                    return;
                }

                Traverse(child, modifierResult.WorldTransform, context, output, modifierResult.TintColor,
                    modifierResult.MaterialGroup, nestedPropResolver, activeNestedProps, depth, maxDepth);
            }
        }
        finally
        {
            output.Materials = inheritedMaterials;
            if (deformer is not null)
            {
                output.Deformers.RemoveAt(output.Deformers.Count - 1);
            }
        }
    }

    private sealed class EvaluationOutput(int maximumModels, CancellationToken cancellationToken)
    {
        public List<EvaluatedSmartPropModel> Models { get; } = [];
        public List<EvaluatedSmartPropWidget> Widgets { get; } = [];
        public List<Func<EvaluatedSmartPropModel, KVObject, SmartPropEvaluationContext, EvaluatedSmartPropModel>> Deformers { get; } = [];
        public int MaximumModels { get; } = maximumModels;
        public CancellationToken CancellationToken { get; } = cancellationToken;
        public long MaximumVisits { get; } = Math.Max(100_000L, (long)maximumModels * 32);
        public long Visits;
        public SmartPropMaterialEvaluator.MaterialState Materials = SmartPropMaterialEvaluator.MaterialState.Empty;
    }

    private static void TraversePlacements(
        KVObject element,
        string className,
        Matrix4x4 parentTransform,
        SmartPropEvaluationContext context,
        EvaluationOutput output,
        Vector4? inheritedTint,
        string? inheritedMaterialGroup,
        Func<string, KVObject?>? nestedPropResolver,
        HashSet<string> activeNestedProps,
        int depth,
        int maxDepth)
    {
        var children = element["m_Children"].AsArraySpan();
        var count = 1;
        var width = 1;
        var length = 1;
        var start = context.ResolveVector3(ReadValue(element, "m_vStart"));
        var end = context.ResolveVector3(ReadValue(element, "m_vEnd"));
        var lineLength = Vector3.Distance(start, end);
        var direction = lineLength > 1e-4f ? (end - start) / lineLength : Vector3.Zero;
        float[] scales = [1f];
        SmartPropLinearLength criteria = default;
        if (className == "PlaceMultiple")
        {
            var resolved = context.ResolveScalar(ReadValue(element, "m_nCount"));
            if (resolved <= 0)
            {
                resolved = context.ResolveScalar(ReadValue(element, "m_Expression"), 1f);
            }
            count = Math.Clamp((int)resolved, 1, MaxPathInstances);
        }
        else if (className == "PlaceInSphere")
        {
            var maximum = context.ResolveScalar(ReadValue(element, "m_nCountMax"));
            var minimum = context.ResolveScalar(ReadValue(element, "m_nCountMin"), 1f);
            count = Math.Clamp((int)(maximum > 0f ? maximum : minimum), 1, MaxPathInstances);
        }
        else if (className == "Layout2DGrid")
        {
            width = Math.Clamp((int)context.ResolveScalar(ReadValue(element, "m_nCountW"), 1f), 1, 256);
            length = Math.Clamp((int)context.ResolveScalar(ReadValue(element, "m_nCountL"), 1f), 1, 256);
            count = width * length;
        }
        else if (lineLength > 1e-4f && TryFindLinearLength(element, context, out criteria) && criteria.Length > 1e-4f)
        {
            scales = BuildPieceScales(lineLength, criteria,
                context.ResolveString(ReadValue(element, "m_nScaleMode"), "SINGLE"));
            count = scales.Length;
        }

        var cumulative = 0f;
        for (var index = 0; index < count && output.Models.Count <= output.MaximumModels; index++)
        {
            output.CancellationToken.ThrowIfCancellationRequested();
            var instanceContext = context.WithPlacement(new SmartPropPlacement(index, count,
                className == "FitOnLine" ? scales[index] : context.LinearScale));
            var offset = Vector3.Zero;
            if (className == "Layout2DGrid")
            {
                var centered = context.ResolveString(ReadValue(element, "m_GridOriginMode"), "CENTER") == "CENTER";
                var row = index % length;
                var shift = ReadBoolean(element, "m_bAlternateShift") && row % 2 == 1
                    ? context.ResolveScalar(ReadValue(element, "m_flAlternateShiftWidth")) : 0f;
                offset = new Vector3(
                    context.ResolveScalar(ReadValue(element, "m_flSpacingWidth"), 128f) * (index / length - (centered ? (width - 1) / 2f : 0f)) + shift,
                    context.ResolveScalar(ReadValue(element, "m_flSpacingLength"), 128f) * (row - (centered ? (length - 1) / 2f : 0f)), 0f);
            }
            else if (className == "PlaceInSphere")
            {
                var inner = MathF.Max(0f, context.ResolveScalar(ReadValue(element, "m_flPositionRadiusInner")));
                var outer = MathF.Max(0f, context.ResolveScalar(ReadValue(element, "m_flPositionRadiusOuter")));
                if (inner > outer)
                {
                    (inner, outer) = (outer, inner);
                }
                var salt = ReadInt32(element, "m_nElementID");
                var z = instanceContext.RandomFloat(salt ^ 401) * 2f - 1f;
                var azimuth = instanceContext.RandomFloat(salt ^ 402) * MathF.Tau;
                var planar = MathF.Sqrt(MathF.Max(0f, 1f - z * z));
                var radius = MathF.Cbrt(inner * inner * inner + (outer * outer * outer - inner * inner * inner)
                    * instanceContext.RandomFloat(salt ^ 403));
                offset = new Vector3(planar * MathF.Cos(azimuth), planar * MathF.Sin(azimuth), z) * radius;
            }
            else if (className == "FitOnLine")
            {
                offset = start + direction * cumulative;
                cumulative += criteria.Length * scales[index];
            }

            foreach (var child in children)
            {
                if (SmartPropSelectionCriteria.MatchesSelectionCriteria(child, index, count, instanceContext))
                {
                    Traverse(child, Matrix4x4.CreateTranslation(offset) * parentTransform, instanceContext, output,
                        inheritedTint, inheritedMaterialGroup, nestedPropResolver, activeNestedProps, depth, maxDepth);
                }
            }
        }
    }

    private static bool TryFindLinearLength(KVObject element, SmartPropEvaluationContext context, out SmartPropLinearLength criteria)
    {
        if (SmartPropSelectionCriteria.TryGetLinearLength(element, context, out criteria))
        {
            return true;
        }
        if (element.TryGetValue("m_Children", out var children) && children.IsArray)
        {
            foreach (var child in children.AsArraySpan())
            {
                if (TryFindLinearLength(child, context, out criteria))
                {
                    return true;
                }
            }
        }
        return false;
    }

    private static float[] BuildPieceScales(float totalLength, SmartPropLinearLength criteria, string scaleMode)
    {
        var authored = criteria.Length;
        if (scaleMode == "SINGLE" && criteria.AllowScale)
        {
            return [criteria.ComputeScale(totalLength)];
        }

        if (!criteria.AllowScale || scaleMode.Equals("NONE", StringComparison.OrdinalIgnoreCase))
        {
            var naturalCount = Math.Clamp((int)MathF.Floor((totalLength / authored) + 1e-4f), 1, 256);
            return [.. Enumerable.Repeat(1f, naturalCount)];
        }

        var minScale = criteria.MinLength > 1e-4f ? criteria.MinLength / authored : 0.1f;
        var maxScale = criteria.MaxLength > 1e-4f ? criteria.MaxLength / authored : totalLength / authored;
        if (minScale > maxScale)
            (minScale, maxScale) = (maxScale, minScale);

        var idealCount = totalLength / authored;
        var minCount = Math.Clamp((int)MathF.Ceiling((totalLength / (authored * maxScale)) - 1e-4f), 1, 256);
        var maxCount = Math.Clamp((int)MathF.Floor((totalLength / (authored * minScale)) + 1e-4f), minCount, 256);

        if (scaleMode.Equals("SCALE_END_TO_FIT", StringComparison.OrdinalIgnoreCase))
        {
            var count = Math.Clamp((int)MathF.Round(idealCount), minCount, maxCount);
            if (count <= 1)
                return [Math.Clamp(idealCount, minScale, maxScale)];

            var pieces = new List<float>(Enumerable.Repeat(1f, count - 1));
            var remainder = totalLength - ((count - 1) * authored);
            pieces.Add(Math.Clamp(remainder / authored, minScale, maxScale));
            return [.. pieces];
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

    private static void TraversePath(
        KVObject element,
        Matrix4x4 parentTransform,
        SmartPropEvaluationContext context,
        EvaluationOutput output,
        Vector4? inheritedTint,
        string? inheritedMaterialGroup,
        Func<string, KVObject?>? nestedPropResolver,
        HashSet<string> activeNestedProps,
        int depth,
        int maxDepth)
    {
        if (!element.TryGetValue("m_Children", out var children) || !children.IsArray)
        {
            return;
        }

        var instances = CreatePathInstances(element, parentTransform, context);
        foreach (var instance in instances)
        {
            var instanceContext = context.WithPlacement(new SmartPropPlacement(instance.Index, instances.Length, context.LinearScale));
            foreach (var child in children.AsArraySpan())
            {
                if (SmartPropSelectionCriteria.MatchesSelectionCriteria(child, instance.Index, instances.Length, instanceContext))
                {
                    Traverse(child, instance.Transform, instanceContext, output, inheritedTint, inheritedMaterialGroup,
                        nestedPropResolver, activeNestedProps, depth, maxDepth);
                }
            }
        }
    }

    private static PathInstance[] CreatePathInstances(
        KVObject element,
        Matrix4x4 parentTransform,
        SmartPropEvaluationContext context)
    {
        var controlPoints = new List<Vector3>();
        if (element.TryGetValue("m_DefaultPath", out var path) && path.IsArray)
        {
            foreach (var point in path.AsArraySpan())
            {
                controlPoints.Add(context.ResolveVector3(point));
            }
        }

        if (controlPoints.Count == 0)
        {
            controlPoints.AddRange(DefaultPathPoints);
        }

        var up = context.ResolveVector3(ReadValue(element, "m_vUpDirection"), Vector3.UnitZ);
        var projectedUp = ReadBoolean(element, "m_bUseProjectedDistance") ? up : (Vector3?)null;
        var (samples, totalLength) = SmartPropSpline.ComputeSamples(controlPoints.ToArray(), projectedUp: projectedUp);
        var spacing = MathF.Max(0.001f, context.ResolveScalar(ReadValue(element, "m_flSpacing"), 1f));
        var offset = MathF.Max(0f, context.ResolveScalar(ReadValue(element, "m_flOffsetAlongPath")));
        var pathOffset = context.ResolveVector3(ReadValue(element, "m_vPathOffset"));
        var worldSpace = context.ResolveString(ReadValue(element, "m_PathSpace"), "WORLD") == "WORLD";

        var distances = new List<float>();
        if (totalLength < 1e-4f)
        {
            distances.Add(0f);
        }
        else
        {
            for (var distance = offset; distance <= totalLength && distances.Count < MaxPathInstances; distance += spacing)
            {
                distances.Add(distance);
            }
        }

        var instances = new PathInstance[Math.Max(distances.Count, 1)];
        for (var i = 0; i < instances.Length; i++)
        {
            var distance = distances.Count == 0 ? 0f : distances[i];
            var (position, tangent) = SmartPropSpline.InterpolateAtDistance(samples, totalLength, distance);
            var transform = SmartPropTransform.CreateFrame(position, tangent, up);
            transform = SmartPropTransform.ApplyPathOffset(transform, pathOffset, worldSpace);
            if (!worldSpace)
            {
                transform *= parentTransform;
            }

            instances[i] = new PathInstance(i, transform);
        }

        return instances;
    }

    private readonly record struct PathInstance(int Index, Matrix4x4 Transform);

    private static int SelectPickOneChild(
        KVObject element,
        ReadOnlySpan<KVObject> children,
        SmartPropEvaluationContext context)
    {
        if (children.Length == 0)
        {
            return -1;
        }

        var elementId = ReadInt32(element, "m_nElementID");
        if (context.TryGetPickOneSelection(elementId, out var selected))
        {
            return Math.Clamp(selected, 0, children.Length - 1);
        }

        var mode = context.ResolveString(ReadValue(element, "m_SelectionMode"), "RANDOM").ToUpperInvariant();
        if (mode is "SPECIFIC" or "SPECIFIC_CHILD")
        {
            return Math.Clamp((int)context.ResolveScalar(ReadValue(element, "m_SpecificChildIndex")), 0, children.Length - 1);
        }

        var totalWeight = 0f;
        foreach (var child in children)
        {
            totalWeight += MathF.Max(0f, SmartPropSelectionCriteria.GetChoiceWeight(child, context));
        }

        if (totalWeight <= 0f)
        {
            return 0;
        }

        var choice = context.RandomFloat(elementId ^ 31337) * totalWeight;
        for (var i = 0; i < children.Length; i++)
        {
            choice -= MathF.Max(0f, SmartPropSelectionCriteria.GetChoiceWeight(children[i], context));
            if (choice <= 0f)
            {
                return i;
            }
        }

        return children.Length - 1;
    }

    private static void TraverseNested(
        KVObject element,
        Matrix4x4 parentTransform,
        SmartPropEvaluationContext context,
        EvaluationOutput output,
        Vector4? inheritedTint,
        string? inheritedMaterialGroup,
        Func<string, KVObject?>? nestedPropResolver,
        HashSet<string> activeNestedProps,
        int depth,
        int maxDepth)
    {
        if (nestedPropResolver is null || depth >= maxDepth)
        {
            return;
        }

        var path = context.ResolveString(ReadValue(element, "m_sSmartProp"));
        if (string.IsNullOrEmpty(path) || !activeNestedProps.Add(path))
        {
            return;
        }

        var nestedRoot = nestedPropResolver(path);
        if (nestedRoot is not null)
        {
            Traverse(
                nestedRoot,
                parentTransform,
                CreateContext(nestedRoot).WithPlacement(context.Placement),
                output,
                inheritedTint,
                inheritedMaterialGroup,
                nestedPropResolver,
                activeNestedProps,
                depth + 1,
                maxDepth);
        }

        activeNestedProps.Remove(path);
    }

    internal static EvaluatedSmartPropWidget CreateWidget(
        KVObject data,
        string type,
        int elementId,
        Matrix4x4 transform,
        SmartPropEvaluationContext context)
    {
        var offset = context.ResolveVector3(ReadValue(data, "m_vOffset") ?? ReadValue(data, "m_vHandleOfffset") ?? ReadValue(data, "m_vHandleOffset"));
        var axis = context.ResolveVector3(ReadValue(data, "m_vRotationAxis"), Vector3.UnitZ);
        var coordinateSpace = context.ResolveString(ReadValue(data, "m_CoordinateSpace"), "WORLD");
        if (type == "rotator" && coordinateSpace is "ELEMENT" or "OBJECT")
        {
            axis = Vector3.TransformNormal(axis, transform);
            if (axis.LengthSquared() > 1e-8f)
                axis = Vector3.Normalize(axis);
        }

        var minimum = new Vector3(
            context.ResolveScalar(ReadValue(data, "m_flInitialMinX")),
            context.ResolveScalar(ReadValue(data, "m_flInitialMinY")),
            context.ResolveScalar(ReadValue(data, "m_flInitialMinZ")));
        var maximum = new Vector3(
            context.ResolveScalar(ReadValue(data, "m_flInitialMaxX")),
            context.ResolveScalar(ReadValue(data, "m_flInitialMaxY")),
            context.ResolveScalar(ReadValue(data, "m_flInitialMaxZ")));
        var handles = new[]
        {
            HasWidgetText(data, "m_OutputVariableMinX"), HasWidgetText(data, "m_OutputVariableMaxX"),
            HasWidgetText(data, "m_OutputVariableMinY"), HasWidgetText(data, "m_OutputVariableMaxY"),
            HasWidgetText(data, "m_OutputVariableMinZ"), HasWidgetText(data, "m_OutputVariableMaxZ"),
        };
        var activeAxes = new[]
        {
            handles[0] || handles[1] || minimum.X != 0f || maximum.X != 0f,
            handles[2] || handles[3] || minimum.Y != 0f || maximum.Y != 0f,
            handles[4] || handles[5] || minimum.Z != 0f || maximum.Z != 0f,
        };
        var defaultColor = type == "rotator" ? new Vector3(0.72f, 0.74f, 0.48f) : new(0.6f);
        var color = ResolveWidgetColor(ReadValue(data, type == "pickone" ? "m_HandleColor" : "m_DisplayColor"), context, defaultColor);

        return new(
            type,
            elementId,
            transform,
            offset,
            minimum,
            maximum,
            axis,
            color,
            handles,
            activeAxes,
            MathF.Max(0.01f, context.ResolveScalar(ReadValue(data, "m_flDisplayScale"), 1f)),
            MathF.Max(1f, context.ResolveScalar(ReadValue(data, "m_flDisplayRadius"), 16f)),
            context.ResolveScalar(ReadValue(data, "m_flInitialAngle")),
            MathF.Max(1f, context.ResolveScalar(ReadValue(data, "m_HandleSize"), 8f)),
            context.ResolveString(ReadValue(data, "m_HandleShape"), "SQUARE").ToUpperInvariant(),
            context.ResolveString(ReadValue(data, type switch
            {
                "locator" => "m_LocatorName",
                "pickone" => "m_OutputChoiceVariableName",
                _ => "m_Name",
            })));
    }

    private static bool HasWidgetText(KVObject data, string name)
        => data.TryGetValue(name, out var value) && value.ValueType == KVValueType.String && ((string)value).Length > 0;

    private static Vector3 ResolveWidgetColor(KVObject? data, SmartPropEvaluationContext context, Vector3 fallback)
    {
        var color = context.ResolveVector3(data, fallback);
        if (color.X > 1f || color.Y > 1f || color.Z > 1f)
        {
            color /= 255f;
        }
        return Vector3.Clamp(color, Vector3.Zero, Vector3.One);
    }

    private static bool IsModel(string className)
        => className is "Model" or "ModelEntity" or "PropPhysics" or "PropDynamic";

    private static bool IsDisabled(KVObject element)
        => element.TryGetValue("m_bEnabled", out var enabled)
            && enabled.ValueType == KVValueType.Boolean
            && !(bool)enabled;

    private static bool ReadBoolean(KVObject element, string name)
        => element.TryGetValue(name, out var value)
            && value.ValueType == KVValueType.Boolean
            && (bool)value;

    private static string? ResolveMaterialGroup(KVObject element, SmartPropEvaluationContext context)
    {
        var materialGroup = context.ResolveString(ReadValue(element, "m_MaterialGroupName"));
        return string.IsNullOrEmpty(materialGroup) ? null : materialGroup;
    }

    private static KVObject? ReadValue(KVObject element, string name)
        => element.TryGetValue(name, out var value) ? value : null;

    private static int ReadInt32(KVObject element, string name)
        => element.TryGetValue(name, out var value)
            && value.ValueType is KVValueType.Int32 or KVValueType.Int64 or KVValueType.UInt32 or KVValueType.UInt64
                ? (int)value
                : 0;
}
