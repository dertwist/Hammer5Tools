using System.Collections;
using System.Globalization;
using System.Numerics;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using Datamodel;
using Hammer5Tools.Core.Format.SmartProps;
using Hammer5Tools.Core.IO.CompiledResource;

namespace Hammer5Tools.Core.Format.Vmap;

/// <summary>Reads editable polygons, hierarchy, editor metadata and evaluated SmartProp placements for DCC import.</summary>
public sealed class ValveMapImportReader
{
    private readonly JsonArray nodes = [];
    private readonly JsonArray selectionSets = [];
    private readonly JsonArray diagnostics = [];
    private readonly HashSet<string> expanding = new(StringComparer.OrdinalIgnoreCase);
    private VmapContentFiles files = null!;

    /// <summary>Returns schema version 1 JSON. Create a reader for each import.</summary>
    public string Read(string path, string? contentRoot = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        nodes.Clear();
        selectionSets.Clear();
        diagnostics.Clear();
        expanding.Clear();
        files = new VmapContentFiles(path, contentRoot);
        VisitMap(path, Matrix4x4.Identity, "", false, 0);
        return new JsonObject
        {
            ["schemaVersion"] = ConvertValue(1),
            ["path"] = ConvertValue(Path.GetFullPath(path)),
            ["nodes"] = nodes.DeepClone(),
            ["selectionSets"] = selectionSets.DeepClone(),
            ["diagnostics"] = diagnostics.DeepClone(),
        }.ToJsonString(VmapImportJsonContext.Default.Options);
    }

    private void VisitMap(string path, Matrix4x4 transform, string parent, bool hidden, int depth)
    {
        path = Path.GetFullPath(path);
        if (depth >= 32 || !expanding.Add(path))
        {
            diagnostics.Add(ConvertValue($"Prefab cycle or nesting limit: {path}"));
            return;
        }
        try
        {
            var document = VmapDocument.LoadInMemory(path);
            var scope = parent;
            if (Value(document.Root, "rootSelectionSet") is Element rootSets)
            {
                selectionSets.Add(new JsonObject { ["scope"] = ConvertValue(scope), ["data"] = Metadata(rootSets) });
            }
            Visit(document.World, transform, parent, hidden, path, depth, scope, new HashSet<Guid>());
        }
        finally
        {
            expanding.Remove(path);
        }
    }

    private void Visit(Element node, Matrix4x4 parentTransform, string parent, bool parentHidden,
        string mapPath, int depth, string scope, HashSet<Guid> ancestors)
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
            var hidden = parentHidden || Value(node, "force_hidden") is true;
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
                ["transform"] = Matrix(transform),
                ["properties"] = properties is null ? new JsonObject() : Metadata(properties),
                ["metadata"] = Metadata(node, omit: ["children", "meshData", "entity_properties"]),
            };
            nodes.Add(item);
            if (Value(node, "meshData") is Element mesh)
            {
                try
                {
                    item["mesh"] = ReadMesh(mesh);
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
                try
                {
                    var document = files.ReadSmartProp(smartProp, out var nested);
                    var overrides = ValveMapSceneReader.ReadParameters(node);
                    item["variables"] = ConvertValue(overrides);
                    if (document["m_Variables"] is JsonArray variables)
                    {
                        foreach (var variable in variables.OfType<JsonObject>())
                        {
                            var name = variable["m_VariableName"]?.GetValue<string>();
                            if (name is not null && overrides.TryGetValue(name, out var value))
                            {
                                variable["m_DefaultValue"] = ConvertValue(value);
                            }
                        }
                    }
                    var result = SmartPropEvaluator.EvaluateJson(document.ToJsonString(VmapImportJsonContext.Default.Options), nested.ToJsonString());
                    item["smartPropModels"] = new JsonArray(result.Models.Select(Model).ToArray());
                    foreach (var diagnostic in result.Diagnostics)
                    {
                        diagnostics.Add(ConvertValue($"{smartProp}: {diagnostic.Code}: {diagnostic.Message}"));
                    }
                }
                catch (Exception error) when (error is IOException or System.Text.Json.JsonException or InvalidOperationException)
                {
                    diagnostics.Add(ConvertValue($"{smartProp}: {error.Message}"));
                }
            }
            if (Value(node, "children") is ElementArray children)
            {
                foreach (var child in children)
                {
                    if (child is not null)
                    {
                        Visit(child, transform, id, hidden, mapPath, depth, scope, ancestors);
                    }
                }
            }
            if (node.ClassName == "CMapPrefab" && Value(node, "targetMapPath") is string target)
            {
                var resolved = files.Resolve(target, mapPath);
                if (resolved is null)
                {
                    diagnostics.Add(ConvertValue($"Prefab not found: {target}"));
                }
                else
                {
                    try
                    {
                        VisitMap(resolved, transform, id, hidden, depth + 1);
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

    private static JsonObject ReadMesh(Element mesh)
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
        return new JsonObject { ["points"] = points, ["faces"] = faces, ["metadata"] = Metadata(mesh) };
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
            or "CMapGroup" or "CMapPrefab" or "CMapSmartProp" or "CMapStaticOverlay" =>
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
