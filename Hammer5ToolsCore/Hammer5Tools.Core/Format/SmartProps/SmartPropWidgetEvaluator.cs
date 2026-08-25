using System.Globalization;
using System.Numerics;
using System.Text.Json.Nodes;

using ValveKeyValue;
using ValveResourceFormat.ResourceTypes.SmartProps;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Produces editor widget placements by probing the authoritative VRF evaluator.
/// </summary>
internal static class SmartPropWidgetEvaluator
{
    private const string ProbeModel = "__hammer5tools_widget_probe__.vmdl";

    public static IReadOnlyList<EvaluatedSmartPropWidget> EvaluateJson(
        string json,
        string? nestedDocumentsJson,
        SmartPropEvaluationOptions options)
    {
        var root = JsonNode.Parse(json) as JsonObject;
        if (root is null)
            return [];

        var nestedDocuments = nestedDocumentsJson is null
            ? null
            : JsonNode.Parse(nestedDocumentsJson) as JsonObject;
        var probes = new List<WidgetProbe>();
        CollectProbes(root, [], probes, null, CreateContext(root));
        if (nestedDocuments is not null)
        {
            foreach (var document in nestedDocuments)
            {
                if (document.Value is JsonObject nestedRoot)
                {
                    CollectProbes(
                        nestedRoot,
                        [],
                        probes,
                        NormalizeResourcePath(document.Key),
                        CreateContext(nestedRoot));
                }
            }
        }
        var widgets = new List<EvaluatedSmartPropWidget>();

        foreach (var probe in probes)
        {
            options.CancellationToken.ThrowIfCancellationRequested();
            var instrumentedRoot = root.DeepClone();
            var instrumentedNested = nestedDocuments?.DeepClone().AsObject();
            var probeDocument = probe.DocumentPath is null
                ? instrumentedRoot
                : FindNestedDocument(instrumentedNested, probe.DocumentPath);
            var element = probeDocument is null ? null : FindObject(probeDocument, probe.Path);
            if (element is null)
                continue;

            Instrument(element, probe.ModifierIndex);
            var evaluated = SmartPropEvaluation.Evaluate(
                SmartPropJsonConverter.Convert(instrumentedRoot.ToJsonString()),
                instrumentedNested is null
                    ? null
                    : CreateNestedResolver(instrumentedNested),
                options.MaximumDepth);

            foreach (var placement in evaluated.Models.Where(model => model.ModelName == ProbeModel))
            {
                widgets.Add(CreateWidget(probe, placement.Transform, probe.Context));
            }
        }

        return widgets;
    }

    private static void CollectProbes(
        JsonNode? node,
        List<PathPart> path,
        List<WidgetProbe> probes,
        string? documentPath,
        SmartPropContext context)
    {
        if (node is JsonObject obj)
        {
            var className = ReadString(obj, "_class");
            if (IsElement(className))
            {
                var elementId = ReadInt32(obj, "m_nElementID");
                if (!IsModelClass(className))
                    probes.Add(new(
                        documentPath,
                        path.ToArray(),
                        null,
                        ClassIs(className, "Group") ? "group" : "element",
                        elementId,
                        obj.DeepClone().AsObject(),
                        context));

                if (className.EndsWith("PickOne", StringComparison.Ordinal))
                    probes.Add(new(
                        documentPath,
                        path.ToArray(),
                        null,
                        "pickone",
                        elementId,
                        obj.DeepClone().AsObject(),
                        context));

                if (obj["m_Modifiers"] is JsonArray modifiers)
                {
                    for (var index = 0; index < modifiers.Count; index++)
                    {
                        if (modifiers[index] is not JsonObject modifier || IsDisabled(modifier))
                            continue;

                        var type = WidgetType(ReadString(modifier, "_class"));
                        if (type is not null)
                        {
                            probes.Add(new(
                                documentPath,
                                path.ToArray(),
                                index,
                                type,
                                ReadInt32(modifier, "m_nElementID", elementId),
                                modifier.DeepClone().AsObject(),
                                context));
                        }
                    }
                }
            }

            foreach (var property in obj)
            {
                path.Add(new(property.Key, null));
                CollectProbes(property.Value, path, probes, documentPath, context);
                path.RemoveAt(path.Count - 1);
            }
        }
        else if (node is JsonArray array)
        {
            for (var index = 0; index < array.Count; index++)
            {
                path.Add(new(null, index));
                CollectProbes(array[index], path, probes, documentPath, context);
                path.RemoveAt(path.Count - 1);
            }
        }
    }

    private static void Instrument(JsonObject element, int? modifierIndex)
    {
        if (modifierIndex is { } count && element["m_Modifiers"] is JsonArray modifiers)
        {
            var prefix = new JsonArray();
            for (var index = 0; index < count; index++)
                prefix.Add(modifiers[index]?.DeepClone());
            element["m_Modifiers"] = prefix;
        }

        element["_class"] = "CSmartPropElement_Model";
        element["m_sModelName"] = ProbeModel;
        element.Remove("m_vModelScale");
        element.Remove("m_flModelScale");
        element.Remove("m_flUniformModelScale");
    }

    private static EvaluatedSmartPropWidget CreateWidget(
        WidgetProbe probe,
        Matrix4x4 transform,
        SmartPropContext context)
    {
        var data = probe.Data;
        var offset = ResolveVector(data["m_vOffset"] ?? data["m_vHandleOfffset"] ?? data["m_vHandleOffset"], context);
        var axis = ResolveVector(data["m_vRotationAxis"], context, Vector3.UnitZ);
        var coordinateSpace = ReadString(data, "m_CoordinateSpace", "WORLD");
        if (probe.Type == "rotator" && coordinateSpace is "ELEMENT" or "OBJECT")
        {
            axis = Vector3.TransformNormal(axis, transform);
            if (axis.LengthSquared() > 1e-8f)
                axis = Vector3.Normalize(axis);
        }

        var minimum = new Vector3(
            ResolveScalar(data["m_flInitialMinX"], context),
            ResolveScalar(data["m_flInitialMinY"], context),
            ResolveScalar(data["m_flInitialMinZ"], context));
        var maximum = new Vector3(
            ResolveScalar(data["m_flInitialMaxX"], context),
            ResolveScalar(data["m_flInitialMaxY"], context),
            ResolveScalar(data["m_flInitialMaxZ"], context));
        var handles = new[]
        {
            HasText(data, "m_OutputVariableMinX"), HasText(data, "m_OutputVariableMaxX"),
            HasText(data, "m_OutputVariableMinY"), HasText(data, "m_OutputVariableMaxY"),
            HasText(data, "m_OutputVariableMinZ"), HasText(data, "m_OutputVariableMaxZ"),
        };
        var activeAxes = new[]
        {
            handles[0] || handles[1] || minimum.X != 0f || maximum.X != 0f,
            handles[2] || handles[3] || minimum.Y != 0f || maximum.Y != 0f,
            handles[4] || handles[5] || minimum.Z != 0f || maximum.Z != 0f,
        };
        var defaultColor = probe.Type == "rotator" ? new Vector3(0.72f, 0.74f, 0.48f) : new(0.6f);
        var color = ResolveColor(data[probe.Type == "pickone" ? "m_HandleColor" : "m_DisplayColor"], context, defaultColor);

        return new(
            probe.Type,
            probe.ElementId,
            transform,
            offset,
            minimum,
            maximum,
            axis,
            color,
            handles,
            activeAxes,
            MathF.Max(0.01f, ResolveScalar(data["m_flDisplayScale"], context, 1f)),
            MathF.Max(1f, ResolveScalar(data["m_flDisplayRadius"], context, 16f)),
            ResolveScalar(data["m_flInitialAngle"], context),
            MathF.Max(1f, ResolveScalar(data["m_HandleSize"], context, 8f)),
            ReadString(data, "m_HandleShape", "SQUARE").ToUpperInvariant(),
            ReadString(data, probe.Type switch
            {
                "locator" => "m_LocatorName",
                "pickone" => "m_OutputChoiceVariableName",
                _ => "m_Name",
            }));
    }

    internal static SmartPropContext CreateContext(JsonObject root)
    {
        var scalars = new Dictionary<string, float>(StringComparer.OrdinalIgnoreCase);
        var vectors = new Dictionary<string, Vector4>(StringComparer.OrdinalIgnoreCase);
        if (root["m_Variables"] is not JsonArray variables)
            return new();

        foreach (var item in variables.OfType<JsonObject>())
        {
            var name = ReadString(item, "m_VariableName");
            if (name.Length == 0)
                continue;

            var value = item["m_DefaultValue"];
            var vector = ResolveLiteralVector(value);
            if (vector is { } resolvedVector)
                vectors[name] = new(resolvedVector, 0f);
            else
                scalars[name] = ResolveLiteralScalar(value);
        }
        return new(scalars, vectors);
    }

    internal static float ResolveScalar(JsonNode? node, SmartPropContext context, float defaultValue = 0f)
    {
        if (node is null)
            return defaultValue;
        if (node is JsonValue value)
        {
            if (value.TryGetValue<bool>(out var boolean))
                return boolean ? 1f : 0f;
            if (value.TryGetValue<float>(out var number))
                return number;
            if (value.TryGetValue<string>(out var text))
                return float.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out number)
                    ? number
                    : SmartPropExpression.Evaluate(text, context, defaultValue);
        }
        if (node is JsonObject obj)
        {
            if (obj["m_Expression"] is JsonValue expression && expression.TryGetValue<string>(out var text))
                return SmartPropExpression.Evaluate(text, context, defaultValue);
            if (obj["m_SourceName"] is JsonValue source && source.TryGetValue<string>(out var name))
                return context.ResolveScalar(SmartPropValue.FromVariable(name), defaultValue);
            if (obj["m_Components"] is JsonArray components && components.Count > 0)
                return ResolveScalar(components[0], context, defaultValue);
        }
        if (node is JsonArray array && array.Count > 0)
            return ResolveScalar(array[0], context, defaultValue);
        return defaultValue;
    }

    internal static Vector3 ResolveVector(JsonNode? node, SmartPropContext context, Vector3 defaultValue = default)
    {
        if (node is JsonObject obj)
        {
            if (obj["m_Components"] is JsonArray components)
                node = components;
            else if (obj["m_SourceName"] is JsonValue source && source.TryGetValue<string>(out var name))
                return context.ResolveVector(SmartPropValue.FromVariable(name), defaultValue);
            else if (obj["m_Expression"] is JsonValue expression && expression.TryGetValue<string>(out var text))
                return new(SmartPropExpression.Evaluate(text, context, defaultValue.X));
        }
        if (node is JsonArray array)
        {
            return new(
                array.Count > 0 ? ResolveScalar(array[0], context, defaultValue.X) : defaultValue.X,
                array.Count > 1 ? ResolveScalar(array[1], context, defaultValue.Y) : defaultValue.Y,
                array.Count > 2 ? ResolveScalar(array[2], context, defaultValue.Z) : defaultValue.Z);
        }
        return node is null ? defaultValue : new(ResolveScalar(node, context, defaultValue.X));
    }

    private static Vector3 ResolveColor(JsonNode? node, SmartPropContext context, Vector3 defaultValue)
    {
        var color = ResolveVector(node, context, defaultValue);
        if (color.X > 1f || color.Y > 1f || color.Z > 1f)
            color /= 255f;
        return Vector3.Clamp(color, Vector3.Zero, Vector3.One);
    }

    internal static JsonObject? FindObject(JsonNode node, IReadOnlyList<PathPart> path)
    {
        JsonNode? current = node;
        foreach (var part in path)
            current = part.Name is not null ? current?[part.Name] : current?[part.Index!.Value];
        return current as JsonObject;
    }

    /// <summary>
    /// Resolves an element's own accumulated world transform by rigging a clone of it as a
    /// <c>CSmartPropElement_Model</c> (keeping its real <c>m_Modifiers</c> and ancestor chain) and
    /// letting VRF's real evaluator compute the placement — the parent/modifier composition logic
    /// lives in VRF's internal <c>SmartPropModifierEvaluator</c>, so probing is the only way to reach it.
    /// </summary>
    internal static Matrix4x4? ProbeElementFrame(
        JsonObject root,
        JsonObject? nestedDocuments,
        IReadOnlyList<PathPart> path,
        SmartPropEvaluationOptions options,
        string probeModelName)
    {
        if (root.DeepClone() is not JsonObject clone)
            return null;
        if (FindObject(clone, path) is not { } element)
            return null;

        element["_class"] = "CSmartPropElement_Model";
        element["m_sModelName"] = probeModelName;
        element.Remove("m_vModelScale");
        element.Remove("m_flModelScale");
        element.Remove("m_flUniformModelScale");

        var resolver = nestedDocuments is null ? null : CreateNestedResolver(nestedDocuments);
        var evaluated = SmartPropEvaluation.Evaluate(
            SmartPropJsonConverter.Convert(clone.ToJsonString()),
            resolver,
            options.MaximumDepth);

        foreach (var placement in evaluated.Models)
        {
            if (placement.ModelName == probeModelName)
                return placement.Transform;
        }

        return null;
    }

    private static JsonObject? FindNestedDocument(JsonObject? documents, string normalizedPath)
    {
        if (documents is null)
            return null;
        foreach (var document in documents)
        {
            if (NormalizeResourcePath(document.Key).Equals(normalizedPath, StringComparison.OrdinalIgnoreCase))
                return document.Value as JsonObject;
        }
        return null;
    }

    internal static Func<string, KVObject?> CreateNestedResolver(JsonObject documents)
    {
        var converted = new Dictionary<string, KVObject>(StringComparer.OrdinalIgnoreCase);
        foreach (var document in documents)
        {
            if (document.Value is not null)
            {
                converted[NormalizeResourcePath(document.Key)] =
                    SmartPropJsonConverter.Convert(document.Value.ToJsonString());
            }
        }
        return path => converted.GetValueOrDefault(NormalizeResourcePath(path));
    }

    private static string? WidgetType(string className)
    {
        if (className.EndsWith("CreateSizer", StringComparison.Ordinal))
            return "sizer";
        if (className.EndsWith("CreateLocator", StringComparison.Ordinal))
            return "locator";
        if (className.EndsWith("CreateRotator", StringComparison.Ordinal))
            return "rotator";
        return null;
    }

    /// <summary>One element matching a target class, with the model-class descendants under it.</summary>
    internal readonly record struct DescendantElementInfo(
        PathPart[] Path, JsonObject Node, int Depth, HashSet<int> DescendantModelIds);

    /// <summary>
    /// Finds every element of <paramref name="targetClassShortName"/> (e.g. <c>"Layout2DGrid"</c>,
    /// without the <c>CSmartPropElement_</c> prefix) and, for each, the element ids of every
    /// Model/ModelEntity/PropPhysics/PropDynamic beneath it. Nested matches of the same class are
    /// supported — an inner match's descendants also count toward its outer ancestors. Ordered by
    /// nesting depth so callers can process innermost-first.
    /// </summary>
    internal static List<DescendantElementInfo> CollectElementsWithDescendants(JsonObject root, string targetClassShortName)
    {
        var found = new List<DescendantElementInfo>();
        var active = new List<int>();
        Walk(root, []);
        return found;

        void Walk(JsonNode? node, List<PathPart> path)
        {
            if (node is JsonObject obj)
            {
                var className = ReadString(obj, "_class");
                var pushed = false;
                if (ClassIs(className, targetClassShortName))
                {
                    found.Add(new(path.ToArray(), obj, active.Count, []));
                    active.Add(found.Count - 1);
                    pushed = true;
                }
                else if (IsModelClass(className))
                {
                    var elementId = ReadInt32(obj, "m_nElementID");
                    foreach (var index in active)
                        found[index].DescendantModelIds.Add(elementId);
                }

                foreach (var property in obj)
                {
                    path.Add(new(property.Key, null));
                    Walk(property.Value, path);
                    path.RemoveAt(path.Count - 1);
                }

                if (pushed)
                    active.RemoveAt(active.Count - 1);
            }
            else if (node is JsonArray array)
            {
                for (var index = 0; index < array.Count; index++)
                {
                    path.Add(new(null, index));
                    Walk(array[index], path);
                    path.RemoveAt(path.Count - 1);
                }
            }
        }
    }

    internal static bool IsModelClass(string className)
        => ClassIs(className, "Model") || ClassIs(className, "ModelEntity")
            || ClassIs(className, "PropPhysics") || ClassIs(className, "PropDynamic");

    internal static bool ClassIs(string className, string shortName)
        => className.Equals(shortName, StringComparison.Ordinal)
            || className.Equals("CSmartPropElement_" + shortName, StringComparison.Ordinal);

    private static bool IsElement(string className)
        => className.StartsWith("CSmartPropElement_", StringComparison.Ordinal)
            || className is "Group" or "Model" or "ModelEntity" or "PropPhysics" or "PropDynamic"
                or "PickOne" or "FitOnLine" or "PlaceOnPath" or "SmartProp";

    private static bool IsDisabled(JsonObject obj)
        => obj["m_bEnabled"] is JsonValue value && value.TryGetValue<bool>(out var enabled) && !enabled;

    private static bool HasText(JsonObject obj, string name) => ReadString(obj, name).Length > 0;

    internal static string ReadString(JsonObject obj, string name, string defaultValue = "")
        => obj[name] is JsonValue value && value.TryGetValue<string>(out var text) ? text : defaultValue;

    internal static int ReadInt32(JsonObject obj, string name, int defaultValue = 0)
        => obj[name] is JsonValue value && value.TryGetValue<int>(out var number) ? number : defaultValue;

    private static float ResolveLiteralScalar(JsonNode? node)
    {
        if (node is JsonValue value)
        {
            if (value.TryGetValue<float>(out var number))
                return number;
            if (value.TryGetValue<bool>(out var boolean))
                return boolean ? 1f : 0f;
            if (value.TryGetValue<string>(out var text)
                && float.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out number))
                return number;
        }
        return 0f;
    }

    private static Vector3? ResolveLiteralVector(JsonNode? node)
    {
        if (node is JsonObject obj)
            node = obj["m_Components"];
        if (node is not JsonArray array)
            return null;
        return new(
            array.Count > 0 ? ResolveLiteralScalar(array[0]) : 0f,
            array.Count > 1 ? ResolveLiteralScalar(array[1]) : 0f,
            array.Count > 2 ? ResolveLiteralScalar(array[2]) : 0f);
    }

    internal static string NormalizeResourcePath(string path) => path.Replace('\\', '/').TrimStart('/');

    internal readonly record struct PathPart(string? Name, int? Index);
    private sealed record WidgetProbe(
        string? DocumentPath,
        IReadOnlyList<PathPart> Path,
        int? ModifierIndex,
        string Type,
        int ElementId,
        JsonObject Data,
        SmartPropContext Context);
}
