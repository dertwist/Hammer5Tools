using ValveKeyValue;

namespace Hammer5Tools.Core.Format.SmartProps.Evaluation;

internal readonly record struct SmartPropModel(
    int ElementId,
    string ModelName,
    Matrix4x4 Transform,
    string? MaterialGroup,
    Vector4? TintColor);

internal sealed record SmartPropEvaluationResult(IReadOnlyList<SmartPropModel> Models);

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
        int maxDepth = DefaultMaxDepth)
    {
        context ??= CreateContext(root);
        var models = new List<SmartPropModel>();
        Traverse(root, Matrix4x4.Identity, context, models, null, null, nestedPropResolver, [], 0, maxDepth);
        return new SmartPropEvaluationResult(models);
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
        List<SmartPropModel> models,
        Vector4? inheritedTint,
        string? inheritedMaterialGroup,
        Func<string, KVObject?>? nestedPropResolver,
        HashSet<string> activeNestedProps,
        int depth,
        int maxDepth)
    {
        if (models.Count >= DefaultMaxModels
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
            inheritedMaterialGroup);
        if (modifierResult.IsFilteredOut)
        {
            return;
        }

        var className = SmartPropClass.Read(element);
        if (IsModel(className))
        {
            var modelName = context.ResolveString(ReadValue(element, "m_sModelName"));
            if (!string.IsNullOrEmpty(modelName))
            {
                models.Add(new SmartPropModel(
                    ReadInt32(element, "m_nElementID"),
                    modelName,
                    modifierResult.ModelTransform,
                    ResolveMaterialGroup(element, context) ?? modifierResult.MaterialGroup,
                    modifierResult.TintColor));
            }
        }

        if (className == "SmartProp")
        {
            TraverseNested(
                element,
                modifierResult.WorldTransform,
                context,
                models,
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
            TraversePath(element, modifierResult.WorldTransform, context, models, modifierResult.TintColor,
                modifierResult.MaterialGroup, nestedPropResolver, activeNestedProps, depth, maxDepth);
            return;
        }

        if (!element.TryGetValue("m_Children", out var children) || !children.IsArray)
        {
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

            var childContext = CreateChildContext(element, child, context);
            Traverse(child, modifierResult.WorldTransform, childContext, models, modifierResult.TintColor,
                modifierResult.MaterialGroup, nestedPropResolver, activeNestedProps, depth, maxDepth);
        }
    }

    private static SmartPropEvaluationContext CreateChildContext(
        KVObject parent,
        KVObject child,
        SmartPropEvaluationContext context)
    {
        if (SmartPropClass.Read(parent) != "FitOnLine")
        {
            return context;
        }

        var start = context.ResolveVector3(ReadValue(parent, "m_vStart"));
        var end = context.ResolveVector3(ReadValue(parent, "m_vEnd"));
        var scale = SmartPropSelectionCriteria.TryGetLinearLength(child, context, out var linearLength)
            ? linearLength.ComputeScale(Vector3.Distance(start, end))
            : 1f;
        return context.WithPlacement(new SmartPropPlacement(context.InstanceIndex, context.InstanceCount, scale));
    }

    private static void TraversePath(
        KVObject element,
        Matrix4x4 parentTransform,
        SmartPropEvaluationContext context,
        List<SmartPropModel> models,
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
                    Traverse(child, instance.Transform, instanceContext, models, inheritedTint, inheritedMaterialGroup,
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
        List<SmartPropModel> models,
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
                CreateContext(nestedRoot),
                models,
                inheritedTint,
                inheritedMaterialGroup,
                nestedPropResolver,
                activeNestedProps,
                depth + 1,
                maxDepth);
        }

        activeNestedProps.Remove(path);
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
