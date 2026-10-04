using System.Numerics;
using System.Text.Json.Nodes;
using Datamodel;
using Hammer5Tools.Core.Format.Vmap;
using DM = Datamodel.Datamodel;

namespace SourcePorter.Core.Tests;

public sealed class ValveMapImportReaderTests
{
    [Fact]
    public void Read_retains_polygon_corners_hidden_hierarchy_sets_and_subdivision_without_changing_preview()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"h5t_import_{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        try
        {
            var path = Path.Combine(directory, "test.vmap");
            var document = new DM("vmap", 29);
            var root = new Element(document, "", null, "CMapRootElement");
            document.Root = root;
            var world = new Element(document, "world", null, "CMapWorld");
            root["world"] = world;
            var group = new Element(document, "group", null, "CMapGroup")
            {
                ["origin"] = new Vector3(10, 20, 30),
                ["force_hidden"] = true,
            };
            world["children"] = new ElementArray { group };
            var node = new Element(document, "quad", null, "CMapMesh")
            {
                ["nodeID"] = 12,
                ["referenceID"] = ulong.MaxValue,
                ["scales"] = new Vector3(2, 1, 1),
                ["meshData"] = Quad(document),
            };
            group["children"] = new ElementArray { node };
            var set = new Element(document, "", null, "CMapSelectionSet")
            {
                ["selectionSetName"] = "Walls",
                ["selectionSetData"] = new Element(document, "", null, "DmElement")
                {
                    ["nodes"] = new ElementArray { group },
                },
            };
            root["rootSelectionSet"] = new Element(document, "", null, "CMapSelectionSet")
            {
                ["children"] = new ElementArray { set },
            };
            document.Save(path, "keyvalues2", 4);

            var reader = new ValveMapImportReader();
            var scene = JsonNode.Parse(reader.Read(path))!;
            var imported = scene["nodes"]![2]!;
            Assert.True(imported["hidden"]!.GetValue<bool>());
            Assert.Equal(scene["nodes"]![1]!["id"]!.GetValue<string>(), imported["parent"]!.GetValue<string>());
            Assert.Equal("18446744073709551615", imported["referenceId"]!.GetValue<string>());
            Assert.Equal(10f, imported["transform"]![12]!.GetValue<float>());
            var face = Assert.Single(imported["mesh"]!["faces"]!.AsArray())!;
            Assert.Equal(4, face["indices"]!.AsArray().Count);
            Assert.Equal(4, face["uvs"]!.AsArray().Count);
            Assert.Equal("materials/grid.vmat", face["material"]!.GetValue<string>());
            Assert.Equal(0.25f, face["uvs"]![0]![0]!.GetValue<float>());
            var sets = scene["selectionSets"]![0]!["data"]!["children"]![0]!;
            Assert.Equal(group.ID.ToString(), sets["selectionSetData"]!["nodes"]![0]!["$ref"]!.GetValue<string>());
            Assert.Single(scene["diagnostics"]!.AsArray());
            Assert.NotNull(imported["mesh"]!["metadata"]!["subdivisionData"]);
            Assert.Empty(new ValveMapSceneReader().Read(path).Meshes);
            Assert.Equal(3, JsonNode.Parse(reader.Read(path))!["nodes"]!.AsArray().Count);

            // A ring that cycles without returning to its starting edge must fail boundedly.
            var topology = (Element)node["meshData"]!;
            topology["edgeNextIndices"] = new IntArray { 0, 0, 0, 0 };
            topology["faceEdgeIndices"] = new IntArray { 1 };
            document.Save(path, "keyvalues2", 4);
            scene = JsonNode.Parse(reader.Read(path))!;
            Assert.Null(scene["nodes"]![2]!["mesh"]);
            Assert.Contains("broken half-edge ring", scene["diagnostics"]![0]!.GetValue<string>(), StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    private static Element Quad(DM document)
    {
        Element Stream(string name, object values) => new(document, "", null, "CDmePolygonMeshDataStream")
        {
            ["standardAttributeName"] = name,
            ["data"] = values,
        };
        Element Data(params Element[] streams) => new(document, "", null, "CDmePolygonMeshDataArray")
        {
            ["streams"] = new ElementArray(streams),
        };
        return new Element(document, "", null, "CDmePolygonMesh")
        {
            ["vertexDataIndices"] = new IntArray { 0, 1, 2, 3 },
            ["edgeVertexIndices"] = new IntArray { 0, 1, 2, 3 },
            ["edgeNextIndices"] = new IntArray { 1, 2, 3, 0 },
            ["edgeVertexDataIndices"] = new IntArray { 0, 1, 2, 3 },
            ["faceEdgeIndices"] = new IntArray { 0 },
            ["faceDataIndices"] = new IntArray { 0 },
            ["materials"] = new StringArray { "materials/grid.vmat" },
            ["vertexData"] = Data(Stream("position", new Vector3Array { new(0, 0, 0), new(1, 0, 0), new(1, 1, 0), new(0, 1, 0) })),
            ["faceVertexData"] = Data(Stream("texcoord", new Vector2Array { new(0.25f, 0.5f), new(1, 0), new(1, 1), new(0, 1) })),
            ["faceData"] = Data(Stream("materialindex", new IntArray { 0 })),
            ["subdivisionData"] = new Element(document, "", null, "CDmePolygonMeshSubdivisionData")
            {
                ["subdivisionLevels"] = new IntArray { 1, 1, 1, 1 },
                ["streams"] = new ElementArray(),
            },
        };
    }
}
