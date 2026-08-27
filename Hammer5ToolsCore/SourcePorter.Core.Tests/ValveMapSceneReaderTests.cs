using System.Numerics;

using Datamodel;
using Hammer5Tools.Core.Format.Vmap;
using DM = Datamodel.Datamodel;

namespace SourcePorter.Core.Tests;

public sealed class ValveMapSceneReaderTests
{
    [Fact]
    public void Read_tessellates_meshes_and_flattens_placements_into_world_space()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"h5t_vmap_scene_{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, "scene.vmap");
        try
        {
            WriteMap(path);

            var scene = new ValveMapSceneReader().Read(path);

            var mesh = Assert.Single(scene.Meshes);
            // One quad face -> one fan of two triangles over four corner vertices.
            Assert.Equal(4 * 3, mesh.Positions.Length);
            Assert.Equal<uint>([0, 1, 2, 0, 2, 3], mesh.Indices.ToArray());
            var submesh = Assert.Single(mesh.SubMeshes);
            Assert.Equal("materials/dev/grid.vmat", submesh.Material);
            Assert.Equal(6, submesh.IndexCount);
            // The mesh node sits at z=32, so its baked corners do too.
            Assert.Equal<float>([0, 0, 32, 16, 0, 32, 16, 16, 32, 0, 16, 32], mesh.Positions.ToArray());
            Assert.All(Enumerable.Range(0, 4), corner =>
                Assert.Equal(1f, mesh.Normals[corner * 3 + 2]));

            var prop = Assert.Single(scene.Props);
            Assert.Equal("prop_static", prop.ClassName);
            Assert.Equal("models/example.vmdl", prop.Model);
            // Group at (100,0,0) times the entity's own (0,50,0): translation is the last row.
            Assert.Equal<float>([100, 50, 0], prop.Transform[12..15].ToArray());

            var smartProp = Assert.Single(scene.SmartProps);
            Assert.Equal("smartprops/example.vsmart", smartProp.File);
            Assert.Equal(4f, smartProp.Variables["length"]);
            Assert.Equal("models/fence.vmdl", smartProp.Variables["column"]);
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    [Fact]
    public void Read_skips_hidden_nodes()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"h5t_vmap_scene_{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, "hidden.vmap");
        try
        {
            WriteMap(path, hidden: true);

            var scene = new ValveMapSceneReader().Read(path);

            Assert.Empty(scene.Meshes);
            Assert.Empty(scene.Props);
            Assert.Empty(scene.SmartProps);
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    [Fact]
    public void Read_expands_prefabs_relative_to_the_content_root()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"h5t_vmap_scene_{Guid.NewGuid():N}");
        var maps = Path.Combine(directory, "maps");
        Directory.CreateDirectory(maps);
        try
        {
            WriteMap(Path.Combine(maps, "target.vmap"));
            WritePrefabHost(Path.Combine(maps, "host.vmap"), "maps/target.vmap");

            var scene = new ValveMapSceneReader().Read(Path.Combine(maps, "host.vmap"));

            var mesh = Assert.Single(scene.Meshes);
            // The prefab sits at x=200; the mesh inside it is at z=32.
            Assert.Equal<float>([200, 0, 32], mesh.Positions[..3].ToArray());
            Assert.Single(scene.Props);
            Assert.Empty(scene.Diagnostics);
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    [Fact]
    public void Read_reports_a_prefab_it_cannot_resolve()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"h5t_vmap_scene_{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, "host.vmap");
        try
        {
            WritePrefabHost(path, "maps/absent.vmap");

            var scene = new ValveMapSceneReader().Read(path);

            Assert.Empty(scene.Meshes);
            Assert.Equal("Prefab not found: maps/absent.vmap", Assert.Single(scene.Diagnostics));
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    private static void WritePrefabHost(string path, string targetMapPath)
    {
        var model = new DM("vmap", 29);
        var root = new Element(model, "", null, "CMapRootElement");
        model.Root = root;
        var world = new Element(model, "", null, "CMapWorld");
        root["world"] = world;
        Place(world, Vector3.Zero);

        var prefab = new Element(model, "prefab", null, "CMapPrefab");
        Place(prefab, new Vector3(200, 0, 0));
        prefab["targetMapPath"] = targetMapPath;
        world["children"] = new ElementArray { prefab };

        model.Save(path, "keyvalues2", 4);
    }

    private static void WriteMap(string path, bool hidden = false)
    {
        var model = new DM("vmap", 29);
        var root = new Element(model, "", null, "CMapRootElement");
        model.Root = root;
        var world = new Element(model, "", null, "CMapWorld");
        root["world"] = world;
        Place(world, Vector3.Zero);

        var children = new ElementArray();
        world["children"] = children;

        var mesh = new Element(model, "brush", null, "CMapMesh");
        Place(mesh, new Vector3(0, 0, 32));
        mesh["meshData"] = Quad(model);
        mesh["force_hidden"] = hidden;
        children.Add(mesh);

        var group = new Element(model, "group", null, "CMapGroup");
        Place(group, new Vector3(100, 0, 0));
        group["force_hidden"] = hidden;
        var groupChildren = new ElementArray();
        group["children"] = groupChildren;
        children.Add(group);

        var entity = new Element(model, "prop", null, "CMapEntity");
        Place(entity, new Vector3(0, 50, 0));
        var properties = new Element(model, "", null, "EditGameClassProps");
        properties["classname"] = "prop_static";
        properties["model"] = "models/example.vmdl";
        entity["entity_properties"] = properties;
        groupChildren.Add(entity);

        var smartProp = new Element(model, "smart", null, "CMapSmartProp");
        Place(smartProp, new Vector3(0, 0, 0));
        smartProp["smartPropFilename"] = "smartprops/example.vsmart";
        smartProp["nodeData"] = NodeData(model);
        groupChildren.Add(smartProp);

        model.Save(path, "keyvalues2", 4);
    }

    private static void Place(Element element, Vector3 origin)
    {
        element["origin"] = origin;
        element["angles"] = new QAngle(0, 0, 0);
        element["scales"] = Vector3.One;
    }

    /// <summary>A unit quad in the half-edge form Hammer writes: four vertices, eight half-edges.</summary>
    private static Element Quad(DM model)
    {
        var mesh = new Element(model, "meshData", null, "CDmePolygonMesh");
        mesh["vertexDataIndices"] = new IntArray { 0, 1, 2, 3 };
        mesh["edgeVertexIndices"] = new IntArray { 1, 0, 2, 1, 3, 2, 0, 3 };
        mesh["edgeNextIndices"] = new IntArray { 2, 7, 4, 1, 6, 3, 0, 5 };
        mesh["edgeVertexDataIndices"] = new IntArray { 0, 1, 2, 3, 4, 5, 6, 7 };
        mesh["faceEdgeIndices"] = new IntArray { 6 };
        mesh["faceDataIndices"] = new IntArray { 0 };
        mesh["materials"] = new StringArray { "materials/dev/grid.vmat" };
        mesh["vertexData"] = DataArray(model, new Element(model, "position:0", null, "CDmePolygonMeshDataStream")
        {
            ["standardAttributeName"] = "position",
            ["data"] = new Vector3Array
            {
                new(0, 0, 0), new(16, 0, 0), new(16, 16, 0), new(0, 16, 0),
            },
        });
        mesh["faceData"] = DataArray(model, new Element(model, "materialindex:0", null, "CDmePolygonMeshDataStream")
        {
            ["standardAttributeName"] = "materialindex",
            ["data"] = new IntArray { 0 },
        });
        return mesh;
    }

    private static Element DataArray(DM model, Element stream)
    {
        var array = new Element(model, "", null, "CDmePolygonMeshDataArray");
        array["streams"] = new ElementArray { stream };
        return array;
    }

    private static Element NodeData(DM model)
    {
        var length = new Element(model, "value", null, "DmElement");
        length["parameterName"] = "length";
        length["value"] = 4f;

        var typed = new Element(model, "value_with_specific_type", null, "DmElement");
        typed["specific_type"] = "resource_name";
        typed["value"] = "models/fence.vmdl";
        var column = new Element(model, "value", null, "DmElement");
        column["parameterName"] = "column";
        column["value"] = typed;

        var values = new ElementArray();
        foreach (var parameter in new[] { length, column })
        {
            var entry = new Element(model, "", null, "DmElement");
            entry["value"] = parameter;
            values.Add(entry);
        }

        var parameters = new Element(model, "parameters", null, "DmElement");
        parameters["values"] = values;
        var nodeData = new Element(model, "nodeData", null, "DmElement");
        nodeData["parameters"] = parameters;
        return nodeData;
    }
}
