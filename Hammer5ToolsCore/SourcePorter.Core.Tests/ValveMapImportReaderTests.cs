using System.Numerics;
using System.Text.Json.Nodes;
using Datamodel;
using Hammer5Tools.Core.Format.SmartProps;
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
            Assert.Equal(0f, imported["transform"]![12]!.GetValue<float>());
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

    [Fact]
    public void Selection_mask_includes_group_descendants_and_prefabs_with_instance_transforms()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"h5t_prefabs_{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        try
        {
            var prefab = new DM("vmap", 29);
            prefab.Root = new Element(prefab, "", null, "CMapRootElement");
            var prefabWorld = new Element(prefab, "prefab", null, "CMapWorld");
            prefab.Root["world"] = prefabWorld;
            prefabWorld["children"] = new ElementArray { new Element(prefab, "quad", null, "CMapMesh") { ["meshData"] = Quad(prefab) } };
            prefab.Save(Path.Combine(directory, "piece.vmap"), "binary", 9);

            var document = new DM("vmap", 29);
            document.Root = new Element(document, "", null, "CMapRootElement");
            var world = new Element(document, "world", null, "CMapWorld");
            document.Root["world"] = world;
            var group = new Element(document, "walls", null, "CMapGroup");
            var first = new Element(document, "first", null, "CMapPrefab")
            {
                ["targetMapPath"] = "piece.vmap",
                ["origin"] = new Vector3(10, 0, 0),
            };
            var second = new Element(document, "second", null, "CMapPrefab")
            {
                ["targetMapPath"] = "piece.vmap",
                ["origin"] = new Vector3(20, 0, 0),
            };
            group["children"] = new ElementArray { first, second };
            var other = new Element(document, "other", null, "CMapMesh") { ["meshData"] = Quad(document) };
            var missingSmart = new Element(document, "missing", null, "CMapSmartProp") { ["smartPropFilename"] = "missing.vsmart" };
            world["children"] = new ElementArray { group, other, missingSmart };
            document.Root["rootSelectionSet"] = new Element(document, "", null, "CMapSelectionSet")
            {
                ["selectionSetName"] = "Walls main",
                ["selectionSetData"] = new Element(document, "", null, "CObjectSelectionSetDataElement")
                {
                    ["selectedObjects"] = new ElementArray { group },
                },
            };
            var path = Path.Combine(directory, "main.vmap");
            document.Save(path, "binary", 9);
            var reader = new ValveMapImportReader();
            var options = new ValveMapImportOptions { SelectionSetMask = "Walls*", IncludeEditorMetadata = false };
            var scene = JsonNode.Parse(reader.Read(path, directory, options))!;
            var meshes = scene["nodes"]!.AsArray().Where(node => node!["mesh"] is not null).ToArray();
            Assert.Equal(2, meshes.Length);
            Assert.Equal(new[] { 10f, 20f }, meshes.Select(node => node!["transform"]![12]!.GetValue<float>()));
            Assert.NotEqual(meshes[0]!["scope"]!.GetValue<string>(), meshes[1]!["scope"]!.GetValue<string>());
            Assert.All(meshes, node => Assert.Empty(node!["metadata"]!.AsObject()));
            Assert.DoesNotContain(scene["diagnostics"]!.AsArray(), value => value!.GetValue<string>().Contains("missing.vsmart"));
            Assert.Equal(2, scene["dependencies"]!.AsArray().Count);

            scene = JsonNode.Parse(reader.Read(path, directory, options with { InvertSelectionSetMask = true, EvaluateSmartProps = false }))!;
            Assert.Single(scene["nodes"]!.AsArray(), node => node!["mesh"] is not null);
            scene = JsonNode.Parse(reader.Read(path, directory, options with { ExpandPrefabs = false }))!;
            Assert.DoesNotContain(scene["nodes"]!.AsArray(), node => node!["mesh"] is not null);
            scene = JsonNode.Parse(reader.Read(path, directory, options with { SelectionSetMask = "unknown" }))!;
            Assert.DoesNotContain(scene["nodes"]!.AsArray(), node => node!["mesh"] is not null);
            Assert.Contains(scene["diagnostics"]!.AsArray(), value => value!.GetValue<string>().Contains("No Hammer selection sets match"));

            group["force_hidden"] = true;
            document.Save(path, "binary", 9);
            scene = JsonNode.Parse(reader.Read(path, directory, options with { IncludeHidden = false }))!;
            Assert.DoesNotContain(scene["nodes"]!.AsArray(), node => node!["mesh"] is not null);
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    [Fact]
    public void SmartProp_deserialization_and_overrides_do_not_mutate_source_or_survive_next_read()
    {
        var path = Path.Combine(Path.GetTempPath(), $"h5t_smart_{Guid.NewGuid():N}.vsmart");
        const string json = """
            {"generic_data_type":"CSmartPropRoot",
             "m_Variables":[{"_class":"CSmartPropVariable_Float","m_VariableName":"Width","m_DefaultValue":2}],
             "m_Children":[{"_class":"CSmartPropElement_Model","m_nElementID":1,"m_sModelName":"models/test.vmdl",
                 "m_vModelScale":{"m_Components":[{"m_Expression":"Width"},1,1]}}]}
            """;
        var text = SmartPropDocumentSerializer.SerializeJson(json);
        File.WriteAllText(path, text);
        try
        {
            var reader = new ValveMapImportReader();
            var scene = JsonNode.Parse(reader.ReadSmartProp(path, variablesJson: "{\"Width\":5}"))!;
            Assert.Single(scene["nodes"]![0]!["smartPropModels"]!.AsArray());
            Assert.Equal(5f, scene["nodes"]![0]!["smartPropModels"]![0]!["transform"]![0]!.GetValue<float>());
            Assert.Equal(5, scene["smartPropDocument"]!["m_Variables"]![0]!["m_DefaultValue"]!.GetValue<int>());
            Assert.Equal(text, File.ReadAllText(path));
            scene = JsonNode.Parse(reader.ReadSmartProp(path))!;
            Assert.Equal(2f, scene["nodes"]![0]!["smartPropModels"]![0]!["transform"]![0]!.GetValue<float>());
            Assert.Throws<InvalidDataException>(() => reader.ReadSmartProp(path, variablesJson: "[]"));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void Ignore_tool_material_objects_checks_used_faces_and_keeps_mixed_or_unknown_materials()
    {
        var path = Path.Combine(Path.GetTempPath(), $"h5t_tools_{Guid.NewGuid():N}.vmap");
        var document = new DM("vmap", 29);
        document.Root = new Element(document, "", null, "CMapRootElement");
        var world = new Element(document, "world", null, "CMapWorld");
        document.Root["world"] = world;
        var tools = Quad(document);
        tools["materials"] = new StringArray { @"MATERIALS\TOOLS\TOOLSCLIP.VMAT_C", "materials/grid.vmat" };
        var visible = Quad(document);
        var mixed = Quad(document);
        mixed["materials"] = new StringArray { "materials/tools/toolstrigger.vmat", "materials/grid.vmat" };
        mixed["faceEdgeIndices"] = new IntArray { 0, 0 };
        mixed["faceDataIndices"] = new IntArray { 0, 1 };
        var faceData = (Element)mixed["faceData"]!;
        var stream = ((ElementArray)faceData["streams"]!)[0]!;
        stream["data"] = new IntArray { 0, 1 };
        var unknown = Quad(document);
        unknown["materials"] = new StringArray();
        world["children"] = new ElementArray
        {
            new Element(document, "tools", null, "CMapMesh") { ["meshData"] = tools },
            new Element(document, "visible", null, "CMapMesh") { ["meshData"] = visible },
            new Element(document, "mixed", null, "CMapMesh") { ["meshData"] = mixed },
            new Element(document, "unknown", null, "CMapMesh") { ["meshData"] = unknown },
        };
        document.Save(path, "binary", 9);
        try
        {
            var reader = new ValveMapImportReader();
            var original = JsonNode.Parse(reader.Read(path))!;
            Assert.Equal(4, original["nodes"]!.AsArray().Count(node => node!["mesh"] is not null));
            var filtered = JsonNode.Parse(reader.Read(path, importOptions: new() { IgnoreToolMaterialObjects = true }))!;
            var nodes = filtered["nodes"]!.AsArray();
            Assert.Equal(5, nodes.Count);
            Assert.False(nodes[1]!["included"]!.GetValue<bool>());
            Assert.Null(nodes[1]!["mesh"]);
            Assert.Equal(3, nodes.Count(node => node!["mesh"] is not null));
            Assert.Equal(2, nodes[3]!["mesh"]!["faces"]!.AsArray().Count);
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void Groups_use_map_space_instances_rebase_target_pivots_and_overlays_can_be_excluded()
    {
        var path = Path.Combine(Path.GetTempPath(), $"h5t_instances_{Guid.NewGuid():N}.vmap");
        var document = new DM("vmap", 29);
        document.Root = new Element(document, "", null, "CMapRootElement");
        var world = new Element(document, "world", null, "CMapWorld");
        document.Root["world"] = world;
        var group = new Element(document, "assembly", null, "CMapGroup")
        {
            ["origin"] = new Vector3(100, 200, 0),
            ["angles"] = new QAngle(0, 90, 0),
        };
        var mesh = new Element(document, "brush", null, "CMapMesh")
        {
            ["origin"] = new Vector3(100, 210, 0),
            ["meshData"] = Quad(document),
        };
        var prop = new Element(document, "model", null, "CMapEntity")
        {
            ["origin"] = new Vector3(100, 220, 0),
            ["entity_properties"] = new Element(document, "", null, "EditGameClassProps")
            {
                ["model"] = "models/test.vmdl",
            },
        };
        group["children"] = new ElementArray { mesh, prop };
        var instance = new Element(document, "copy", null, "CMapInstance")
        {
            ["origin"] = new Vector3(300, 400, 0),
            ["target"] = group,
        };
        var overlay = new Element(document, "decal", null, "CMapStaticOverlay") { ["meshData"] = Quad(document) };
        world["children"] = new ElementArray { group, instance, overlay };
        document.Root["rootSelectionSet"] = new Element(document, "", null, "CMapSelectionSet")
        {
            ["selectionSetName"] = "Copies",
            ["selectionSetData"] = new Element(document, "", null, "CObjectSelectionSetDataElement")
            {
                ["selectedObjects"] = new ElementArray { instance },
            },
        };
        document.Save(path, "binary", 9);
        try
        {
            var reader = new ValveMapImportReader();
            var scene = JsonNode.Parse(reader.Read(path, importOptions: new() { IgnoreStaticOverlays = true }))!;
            var nodes = scene["nodes"]!.AsArray();
            var brushes = nodes.Where(node => node!["mesh"] is not null).ToArray();
            Assert.Equal(2, brushes.Length);
            Assert.Equal(100f, brushes[0]!["transform"]![12]!.GetValue<float>());
            Assert.Equal(210f, brushes[0]!["transform"]![13]!.GetValue<float>());
            Assert.InRange(brushes[1]!["transform"]![12]!.GetValue<float>(), 309.99f, 310.01f);
            Assert.InRange(brushes[1]!["transform"]![13]!.GetValue<float>(), 399.99f, 400.01f);
            var models = nodes.Where(node => node!["model"] is not null).ToArray();
            Assert.Equal(2, models.Length);
            Assert.InRange(models[1]!["transform"]![12]!.GetValue<float>(), 319.99f, 320.01f);
            Assert.False(nodes.Last()!["included"]!.GetValue<bool>());
            scene = JsonNode.Parse(reader.Read(path, importOptions: new() { SelectionSetMask = "Copies" }))!;
            Assert.Single(scene["nodes"]!.AsArray(), node => node!["mesh"] is not null);
            var preview = new ValveMapSceneReader().Read(path);
            Assert.Equal(2, preview.Props.Length);
            Assert.InRange(preview.Props[1].Transform[12], 319.99f, 320.01f);
            var setData = (Element)((Element)document.Root["rootSelectionSet"]!)["selectionSetData"]!;
            setData["selectedObjects"] = new ElementArray { group };
            document.Save(path, "binary", 9);
            scene = JsonNode.Parse(reader.Read(path, importOptions: new() { SelectionSetMask = "Copies" }))!;
            Assert.Single(scene["nodes"]!.AsArray(), node => node!["mesh"] is not null);

            // A cyclic reference must produce diagnostics rather than overflow the stack.
            group["children"] = new ElementArray { mesh, instance };
            document.Save(path, "binary", 9);
            scene = JsonNode.Parse(reader.Read(path))!;
            Assert.Contains(scene["diagnostics"]!.AsArray(), value => value!.GetValue<string>().Contains("Node cycle"));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void Missing_nested_smartprop_keeps_valid_models_and_reports_dependency()
    {
        var path = Path.Combine(Path.GetTempPath(), $"h5t_nested_{Guid.NewGuid():N}.vsmart");
        File.WriteAllText(path, SmartPropDocumentSerializer.SerializeJson("""
            {"generic_data_type":"CSmartPropRoot", "m_Children":[
                {"_class":"CSmartPropElement_Model", "m_nElementID":1, "m_sModelName":"models/test.vmdl"},
                {"_class":"CSmartPropElement_SmartProp", "m_nElementID":2, "m_sSmartProp":"missing/child.vsmart"}]}
            """));
        try
        {
            var scene = JsonNode.Parse(new ValveMapImportReader().ReadSmartProp(path))!;
            Assert.Single(scene["nodes"]![0]!["smartPropModels"]!.AsArray());
            Assert.Contains(scene["diagnostics"]!.AsArray(), value => value!.GetValue<string>().Contains("missing/child.vsmart"));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void Hammer_visibility_and_selection_overrides_filter_before_building_geometry()
    {
        var path = Path.Combine(Path.GetTempPath(), $"h5t_visible_{Guid.NewGuid():N}.vmap");
        var document = new DM("vmap", 29);
        document.Root = new Element(document, "", null, "CMapRootElement");
        var world = new Element(document, "world", null, "CMapWorld");
        document.Root["world"] = world;
        var hidden = new Element(document, "hidden", null, "CMapMesh") { ["meshData"] = Quad(document) };
        var visible = new Element(document, "visible", null, "CMapMesh") { ["meshData"] = Quad(document) };
        world["children"] = new ElementArray { hidden, visible };
        document.Root["visbility"] = new Element(document, "", null, "CVisibilityMgr")
        {
            ["nodes"] = new ElementArray { hidden, visible },
            ["hiddenFlags"] = new IntArray { 1, 0 },
        };
        Element Set(string name, Element node) => new(document, "", null, "CMapSelectionSet")
        {
            ["selectionSetName"] = name,
            ["selectionSetData"] = new Element(document, "", null, "CObjectSelectionSetDataElement")
            {
                ["selectedObjects"] = new ElementArray { node },
            },
        };
        document.Root["rootSelectionSet"] = new Element(document, "", null, "CMapSelectionSet")
        {
            ["children"] = new ElementArray { Set("Hidden", hidden), Set("Visible", visible), Set("Overlap", hidden) },
        };
        document.Save(path, "binary", 9);
        try
        {
            var reader = new ValveMapImportReader();
            var options = new ValveMapImportOptions { IncludeHidden = false, IncludeEditorMetadata = false };
            var scene = JsonNode.Parse(reader.Read(path, importOptions: options))!;
            Assert.Equal(2, scene["schemaVersion"]!.GetValue<int>());
            Assert.Single(scene["nodes"]!.AsArray(), node => node!["mesh"] is not null);
            Assert.True(scene["nodes"]![1]!["hidden"]!.GetValue<bool>());
            var catalog = scene["selectionSetStates"]!.AsArray();
            Assert.Equal("hidden", catalog[0]!["visibility"]!.GetValue<string>());
            Assert.Equal("visible", catalog[1]!["visibility"]!.GetValue<string>());
            var overrides = new Dictionary<string, int>
            {
                [catalog[0]!["key"]!.GetValue<string>()] = 1,
                [catalog[1]!["key"]!.GetValue<string>()] = 2,
            };
            scene = JsonNode.Parse(reader.Read(path, importOptions: options with { SelectionSetOverrides = overrides }))!;
            Assert.NotNull(scene["nodes"]![1]!["mesh"]);
            Assert.Null(scene["nodes"]![2]!["mesh"]);
            overrides[catalog[2]!["key"]!.GetValue<string>()] = 2;
            scene = JsonNode.Parse(reader.Read(path, importOptions: options with { SelectionSetOverrides = overrides, IncludeHidden = true }))!;
            Assert.DoesNotContain(scene["nodes"]!.AsArray(), node => node!["mesh"] is not null);
            scene = JsonNode.Parse(reader.Read(path, importOptions: options with { MetadataOnly = true }))!;
            Assert.DoesNotContain(scene["nodes"]!.AsArray(), node => node!["mesh"] is not null);
            Assert.Equal(3, scene["selectionSetStates"]!.AsArray().Count);
        }
        finally
        {
            File.Delete(path);
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
