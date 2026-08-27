using System.Collections.Immutable;
using System.Numerics;
using System.Runtime.InteropServices;

using Datamodel;

namespace Hammer5Tools.Core.Format.Vmap;

/// <summary>
/// Vmap reading experiments: projects an uncompiled <c>.vmap</c> into drawable geometry:
/// brush/displacement meshes triangulated from their half-edge <c>CDmePolygonMesh</c> form,
/// model placements, and SmartProp placements with their per-placement parameter overrides.
///
/// This is a viewer-side projection, not an importer: it flattens the node tree into world
/// space and keeps only what a preview needs.
/// </summary>
public sealed class ValveMapSceneReader
{
    private readonly List<ValveMapSceneMesh> meshes = [];
    private readonly List<ValveMapSceneProp> props = [];
    private readonly List<ValveMapSceneSmartProp> smartProps = [];
    private readonly List<string> diagnostics = [];

    /// <summary>Prefab files currently on the expansion stack, so a self-reference cannot recurse.</summary>
    private readonly HashSet<string> expanding = new(StringComparer.OrdinalIgnoreCase);

    private const int MaximumPrefabDepth = 8;

    /// <summary>Reads <paramref name="path"/> and flattens it into world-space scene items.</summary>
    public ValveMapScene Read(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        var document = VmapDocument.LoadInMemory(path);
        Visit(document.World, Matrix4x4.Identity, document.Path, 0);
        return new ValveMapScene(document.Path, [.. meshes], [.. props], [.. smartProps], [.. diagnostics]);
    }

    private void Visit(Element node, Matrix4x4 parentTransform, string mapPath, int depth)
    {
        // Hammer's per-node hide flag: a viewer that ignored it would show geometry
        // the mapper deliberately took out of view.
        if (Scalar<bool>(node, "force_hidden"))
        {
            return;
        }

        var transform = LocalTransform(node) * parentTransform;

        switch (node.ClassName)
        {
            case "CMapSmartProp":
                AddSmartProp(node, transform);
                break;
            case "CMapEntity":
                AddEntity(node, transform);
                break;
            case "CMapPrefab":
                ExpandPrefab(node, transform, mapPath, depth);
                break;
        }

        // Meshes hang off CMapMesh and CMapStaticOverlay alike, so key on the attribute.
        if (Value(node, "meshData") is Element meshData)
        {
            AddMesh(node.Name ?? node.ClassName, meshData, transform);
        }

        if (Value(node, "children") is ElementArray children)
        {
            foreach (var child in children)
            {
                if (child is not null)
                {
                    Visit(child, transform, mapPath, depth);
                }
            }
        }
    }

    /// <summary>
    /// Draws a prefab reference by reading the map it points at and visiting it under the
    /// prefab's own transform � without it, everything a prefab-composed map contains is missing.
    /// </summary>
    private void ExpandPrefab(Element node, Matrix4x4 transform, string mapPath, int depth)
    {
        var target = Scalar<string>(node, "targetMapPath");
        if (string.IsNullOrWhiteSpace(target))
        {
            return;
        }

        if (depth >= MaximumPrefabDepth)
        {
            diagnostics.Add($"Prefab nesting limit reached at: {target}");
            return;
        }

        var resolved = ResolveContentRelative(mapPath, target);
        if (resolved is null)
        {
            diagnostics.Add($"Prefab not found: {target}");
            return;
        }

        if (!expanding.Add(resolved))
        {
            diagnostics.Add($"Prefab references itself: {target}");
            return;
        }

        try
        {
            Visit(VmapDocument.LoadInMemory(resolved).World, transform, resolved, depth + 1);
        }
        catch (Exception error)
        {
            diagnostics.Add($"Prefab '{target}' could not be read: {error.Message}");
        }
        finally
        {
            expanding.Remove(resolved);
        }
    }

    /// <summary>
    /// A prefab path is relative to the addon's content root, which is not handed to the
    /// reader � so walk up from the referencing map until the relative path resolves.
    /// </summary>
    private static string? ResolveContentRelative(string mapPath, string relativePath)
    {
        var normalized = relativePath.Replace('\\', '/').TrimStart('/');
        var directory = Path.GetDirectoryName(Path.GetFullPath(mapPath));
        while (directory is not null)
        {
            var candidate = Path.Combine(directory, normalized);
            if (File.Exists(candidate))
            {
                return Path.GetFullPath(candidate);
            }
            directory = Path.GetDirectoryName(directory);
        }
        return null;
    }

    private void AddEntity(Element node, Matrix4x4 transform)
    {
        if (Value(node, "entity_properties") is not Element properties)
        {
            return;
        }

        var model = Scalar<string>(properties, "model");
        if (string.IsNullOrWhiteSpace(model))
        {
            return;
        }

        props.Add(new ValveMapSceneProp(
            node.Name ?? "",
            Scalar<string>(properties, "classname") ?? "",
            model,
            Flatten(transform)));
    }

    private void AddSmartProp(Element node, Matrix4x4 transform)
    {
        var file = Scalar<string>(node, "smartPropFilename");
        if (string.IsNullOrWhiteSpace(file))
        {
            return;
        }

        smartProps.Add(new ValveMapSceneSmartProp(
            node.Name ?? "", file, Flatten(transform), ReadParameters(node)));
    }

    /// <summary>
    /// The placement's parameter overrides, as <c>{variable name: value}</c>. Hammer stores each
    /// under <c>nodeData/parameters/values[i]/value</c>; a resource-typed override nests its
    /// string one level deeper under <c>value_with_specific_type</c>.
    /// </summary>
    private static Dictionary<string, object?> ReadParameters(Element node)
    {
        var overrides = new Dictionary<string, object?>(StringComparer.Ordinal);
        if (Value(node, "nodeData") is not Element nodeData
            || Value(nodeData, "parameters") is not Element parameters
            || Value(parameters, "values") is not ElementArray values)
        {
            return overrides;
        }

        foreach (var entry in values)
        {
            if (entry is null
                || Value(entry, "value") is not Element parameter
                || Value(parameter, "parameterName") is not string name
                || string.IsNullOrEmpty(name))
            {
                continue;
            }

            var value = Value(parameter, "value");
            if (value is Element typed)
            {
                value = Value(typed, "value");
            }
            overrides[name] = value;
        }

        return overrides;
    }

    private void AddMesh(string name, Element meshData, Matrix4x4 transform)
    {
        var positions = StreamData(meshData, "vertexData", "position") as Vector3Array;
        var vertexDataIndices = Value(meshData, "vertexDataIndices") as IntArray;
        var edgeVertexIndices = Value(meshData, "edgeVertexIndices") as IntArray;
        var edgeNextIndices = Value(meshData, "edgeNextIndices") as IntArray;
        var edgeVertexDataIndices = Value(meshData, "edgeVertexDataIndices") as IntArray;
        var faceEdgeIndices = Value(meshData, "faceEdgeIndices") as IntArray;
        if (positions is null || vertexDataIndices is null || edgeVertexIndices is null
            || edgeNextIndices is null || faceEdgeIndices is null)
        {
            diagnostics.Add($"Mesh '{name}' is missing its polygon-mesh topology.");
            return;
        }

        var texcoords = StreamData(meshData, "faceVertexData", "texcoord") as Vector2Array;
        var normals = StreamData(meshData, "faceVertexData", "normal") as Vector3Array;
        var faceDataIndices = Value(meshData, "faceDataIndices") as IntArray;
        var materialIndices = StreamData(meshData, "faceData", "materialindex") as IntArray;
        var materials = Value(meshData, "materials") as StringArray;

        // One vertex per face corner: UVs and normals are per corner, so sharing
        // positions between faces would need a split pass for no visual gain.
        var vertices = new List<Vector3>();
        var vertexNormals = new List<Vector3>();
        var vertexTexcoords = new List<Vector2>();
        var trianglesByMaterial = new Dictionary<string, List<uint>>(StringComparer.Ordinal);

        var loop = new List<int>();
        for (var face = 0; face < faceEdgeIndices.Count; face++)
        {
            loop.Clear();
            var start = faceEdgeIndices[face];
            if (start < 0 || start >= edgeNextIndices.Count)
            {
                continue;
            }

            var edge = start;
            do
            {
                loop.Add(edge);
                edge = edgeNextIndices[edge];
                // A corrupt ring would otherwise spin forever.
            }
            while (edge != start && edge >= 0 && edge < edgeNextIndices.Count && loop.Count <= edgeNextIndices.Count);

            if (loop.Count < 3)
            {
                continue;
            }

            var first = (uint)vertices.Count;
            foreach (var halfEdge in loop)
            {
                var vertex = edgeVertexIndices[halfEdge];
                vertices.Add(Vector3.Transform(positions[vertexDataIndices[vertex]], transform));
                var corner = edgeVertexDataIndices is null ? -1 : edgeVertexDataIndices[halfEdge];
                vertexTexcoords.Add(texcoords is not null && corner >= 0 && corner < texcoords.Count
                    ? texcoords[corner]
                    : Vector2.Zero);
                // ponytail: rotation only, so a non-uniformly scaled brush gets slightly
                // wrong shading; swap in the inverse-transpose if that ever shows.
                vertexNormals.Add(normals is not null && corner >= 0 && corner < normals.Count
                    ? Vector3.TransformNormal(normals[corner], transform)
                    : Vector3.Zero);
            }

            // Hammer writes zeroed normals for some corners; Newell's method over the
            // face loop is the reliable fallback and matches the winding.
            FillMissingNormals(vertices, vertexNormals, (int)first, loop.Count);

            var material = MaterialOf(face, faceDataIndices, materialIndices, materials);
            var triangles = trianglesByMaterial.TryGetValue(material, out var existing)
                ? existing
                : trianglesByMaterial[material] = [];
            for (var corner = 1; corner < loop.Count - 1; corner++)
            {
                triangles.Add(first);
                triangles.Add(first + (uint)corner);
                triangles.Add(first + (uint)corner + 1);
            }
        }

        if (vertices.Count == 0)
        {
            return;
        }

        var indices = new List<uint>();
        var subMeshes = new List<ValveMapSceneSubMesh>();
        foreach (var (material, triangles) in trianglesByMaterial)
        {
            subMeshes.Add(new ValveMapSceneSubMesh(indices.Count, triangles.Count, material));
            indices.AddRange(triangles);
        }

        meshes.Add(new ValveMapSceneMesh(
            name, Flatten(vertices), Flatten(vertexNormals), Flatten(vertexTexcoords),
            [.. indices], [.. subMeshes]));
    }

    private static void FillMissingNormals(List<Vector3> vertices, List<Vector3> normals, int offset, int count)
    {
        var missing = false;
        for (var index = offset; index < offset + count; index++)
        {
            if (normals[index].LengthSquared() < 1e-12f)
            {
                missing = true;
                break;
            }
        }

        if (!missing)
        {
            return;
        }

        var newell = Vector3.Zero;
        for (var index = 0; index < count; index++)
        {
            var current = vertices[offset + index];
            var next = vertices[offset + (index + 1) % count];
            newell += new Vector3(
                (current.Y - next.Y) * (current.Z + next.Z),
                (current.Z - next.Z) * (current.X + next.X),
                (current.X - next.X) * (current.Y + next.Y));
        }

        var normal = newell.LengthSquared() < 1e-12f ? Vector3.UnitZ : Vector3.Normalize(newell);
        for (var index = offset; index < offset + count; index++)
        {
            if (normals[index].LengthSquared() < 1e-12f)
            {
                normals[index] = normal;
            }
        }
    }

    private static string MaterialOf(int face, IntArray? faceDataIndices, IntArray? materialIndices, StringArray? materials)
    {
        if (materials is null || materialIndices is null)
        {
            return "";
        }

        var dataIndex = faceDataIndices is not null && face < faceDataIndices.Count ? faceDataIndices[face] : face;
        if (dataIndex < 0 || dataIndex >= materialIndices.Count)
        {
            return "";
        }

        var materialIndex = materialIndices[dataIndex];
        return materialIndex >= 0 && materialIndex < materials.Count ? materials[materialIndex] ?? "" : "";
    }

    /// <summary>The <c>data</c> array of the named stream inside one of the mesh's data arrays.</summary>
    private static object? StreamData(Element meshData, string arrayName, string streamName)
    {
        if (Value(meshData, arrayName) is not Element array || Value(array, "streams") is not ElementArray streams)
        {
            return null;
        }

        foreach (var stream in streams)
        {
            if (stream is not null
                && Value(stream, "standardAttributeName") is string name
                && name == streamName)
            {
                return Value(stream, "data");
            }
        }

        return null;
    }

    /// <summary>
    /// The node's own transform, in the row-vector convention the viewport uses
    /// (translation in the last row), from Source's pitch=Y, yaw=Z, roll=X angles.
    /// </summary>
    private static Matrix4x4 LocalTransform(Element node)
    {
        var origin = Value(node, "origin") is Vector3 position ? position : Vector3.Zero;
        var scales = Value(node, "scales") is Vector3 scale ? scale : Vector3.One;
        var pitch = 0f;
        var yaw = 0f;
        var roll = 0f;
        if (Value(node, "angles") is QAngle angles)
        {
            pitch = float.DegreesToRadians(angles.Pitch);
            yaw = float.DegreesToRadians(angles.Yaw);
            roll = float.DegreesToRadians(angles.Roll);
        }

        return Matrix4x4.CreateScale(scales)
            * Matrix4x4.CreateRotationX(roll)
            * Matrix4x4.CreateRotationY(pitch)
            * Matrix4x4.CreateRotationZ(yaw)
            * Matrix4x4.CreateTranslation(origin);
    }

    private static T? Scalar<T>(Element node, string name) => Value(node, name) is T value ? value : default;

    /// <summary>The named attribute, or null � <c>Element</c>'s indexer throws on a missing key.</summary>
    private static object? Value(Element node, string name) => node.ContainsKey(name) ? node[name] : null;

    private static ImmutableArray<float> Flatten(Matrix4x4 matrix) =>
    [
        matrix.M11, matrix.M12, matrix.M13, matrix.M14,
        matrix.M21, matrix.M22, matrix.M23, matrix.M24,
        matrix.M31, matrix.M32, matrix.M33, matrix.M34,
        matrix.M41, matrix.M42, matrix.M43, matrix.M44,
    ];

    private static ImmutableArray<float> Flatten(List<Vector3> values)
    {
        var result = new float[values.Count * 3];
        for (var index = 0; index < values.Count; index++)
        {
            result[index * 3] = values[index].X;
            result[index * 3 + 1] = values[index].Y;
            result[index * 3 + 2] = values[index].Z;
        }
        return ImmutableCollectionsMarshal.AsImmutableArray(result);
    }

    private static ImmutableArray<float> Flatten(List<Vector2> values)
    {
        var result = new float[values.Count * 2];
        for (var index = 0; index < values.Count; index++)
        {
            result[index * 2] = values[index].X;
            result[index * 2 + 1] = values[index].Y;
        }
        return ImmutableCollectionsMarshal.AsImmutableArray(result);
    }
}
