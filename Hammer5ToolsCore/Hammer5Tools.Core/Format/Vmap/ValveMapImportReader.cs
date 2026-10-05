using System.Collections;
using System.Globalization;
using System.Numerics;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Datamodel;
using Hammer5Tools.Core.Format.Materials;
using Hammer5Tools.Core.Format.SmartProps;
using Hammer5Tools.Core.IO.CompiledResource;

namespace Hammer5Tools.Core.Format.Vmap;

/// <summary>Reads editable polygons, hierarchy, editor metadata and evaluated SmartProp placements for DCC import.</summary>
public sealed class ValveMapImportReader
{
    private readonly JsonArray nodes = [];
    private readonly JsonArray selectionSets = [];
    private readonly JsonArray selectionSetStates = [];
    private readonly JsonArray diagnostics = [];
    private readonly HashSet<string> expanding = new(StringComparer.OrdinalIgnoreCase);
    private VmapContentFiles files = null!;
    private ValveMapImportOptions options = new();
    private readonly Dictionary<string, VmapDocument> documents = new(StringComparer.OrdinalIgnoreCase);
    private readonly Dictionary<(string Path, Guid Id), JsonObject> meshes = [];
    private Regex[] selectionPatterns = [];
    private int matchingSets;
    private readonly Dictionary<string, JsonArray> smartPropModels = new(StringComparer.Ordinal);

    /// <summary>Returns schema version 2 JSON with authored visibility. Create a reader for each import.</summary>
    public string Read(string path, string? contentRoot = null, ValveMapImportOptions? importOptions = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        nodes.Clear();
        selectionSets.Clear();
        selectionSetStates.Clear();
        diagnostics.Clear();
        expanding.Clear();
        documents.Clear();
        meshes.Clear();
        smartPropModels.Clear();
        matchingSets = 0;
        options = importOptions ?? new();
        selectionPatterns = options.SelectionSetMask.Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(pattern => new Regex($"^{Regex.Escape(pattern).Replace("\\*", ".*", StringComparison.Ordinal).Replace("\\?", ".", StringComparison.Ordinal)}$",
                RegexOptions.IgnoreCase | RegexOptions.CultureInvariant, TimeSpan.FromSeconds(1))).ToArray();
        using var contentFiles = new VmapContentFiles(path, contentRoot, options.GameDirectory, options.ActiveAddon);
        files = contentFiles;
        VisitMap(path, Matrix4x4.Identity, "", false, 0, false);
        if (selectionPatterns.Length > 0 && matchingSets == 0)
            diagnostics.Add(ConvertValue($"No Hammer selection sets match '{options.SelectionSetMask}'."));
        return SceneJson(path);
    }

    private string SceneJson(string path, JsonObject? smartPropDocument = null)
    {
        var result = new JsonObject
        {
            ["schemaVersion"] = ConvertValue(2),
            ["path"] = ConvertValue(Path.GetFullPath(path)),
            ["nodes"] = nodes,
            ["selectionSets"] = selectionSets,
            ["selectionSetStates"] = selectionSetStates,
            ["diagnostics"] = diagnostics,
            ["dependencies"] = ConvertValue(files.Dependencies),
        };
        if (smartPropDocument is not null)
            result["smartPropDocument"] = smartPropDocument;
        try
        {
            return result.ToJsonString(VmapImportJsonContext.Default.Options);
        }
        finally
        {
            result.Clear();
        }
    }

    private void VisitMap(string path, Matrix4x4 transform, string parent, bool hidden, int depth, bool parentSelected, int parentState = 0)
    {
        path = Path.GetFullPath(path);
        if (depth >= 32 || !expanding.Add(path))
        {
            diagnostics.Add(ConvertValue($"Prefab cycle or nesting limit: {path}"));
            return;
        }
        try
        {
            if (!documents.TryGetValue(path, out var document))
                documents[path] = document = VmapDocument.LoadInMemory(path);
            files.Dependencies.Add(path);
            var scope = parent;
            var selected = new HashSet<Guid>();
            var hiddenNodes = new HashSet<Guid>();
            var visibility = Value(document.Root, "visbility") as Element ?? Value(document.Root, "visibility") as Element;
            if (visibility is not null && Value(visibility, "nodes") is ElementArray visibilityNodes
                && Value(visibility, "hiddenFlags") is IntArray flags)
                for (var index = 0; index < Math.Min(visibilityNodes.Count, flags.Count); index++)
                    if (flags[index] != 0 && visibilityNodes[index] is { } hiddenNode)
                        hiddenNodes.Add(hiddenNode.ID);
            var states = new Dictionary<Guid, int>();
            var authoredHidden = new HashSet<Guid>(hiddenNodes);
            void HiddenChildren(Element element, bool ancestorHidden, HashSet<Guid> visited)
            {
                if (!visited.Add(element.ID))
                    return;
                var isHidden = ancestorHidden || hiddenNodes.Contains(element.ID) || Value(element, "force_hidden") is true;
                if (isHidden)
                    authoredHidden.Add(element.ID);
                if (Value(element, "children") is ElementArray children)
                    foreach (var child in children)
                        if (child is not null)
                            HiddenChildren(child, isHidden, visited);
            }
            HiddenChildren(document.World, hidden, []);
            if (Value(document.Root, "rootSelectionSet") is Element rootSets)
            {
                selectionSets.Add(new JsonObject { ["scope"] = ConvertValue(scope), ["data"] = Metadata(rootSets) });
                Select(rootSets, selected);
                SelectionStates(rootSets, path, authoredHidden, states);
            }
            Visit(document.World, transform, parent, hidden, path, depth, scope, new HashSet<Guid>(), selected, parentSelected,
                hiddenNodes, states, parentState);
        }
        finally
        {
            expanding.Remove(path);
        }
    }

    private void Visit(Element node, Matrix4x4 parentTransform, string parent, bool parentHidden,
        string mapPath, int depth, string scope, HashSet<Guid> ancestors, HashSet<Guid> selected, bool parentSelected,
        HashSet<Guid> hiddenNodes, Dictionary<Guid, int> states, int parentState)
    {
        if (!ancestors.Add(node.ID))
        {
            diagnostics.Add(ConvertValue($"Node cycle: {node.Name}"));
            return;
        }
        try
        {
            var id = $"{parent}/{nodes.Count}";
            var transform = ValveMapSceneReader.LocalTransform(node) * parentTransform;
            var state = Math.Max(parentState, states.GetValueOrDefault(node.ID));
            var hidden = state == 2 || (state == 0 && (parentHidden || Value(node, "force_hidden") is true || hiddenNodes.Contains(node.ID)));
            var isSelected = parentSelected || selected.Contains(node.ID);
            var included = (selectionPatterns.Length == 0 || isSelected != options.InvertSelectionSetMask)
                && state != 2 && (options.IncludeHidden || !hidden);
            if (options.IgnoreStaticOverlays && node.ClassName == "CMapStaticOverlay")
                included = false;
            if (included && options.IgnoreToolMaterialObjects && Value(node, "meshData") is Element toolMesh
                && UsesOnlyToolMaterials(toolMesh))
            {
                included = false;
            }
            var properties = Value(node, "entity_properties") as Element;
            var item = new JsonObject
            {
                ["id"] = ConvertValue(id),
                ["parent"] = ConvertValue(parent),
                ["scope"] = ConvertValue(scope),
                ["sourceMap"] = ConvertValue(mapPath),
                ["sourceId"] = ConvertValue(node.ID.ToString()),
                ["nodeId"] = ConvertValue(Value(node, "nodeID")?.ToString()),
                ["referenceId"] = ConvertValue(Value(node, "referenceID")?.ToString()),
                ["name"] = ConvertValue(node.Name ?? ""),
                ["type"] = ConvertValue(node.ClassName),
                ["hidden"] = ConvertValue(hidden),
                ["included"] = ConvertValue(included),
                ["transform"] = Matrix(transform),
                ["properties"] = properties is null ? new JsonObject() : Metadata(properties),
                ["metadata"] = options.IncludeEditorMetadata ? Metadata(node, omit: ["children", "meshData", "entity_properties"]) : new JsonObject(),
            };
            nodes.Add(item);
            if (included && !options.MetadataOnly && Value(node, "meshData") is Element mesh)
            {
                try
                {
                    var meshKey = (mapPath, mesh.ID);
                    if (meshes.TryGetValue(meshKey, out var projection))
                    {
                        item["mesh"] = projection.DeepClone();
                    }
                    else
                    {
                        meshes[meshKey] = projection = ReadMesh(mesh, options.IncludeEditorMetadata);
                        item["mesh"] = projection;
                    }
                    if (HasSubdivision(mesh))
                    {
                        diagnostics.Add(ConvertValue($"{node.Name}: subdivision/displacement data retained as metadata; only the control mesh is imported."));
                    }
                }
                catch (InvalidDataException error)
                {
                    diagnostics.Add(ConvertValue($"{node.Name}: {error.Message}"));
                }
            }
            if (properties is not null && Value(properties, "model") is string model)
            {
                item["model"] = ConvertValue(model);
            }
            if (node.ClassName == "CMapSmartProp" && Value(node, "smartPropFilename") is string smartProp)
            {
                item["smartProp"] = ConvertValue(smartProp);
                if (included && !options.MetadataOnly && options.EvaluateSmartProps)
                {
                    try
                    {
                        var overrides = (JsonObject)ConvertValue(ValveMapSceneReader.ReadParameters(node))!;
                        item["variables"] = overrides;
                        item["smartPropModels"] = EvaluateSmartProp(smartProp, overrides, out _);
                    }
                    catch (Exception error) when (error is IOException or System.Text.Json.JsonException or InvalidOperationException)
                    {
                        diagnostics.Add(ConvertValue($"{smartProp}: {error.Message}"));
                    }
                }
            }
            if (Value(node, "children") is ElementArray children)
            {
                foreach (var child in children)
                {
                    if (child is not null)
                    {
                        // Hammer children are in map space; only prefab/instance expansion changes that space.
                        Visit(child, parentTransform, id, hidden, mapPath, depth, scope, ancestors, selected, isSelected,
                            hiddenNodes, states, state);
                    }
                }
            }
            if (node.ClassName == "CMapInstance" && Value(node, "target") is Element targetNode)
            {
                item["instanceTarget"] = ConvertValue(targetNode.ID.ToString());
                if (depth >= 32 || !Matrix4x4.Invert(ValveMapSceneReader.LocalTransform(targetNode), out var inverseTarget))
                {
                    diagnostics.Add(ConvertValue($"Instance cycle, nesting limit or singular target transform: {node.Name}"));
                }
                else
                {
                    Visit(targetNode, inverseTarget * transform, id, hidden, mapPath, depth + 1, id,
                        ancestors, [], isSelected, [], [], state);
                }
            }
            if (node.ClassName == "CMapPrefab" && Value(node, "targetMapPath") is string target)
            {
                item["prefabPath"] = ConvertValue(target);
                if (!options.ExpandPrefabs || (hidden && !options.IncludeHidden))
                    return;
                var resolved = files.Resolve(target, mapPath);
                if (resolved is null)
                {
                    diagnostics.Add(ConvertValue($"Prefab not found: {target}"));
                }
                else
                {
                    try
                    {
                        VisitMap(resolved, transform, id, hidden, depth + 1, isSelected, state);
                    }
                    catch (Exception error) when (error is IOException or InvalidOperationException or ArgumentException)
                    {
                        diagnostics.Add(ConvertValue($"Prefab {target}: {error.Message}"));
                    }
                }
            }
        }
        finally
        {
            ancestors.Remove(node.ID);
        }
    }

    private void Select(Element set, HashSet<Guid> selected)
    {
        if (Value(set, "selectionSetName") is string name && selectionPatterns.Any(pattern => pattern.IsMatch(name)))
        {
            matchingSets++;
            var visited = new HashSet<Guid>();
            void References(object? value)
            {
                if (value is Element element)
                {
                    if (!visited.Add(element.ID))
                        return;
                    if (element.ClassName is "CMapWorld" or "CMapGroup" or "CMapPrefab" or "CMapMesh"
                        or "CMapEntity" or "CMapSmartProp" or "CMapStaticOverlay" or "CMapInstance")
                    {
                        selected.Add(element.ID);
                        return;
                    }
                    foreach (var (_, child) in element)
                        References(child);
                }
                else if (value is IEnumerable array && value is not string)
                {
                    foreach (var child in array)
                        References(child);
                }
            }
            References(Value(set, "selectionSetData"));
        }
        if (Value(set, "children") is ElementArray children)
            foreach (var child in children)
                if (child is not null)
                    Select(child, selected);
    }

    private void SelectionStates(Element set, string path, HashSet<Guid> hidden, Dictionary<Guid, int> states)
    {
        if (Value(set, "selectionSetName") is string name && name.Length > 0)
        {
            var objects = new List<Element>();
            var visited = new HashSet<Guid>();
            void References(object? value)
            {
                if (value is Element element)
                {
                    if (!visited.Add(element.ID))
                        return;
                    if (element.ClassName is "CMapWorld" or "CMapGroup" or "CMapPrefab" or "CMapMesh"
                        or "CMapEntity" or "CMapSmartProp" or "CMapStaticOverlay" or "CMapInstance")
                        objects.Add(element);
                    else
                        foreach (var (_, child) in element)
                            References(child);
                }
                else if (value is IEnumerable array && value is not string)
                    foreach (var child in array)
                        References(child);
            }
            References(Value(set, "selectionSetData"));
            var key = path.Replace('\\', '/') + "#" + set.ID;
            var visibility = objects.Count == 0 ? "empty" : objects.All(element => hidden.Contains(element.ID)) ? "hidden"
                : objects.Any(element => hidden.Contains(element.ID)) ? "mixed" : "visible";
            selectionSetStates.Add(new JsonObject
            {
                ["key"] = ConvertValue(key),
                ["name"] = ConvertValue(name),
                ["sourceMap"] = ConvertValue(path),
                ["visibility"] = ConvertValue(visibility),
            });
            if (options.SelectionSetOverrides.TryGetValue(key, out var state))
            {
                if (state is < 0 or > 2)
                    throw new ArgumentException("Selection set state must be 0, 1 or 2.");
                foreach (var element in objects)
                    states[element.ID] = Math.Max(states.GetValueOrDefault(element.ID), state);
            }
        }
        if (Value(set, "children") is ElementArray children)
            foreach (var child in children)
                if (child is not null)
                    SelectionStates(child, path, hidden, states);
    }

    /// <summary>Deserializes a source or compiled SmartProp and evaluates it as a DCC scene.</summary>
    public string ReadSmartProp(string path, string? contentRoot = null, ValveMapImportOptions? importOptions = null,
        string variablesJson = "{}")
    {
        nodes.Clear();
        selectionSets.Clear();
        selectionSetStates.Clear();
        diagnostics.Clear();
        smartPropModels.Clear();
        options = importOptions ?? new();
        using var contentFiles = new VmapContentFiles(path, contentRoot, options.GameDirectory, options.ActiveAddon);
        files = contentFiles;
        var variables = JsonNode.Parse(variablesJson) as JsonObject
            ?? throw new InvalidDataException("SmartProp variable overrides must be a JSON object.");
        var models = EvaluateSmartProp(path, variables, out var document);
        nodes.Add(new JsonObject
        {
            ["id"] = ConvertValue("/0"),
            ["parent"] = ConvertValue(""),
            ["scope"] = ConvertValue(""),
            ["sourceId"] = ConvertValue("/0"),
            ["sourceMap"] = ConvertValue(path),
            ["name"] = ConvertValue(Path.GetFileNameWithoutExtension(path)),
            ["type"] = ConvertValue("CMapSmartProp"),
            ["hidden"] = ConvertValue(false),
            ["included"] = ConvertValue(true),
            ["transform"] = Matrix(Matrix4x4.Identity),
            ["properties"] = new JsonObject(),
            ["metadata"] = new JsonObject(),
            ["smartProp"] = ConvertValue(path),
            ["smartPropModels"] = models,
            ["variables"] = variables,
        });
        return SceneJson(path, document);
    }

    private JsonArray EvaluateSmartProp(string resource, JsonObject overrides, out JsonObject document)
    {
        document = files.ReadSmartProp(resource, out var nested);
        var key = resource + "\n" + overrides.ToJsonString(VmapImportJsonContext.Default.Options);
        if (smartPropModels.TryGetValue(key, out var cached))
            return (JsonArray)cached.DeepClone();
        if (document["m_Variables"] is JsonArray variables)
            foreach (var variable in variables.OfType<JsonObject>())
                if (variable["m_VariableName"]?.GetValue<string>() is { } name && overrides.TryGetPropertyValue(name, out var value))
                    variable["m_DefaultValue"] = value?.DeepClone();
        var result = SmartPropEvaluator.EvaluateJson(document.ToJsonString(VmapImportJsonContext.Default.Options),
            nested.ToJsonString(VmapImportJsonContext.Default.Options));
        foreach (var diagnostic in result.Diagnostics)
            diagnostics.Add(ConvertValue($"{resource}: {diagnostic.Code}: {diagnostic.Message}"));
        var models = new JsonArray(result.Models.Select(Model).ToArray());
        foreach (var diagnostic in files.Diagnostics)
            if (!diagnostics.Any(value => value?.GetValue<string>() == diagnostic))
                diagnostics.Add(ConvertValue(diagnostic));
        smartPropModels[key] = models;
        return (JsonArray)models.DeepClone();
    }

    private static bool UsesOnlyToolMaterials(Element mesh)
    {
        if (Value(mesh, "faceEdgeIndices") is not IntArray edges)
            return false;
        var materials = Value(mesh, "materials") as StringArray;
        var faceData = Value(mesh, "faceDataIndices") as IntArray;
        var materialIndices = ValveMapSceneReader.StreamData(mesh, "faceData", "materialindex") as IntArray;
        var hasFace = false;
        for (var face = 0; face < edges.Count; face++)
        {
            if (edges[face] == -1)
                continue;
            hasFace = true;
            var material = ValveMapSceneReader.MaterialOf(face, faceData, materialIndices, materials);
            if (!VmtFile.IsToolMaterialPath("/" + material))
                return false;
        }
        return hasFace;
    }

    private static JsonObject ReadMesh(Element mesh, bool includeMetadata)
    {
        var positions = ValveMapSceneReader.StreamData(mesh, "vertexData", "position") as Vector3Array;
        var vertexData = Value(mesh, "vertexDataIndices") as IntArray;
        var edgeVertices = Value(mesh, "edgeVertexIndices") as IntArray;
        var edgeNext = Value(mesh, "edgeNextIndices") as IntArray;
        var faceEdges = Value(mesh, "faceEdgeIndices") as IntArray;
        if (positions is null || vertexData is null || edgeVertices is null || edgeNext is null || faceEdges is null)
        {
            throw new InvalidDataException("Mesh topology is incomplete.");
        }
        var points = new JsonArray();
        foreach (var index in vertexData)
        {
            CheckIndex(index, positions.Count);
            points.Add(ConvertValue(positions[index]));
        }
        var corners = Value(mesh, "edgeVertexDataIndices") as IntArray;
        var uvs = ValveMapSceneReader.StreamData(mesh, "faceVertexData", "texcoord") as Vector2Array;
        var normals = ValveMapSceneReader.StreamData(mesh, "faceVertexData", "normal") as Vector3Array;
        var faceData = Value(mesh, "faceDataIndices") as IntArray;
        var materials = Value(mesh, "materials") as StringArray;
        var materialIndices = ValveMapSceneReader.StreamData(mesh, "faceData", "materialindex") as IntArray;
        var faces = new JsonArray();
        for (var face = 0; face < faceEdges.Count; face++)
        {
            var start = faceEdges[face];
            if (start == -1)
            {
                continue;
            }
            var indices = new JsonArray();
            var texcoords = new JsonArray();
            var vertexNormals = new JsonArray();
            var edge = start;
            var seen = new HashSet<int>();
            do
            {
                CheckIndex(edge, edgeNext.Count);
                CheckIndex(edge, edgeVertices.Count);
                if (!seen.Add(edge))
                {
                    throw new InvalidDataException("Mesh face contains a broken half-edge ring.");
                }
                var vertex = edgeVertices[edge];
                CheckIndex(vertex, vertexData.Count);
                indices.Add(ConvertValue(vertex));
                var corner = corners is not null && edge < corners.Count ? corners[edge] : -1;
                texcoords.Add(ConvertValue(uvs is not null && corner >= 0 && corner < uvs.Count ? uvs[corner] : Vector2.Zero));
                vertexNormals.Add(ConvertValue(normals is not null && corner >= 0 && corner < normals.Count ? normals[corner] : Vector3.Zero));
                edge = edgeNext[edge];
            }
            while (edge != start);
            if (indices.Count < 3)
            {
                throw new InvalidDataException("Mesh face has fewer than three vertices.");
            }
            faces.Add(new JsonObject
            {
                ["sourceFace"] = ConvertValue(face),
                ["indices"] = indices,
                ["uvs"] = texcoords,
                ["normals"] = vertexNormals,
                ["material"] = ConvertValue(ValveMapSceneReader.MaterialOf(face, faceData, materialIndices, materials)),
            });
        }
        return new JsonObject { ["points"] = points, ["faces"] = faces, ["metadata"] = includeMetadata ? Metadata(mesh) : new JsonObject() };
    }

    private static bool HasSubdivision(Element mesh) => Value(mesh, "subdivisionData") is Element data
        && (Value(data, "subdivisionLevels") is IntArray levels && levels.Any(level => level > 0)
            || Value(data, "streams") is ElementArray streams && streams.Count > 0);

    private static void CheckIndex(int index, int count)
    {
        if (index < 0 || index >= count)
        {
            throw new InvalidDataException($"Mesh index {index} is outside [0, {count}).");
        }
    }

    private static JsonNode Model(EvaluatedSmartPropModel model) => new JsonObject
    {
        ["model"] = ConvertValue(model.ModelName),
        ["elementId"] = ConvertValue(model.ElementId),
        ["transform"] = Matrix(model.Transform),
        ["materialGroup"] = ConvertValue(model.MaterialGroup),
        ["tint"] = model.TintColor is { } tint ? ConvertValue(tint) : null,
        ["deformer"] = model.Deformer is { } deformer ? new JsonObject
        {
            ["size"] = ConvertValue(deformer.Size),
            ["controlPoints"] = ConvertValue(deformer.ControlPoints),
            ["midpoints"] = ConvertValue(deformer.Midpoints),
            ["deformerFrame"] = Matrix(deformer.DeformerFrame),
            ["volumeFrame"] = Matrix(deformer.VolumeFrame),
        } : null,
        ["materialTints"] = new JsonArray((model.MaterialTints ?? []).Select(value => (JsonNode)new JsonObject
        {
            ["material"] = ConvertValue(value.Material),
            ["color"] = ConvertValue(value.Color),
        }).ToArray()),
        ["materialOverrides"] = new JsonArray((model.MaterialOverrides ?? []).Select(value => (JsonNode)new JsonObject
        {
            ["originalMaterial"] = ConvertValue(value.OriginalMaterial),
            ["replacementMaterial"] = ConvertValue(value.ReplacementMaterial),
        }).ToArray()),
    };

    private static JsonArray Matrix(Matrix4x4 matrix) =>
    [
        ConvertValue(matrix.M11), ConvertValue(matrix.M12), ConvertValue(matrix.M13), ConvertValue(matrix.M14),
        ConvertValue(matrix.M21), ConvertValue(matrix.M22), ConvertValue(matrix.M23), ConvertValue(matrix.M24),
        ConvertValue(matrix.M31), ConvertValue(matrix.M32), ConvertValue(matrix.M33), ConvertValue(matrix.M34),
        ConvertValue(matrix.M41), ConvertValue(matrix.M42), ConvertValue(matrix.M43), ConvertValue(matrix.M44),
    ];

    private static object? Value(Element element, string name) => element.ContainsKey(name) ? element[name] : null;

    private static JsonObject Metadata(Element element, HashSet<Guid>? stack = null, string[]? omit = null)
    {
        stack ??= [];
        if (!stack.Add(element.ID))
        {
            return new JsonObject { ["$ref"] = ConvertValue(element.ID.ToString()) };
        }
        var result = new JsonObject { ["$id"] = ConvertValue(element.ID.ToString()), ["$type"] = ConvertValue(element.ClassName) };
        foreach (var (name, value) in element)
        {
            if (omit?.Contains(name) is true)
            {
                continue;
            }
            result[name] = ConvertValue(value, stack);
        }
        stack.Remove(element.ID);
        return result;
    }

    private static JsonNode? ConvertValue(object? value, HashSet<Guid>? stack = null) => value switch
    {
        null => null,
        string text => JsonValue.Create(text, VmapImportJsonContext.Default.String),
        bool boolean => JsonValue.Create(boolean, VmapImportJsonContext.Default.Boolean),
        int number => JsonValue.Create(number, VmapImportJsonContext.Default.Int32),
        long number => JsonValue.Create(number, VmapImportJsonContext.Default.Int64),
        uint number => JsonValue.Create(number, VmapImportJsonContext.Default.UInt32),
        ulong number => ConvertValue(number.ToString(CultureInfo.InvariantCulture)),
        float number => JsonValue.Create(number, VmapImportJsonContext.Default.Single),
        double number => JsonValue.Create(number, VmapImportJsonContext.Default.Double),
        byte number => JsonValue.Create(number, VmapImportJsonContext.Default.Byte),
        byte[] bytes => ConvertValue(Convert.ToBase64String(bytes)),
        Vector2 vector => new JsonArray(ConvertValue(vector.X), ConvertValue(vector.Y)),
        Vector3 vector => new JsonArray(ConvertValue(vector.X), ConvertValue(vector.Y), ConvertValue(vector.Z)),
        Vector4 vector => new JsonArray(ConvertValue(vector.X), ConvertValue(vector.Y), ConvertValue(vector.Z), ConvertValue(vector.W)),
        QAngle angle => new JsonArray(ConvertValue(angle.Pitch), ConvertValue(angle.Yaw), ConvertValue(angle.Roll)),
        Element element when element.ClassName is "CMapWorld" or "CMapMesh" or "CMapEntity"
            or "CMapGroup" or "CMapPrefab" or "CMapSmartProp" or "CMapStaticOverlay" or "CMapInstance" =>
            new JsonObject { ["$ref"] = ConvertValue(element.ID.ToString()) },
        Element element => Metadata(element, stack),
        IDictionary<string, object?> dictionary => new JsonObject(dictionary.Select(pair =>
            new KeyValuePair<string, JsonNode?>(pair.Key, ConvertValue(pair.Value, stack)))),
        IEnumerable array => new JsonArray(array.Cast<object?>().Select(item => ConvertValue(item, stack)).ToArray()),
        _ => ConvertValue(Convert.ToString(value, CultureInfo.InvariantCulture)),
    };
}

[JsonSerializable(typeof(string))]
[JsonSerializable(typeof(bool))]
[JsonSerializable(typeof(byte))]
[JsonSerializable(typeof(int))]
[JsonSerializable(typeof(long))]
[JsonSerializable(typeof(uint))]
[JsonSerializable(typeof(float))]
[JsonSerializable(typeof(double))]
internal sealed partial class VmapImportJsonContext : JsonSerializerContext;
