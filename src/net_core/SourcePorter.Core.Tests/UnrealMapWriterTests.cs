using System.Text.Json;

using SourcePorter.Core.Vmap;

namespace SourcePorter.Core.Tests;

public sealed class UnrealMapWriterTests
{
    [Fact]
    public void WriteJson_writes_typed_entities_and_smartprops()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"h5t_unreal_writer_{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, "scene.vmap");
        try
        {
            var request = new UnrealMapWriteRequest(
            [
                new UnrealMapPlacement(
                    UnrealMapPlacementKind.Entity,
                    "Chair",
                    [300, -400, 50],
                    [-20, -60, 30],
                    [2, 3, 4],
                    new Dictionary<string, string>
                    {
                        ["classname"] = "prop_static",
                        ["model"] = "models/meshes/chair.vmdl",
                    },
                    null),
                new UnrealMapPlacement(
                    UnrealMapPlacementKind.SmartProp,
                    "Door",
                    [0, 0, 0],
                    [0, 0, 0],
                    [1, 1, 1],
                    null,
                    "smartprops/door.vsmart"),
            ]);

            var result = UnrealMapWriter.WriteJson(JsonSerializer.Serialize(request), path);

            Assert.True(result.IsSuccess);
            Assert.Equal(2, result.Value!.PlacementCount);
            Assert.Equal("binary", result.Value.Encoding);
            var document = VmapDocument.LoadInMemory(path);
            var prop = Assert.Single(document.WorldChildren, node => node.ClassName == "CMapEntity");
            var properties = Assert.IsType<Datamodel.Element>(prop["entity_properties"]);
            Assert.Equal("models/meshes/chair.vmdl", properties["model"]);
            Assert.Equal(new System.Numerics.Vector3(300, -400, 50), prop["origin"]);
            var smartProp = Assert.Single(document.WorldChildren, node => node.ClassName == "CMapSmartProp");
            Assert.Equal("smartprops/door.vsmart", smartProp["smartPropFilename"]);
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    [Fact]
    public void WriteJson_returns_structured_diagnostic_for_invalid_request()
    {
        var result = UnrealMapWriter.WriteJson("{}", "invalid.vmap");

        Assert.False(result.IsSuccess);
        Assert.Equal("unreal_vmap_write_failed", Assert.Single(result.Diagnostics).Code);
    }

    [Fact]
    public void Write_writes_native_decal_mesh()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"h5t_unreal_writer_{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, "decal.vmap");
        try
        {
            var request = new UnrealMapWriteRequest(
            [
                new UnrealMapPlacement(
                    UnrealMapPlacementKind.Decal,
                    "Poster",
                    [0, 0, 0],
                    [0, 0, 0],
                    [1, 1, 1],
                    null,
                    "materials/m/poster.vmat"),
            ]);

            var result = UnrealMapWriter.Write(request, path);

            Assert.True(result.IsSuccess);
            var document = VmapDocument.LoadInMemory(path);
            var overlay = Assert.Single(document.WorldChildren);
            Assert.Equal("CMapStaticOverlay", overlay.ClassName);
            var mesh = Assert.IsType<Datamodel.Element>(overlay["meshData"]);
            Assert.Equal("CDmePolygonMesh", mesh.ClassName);
            Assert.Equal(["materials/m/poster.vmat"], Assert.IsType<Datamodel.StringArray>(mesh["materials"]));
            var subdivision = Assert.IsType<Datamodel.Element>(mesh["subdivisionData"]);
            Assert.Equal(8, Assert.IsType<Datamodel.IntArray>(subdivision["subdivisionLevels"]).Count);
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }
}
