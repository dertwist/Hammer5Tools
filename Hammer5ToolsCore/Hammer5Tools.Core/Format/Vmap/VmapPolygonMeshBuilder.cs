using System.Numerics;

using Datamodel;
using DM = Datamodel.Datamodel;

namespace Hammer5Tools.Core.Format.Vmap;

/// <summary>Builds Hammer-compatible polygon mesh nodes from convex faces.</summary>
internal static class VmapPolygonMeshBuilder
{
    private sealed class MeshTopology
    {
        public List<Vector3> Positions { get; } = [];

        public List<Vector2> Texcoords { get; } = [];

        public List<Vector3> Normals { get; } = [];

        public List<Vector4> Tangents { get; } = [];

        public List<int> VertexEdgeIndices { get; } = [];

        public List<int> VertexDataIndices { get; } = [];

        public List<int> EdgeVertexIndices { get; } = [];

        public List<int> EdgeOppositeIndices { get; } = [];

        public List<int> EdgeNextIndices { get; } = [];

        public List<int> EdgeFaceIndices { get; } = [];

        public List<int> EdgeDataIndices { get; } = [];

        public List<int> EdgeVertexDataIndices { get; } = [];

        public List<int> FaceEdgeIndices { get; } = [];

        public List<int> FaceDataIndices { get; } = [];

        public List<int> EdgeFlags { get; } = [];
    }

    public static Element Build(
        DM document,
        IReadOnlyList<IReadOnlyList<Vector3>> faces,
        string materialPath,
        int nodeId,
        string name)
    {
        ArgumentNullException.ThrowIfNull(document);
        ArgumentNullException.ThrowIfNull(faces);
        ArgumentException.ThrowIfNullOrWhiteSpace(materialPath);

        if (faces.Count == 0)
            throw new ArgumentException("At least one face is required.", nameof(faces));

        var topology = BuildIndependentTopology(faces);
        var positions = topology.Positions;
        var texcoords = topology.Texcoords;
        var normals = topology.Normals;
        var tangents = topology.Tangents;
        var vertexEdgeIndices = topology.VertexEdgeIndices;
        var vertexDataIndices = topology.VertexDataIndices;
        var edgeVertexIndices = topology.EdgeVertexIndices;
        var edgeOppositeIndices = topology.EdgeOppositeIndices;
        var edgeNextIndices = topology.EdgeNextIndices;
        var edgeFaceIndices = topology.EdgeFaceIndices;
        var edgeDataIndices = topology.EdgeDataIndices;
        var edgeVertexDataIndices = topology.EdgeVertexDataIndices;
        var faceEdgeIndices = topology.FaceEdgeIndices;
        var faceDataIndices = topology.FaceDataIndices;
        var edgeFlags = topology.EdgeFlags;

        var vertexData = DataArray(document, positions.Count,
        [
            Vector3Stream(document, "position", positions),
        ]);
        var faceVertexData = DataArray(document, texcoords.Count,
        [
            Vector2Stream(document, "texcoord", texcoords),
            Vector3Stream(document, "normal", normals),
            Vector4Stream(document, "tangent", tangents),
        ]);
        var edgeData = DataArray(document, edgeFlags.Count,
        [
            IntStream(document, "flags", edgeFlags, 3),
        ]);
        var faceData = DataArray(document, faces.Count,
        [
            Vector2Stream(document, "textureScale", Enumerable.Repeat(new Vector2(0.25f, 0.25f), faces.Count)),
            Vector4Stream(document, "textureAxisU", Enumerable.Repeat(new Vector4(1, 0, 0, 0), faces.Count)),
            Vector4Stream(document, "textureAxisV", Enumerable.Repeat(new Vector4(0, -1, 0, 512), faces.Count)),
            IntStream(document, "materialindex", Enumerable.Repeat(0, faces.Count), 8),
            IntStream(document, "flags", Enumerable.Repeat(0, faces.Count), 3),
            IntStream(document, "lightmapScaleBias", Enumerable.Repeat(0, faces.Count), 1),
        ]);

        var subdivision = Create(document, "CDmePolygonMeshSubdivisionData");
        subdivision["subdivisionLevels"] = Integers(Enumerable.Repeat(0, edgeVertexIndices.Count));
        subdivision["streams"] = new ElementArray();

        var meshData = Create(document, "CDmePolygonMesh", "meshData");
        meshData["vertexEdgeIndices"] = Integers(vertexEdgeIndices);
        meshData["vertexDataIndices"] = Integers(vertexDataIndices);
        meshData["edgeVertexIndices"] = Integers(edgeVertexIndices);
        meshData["edgeOppositeIndices"] = Integers(edgeOppositeIndices);
        meshData["edgeNextIndices"] = Integers(edgeNextIndices);
        meshData["edgeFaceIndices"] = Integers(edgeFaceIndices);
        meshData["edgeDataIndices"] = Integers(edgeDataIndices);
        meshData["edgeVertexDataIndices"] = Integers(edgeVertexDataIndices);
        meshData["faceEdgeIndices"] = Integers(faceEdgeIndices);
        meshData["faceDataIndices"] = Integers(faceDataIndices);
        meshData["materials"] = new StringArray { materialPath };
        meshData["vertexData"] = vertexData;
        meshData["faceVertexData"] = faceVertexData;
        meshData["edgeData"] = edgeData;
        meshData["faceData"] = faceData;
        meshData["subdivisionData"] = subdivision;

        var transformPin = Create(document, "DmElement", "transformPin");
        transformPin["referenceName"] = "";
        transformPin["targetReferenceID"] = 0UL;
        transformPin["offsetOrigin"] = Vector3.Zero;
        transformPin["offsetAngles"] = new QAngle(0, 0, 0);
        transformPin["pinAngles"] = true;
        transformPin["twoWay"] = false;

        var mesh = Create(document, "CMapMesh", name);
        mesh["nodeID"] = nodeId;
        mesh["referenceID"] = RandomReferenceId();
        mesh["children"] = new ElementArray();
        mesh["variableTargetKeys"] = new StringArray();
        mesh["variableNames"] = new StringArray();
        mesh["meshData"] = meshData;
        mesh["origin"] = Vector3.Zero;
        mesh["angles"] = new QAngle(0, 0, 0);
        mesh["scales"] = Vector3.One;
        mesh["transformLocked"] = false;
        mesh["transformPin"] = transformPin;
        mesh["force_hidden"] = false;
        mesh["editorOnly"] = false;
        mesh["customVisGroup"] = "";
        mesh["randomSeed"] = 0;
        mesh["disableShadows"] = 0;
        mesh["bakelighting"] = false;
        mesh["cubeMapName"] = "";
        mesh["emissiveLightingEnabled"] = true;
        mesh["emissiveLightingBoost"] = 1f;
        mesh["lightingDummy"] = false;
        mesh["bakeLightDoubleSided"] = false;
        mesh["visexclude"] = false;
        mesh["disablemerging"] = false;
        mesh["renderwithdynamic"] = false;
        mesh["renderToCubemaps"] = false;
        mesh["keep_vertices"] = true;
        mesh["fademindist"] = -1f;
        mesh["fademaxdist"] = 0f;
        mesh["disableHeightDisplacement"] = true;
        mesh["smoothingAngle"] = 40f;
        mesh["tintColor"] = new Color(255, 255, 255, 255);
        mesh["renderAmt"] = 255;
        mesh["physicsType"] = "none";
        mesh["physicsCollisionProperty"] = "";
        mesh["physicsGroup"] = "";
        mesh["physicsInteractsAs"] = "";
        mesh["physicsInteractsWith"] = "";
        mesh["physicsInteractsExclude"] = "";
        mesh["physicsIncludedDetailLayers"] = new ElementArray();
        mesh["physicsMissingDetailLayers"] = new ElementArray();
        mesh["physicsSimplificationOverride"] = false;
        mesh["physicsSimplificationError"] = 0f;
        return mesh;
    }

    private static MeshTopology BuildIndependentTopology(IReadOnlyList<IReadOnlyList<Vector3>> faces)
    {
        var topology = new MeshTopology();
        for (var faceIndex = 0; faceIndex < faces.Count; faceIndex++)
        {
            var face = UpwardFace(faces[faceIndex], faceIndex);
            var vertexStart = topology.Positions.Count;
            var halfEdgeStart = topology.EdgeVertexIndices.Count;
            var edgeStart = topology.EdgeFlags.Count;
            var normal = FaceNormal(face);
            var tangent = Tangent(normal);

            for (var cornerIndex = 0; cornerIndex < face.Count; cornerIndex++)
            {
                var position = face[cornerIndex];
                var nextCorner = (cornerIndex + 1) % face.Count;
                var previousCorner = (cornerIndex + face.Count - 1) % face.Count;
                var interiorEdge = halfEdgeStart + (cornerIndex * 2);
                var boundaryEdge = interiorEdge + 1;

                topology.Positions.Add(position);
                topology.VertexEdgeIndices.Add(interiorEdge);
                topology.VertexDataIndices.Add(vertexStart + cornerIndex);
                topology.EdgeVertexIndices.Add(vertexStart + nextCorner);
                topology.EdgeVertexIndices.Add(vertexStart + cornerIndex);
                topology.EdgeOppositeIndices.Add(boundaryEdge);
                topology.EdgeOppositeIndices.Add(interiorEdge);
                topology.EdgeNextIndices.Add(halfEdgeStart + (nextCorner * 2));
                topology.EdgeNextIndices.Add(halfEdgeStart + (previousCorner * 2) + 1);
                topology.EdgeFaceIndices.Add(faceIndex);
                topology.EdgeFaceIndices.Add(-1);
                topology.EdgeDataIndices.Add(edgeStart + cornerIndex);
                topology.EdgeDataIndices.Add(edgeStart + cornerIndex);
                topology.EdgeVertexDataIndices.Add(interiorEdge);
                topology.EdgeVertexDataIndices.Add(boundaryEdge);

                var nextPosition = face[nextCorner];
                AddFaceVertex(topology, nextPosition, normal, tangent);
                AddBoundaryVertex(topology);
                topology.EdgeFlags.Add(0);
            }

            topology.FaceEdgeIndices.Add(halfEdgeStart + ((face.Count - 1) * 2));
            topology.FaceDataIndices.Add(faceIndex);
        }
        return topology;
    }

    private static IReadOnlyList<Vector3> UpwardFace(IReadOnlyList<Vector3> sourceFace, int faceIndex)
    {
        if (sourceFace.Count < 3)
            throw new InvalidDataException($"Face {faceIndex} has fewer than three vertices.");
        return FaceNormal(sourceFace).Z < 0f
            ? sourceFace.Reverse().ToArray()
            : sourceFace;
    }

    private static void AddFaceVertex(
        MeshTopology topology,
        Vector3 position,
        Vector3 normal,
        Vector4 tangent)
    {
        topology.Texcoords.Add(new Vector2(position.X / 128f, -position.Y / 128f));
        topology.Normals.Add(normal);
        topology.Tangents.Add(tangent);
    }

    private static void AddBoundaryVertex(MeshTopology topology)
    {
        topology.Texcoords.Add(Vector2.Zero);
        topology.Normals.Add(Vector3.Zero);
        topology.Tangents.Add(Vector4.Zero);
    }

    private static Vector3 FaceNormal(IReadOnlyList<Vector3> face)
    {
        for (var index = 1; index < face.Count - 1; index++)
        {
            var cross = Vector3.Cross(face[index] - face[0], face[index + 1] - face[0]);
            if (cross.LengthSquared() > 0.000001f)
                return Vector3.Normalize(cross);
        }

        return Vector3.UnitZ;
    }

    private static Vector4 Tangent(Vector3 normal)
    {
        var axis = MathF.Abs(Vector3.Dot(normal, Vector3.UnitZ)) > 0.99f
            ? Vector3.UnitX
            : Vector3.Normalize(Vector3.Cross(Vector3.UnitZ, normal));
        return new Vector4(axis, -1f);
    }

    private static Element DataArray(DM document, int size, IEnumerable<Element> streams)
    {
        var array = Create(document, "CDmePolygonMeshDataArray");
        array["size"] = size;
        var values = new ElementArray();
        foreach (var stream in streams)
            values.Add(stream);
        array["streams"] = values;
        return array;
    }

    private static Element Stream(DM document, string name, int flags = 1)
    {
        var stream = Create(document, "CDmePolygonMeshDataStream", $"{name}:0");
        stream["standardAttributeName"] = name;
        stream["semanticName"] = name;
        stream["semanticIndex"] = 0;
        stream["vertexBufferLocation"] = 0;
        stream["dataStateFlags"] = flags;
        return stream;
    }

    private static Element IntStream(DM document, string name, IEnumerable<int> values, int flags)
    {
        var stream = Stream(document, name, flags);
        stream["data"] = Integers(values);
        return stream;
    }

    private static Element Vector2Stream(DM document, string name, IEnumerable<Vector2> values)
    {
        var stream = Stream(document, name);
        var array = new Vector2Array();
        foreach (var value in values)
            array.Add(value);
        stream["data"] = array;
        return stream;
    }

    private static Element Vector3Stream(DM document, string name, IEnumerable<Vector3> values)
    {
        var stream = Stream(document, name);
        var array = new Vector3Array();
        foreach (var value in values)
            array.Add(value);
        stream["data"] = array;
        return stream;
    }

    private static Element Vector4Stream(DM document, string name, IEnumerable<Vector4> values)
    {
        var stream = Stream(document, name);
        var array = new Vector4Array();
        foreach (var value in values)
            array.Add(value);
        stream["data"] = array;
        return stream;
    }

    private static IntArray Integers(IEnumerable<int> values)
    {
        var array = new IntArray();
        foreach (var value in values)
            array.Add(value);
        return array;
    }

    private static Element Create(DM document, string className, string name = "") =>
        new(document, name, null, className);

    private static ulong RandomReferenceId()
    {
        Span<byte> bytes = stackalloc byte[sizeof(ulong)];
        Random.Shared.NextBytes(bytes);
        return BitConverter.ToUInt64(bytes);
    }
}
