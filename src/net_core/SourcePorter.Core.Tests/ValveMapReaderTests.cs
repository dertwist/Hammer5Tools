using Datamodel;
using SourcePorter.Core.Vmap;
using DM = Datamodel.Datamodel;

namespace SourcePorter.Core.Tests;

public sealed class ValveMapReaderTests
{
    [Fact]
    public void Read_projects_world_nodes_and_scalar_properties_without_writing()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"h5t_vmap_reader_{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, "reader.vmap");
        try
        {
            WriteMap(path);
            var timestamp = File.GetLastWriteTimeUtc(path);

            var result = new ValveMapReader().Read(path);

            Assert.Equal(path, result.Path);
            Assert.Equal("CMapWorld", result.World.ClassName);
            Assert.Equal(2, result.Nodes.Count);
            var entity = Assert.Single(result.Nodes, node => node.ClassName == "CMapEntity");
            Assert.Equal("maps/example.vmap", entity.Properties["targetMapPath"]);
            Assert.Equal(timestamp, File.GetLastWriteTimeUtc(path));
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    private static void WriteMap(string path)
    {
        var model = new DM("vmap", 29);
        var root = new Element(model, "", null, "CMapRootElement");
        model.Root = root;
        var world = new Element(model, "", null, "CMapWorld");
        root["world"] = world;
        var children = new ElementArray();
        world["children"] = children;
        var entity = new Element(model, "", null, "CMapEntity")
        {
            ["targetMapPath"] = "maps/example.vmap",
        };
        children.Add(entity);
        model.Save(path, "keyvalues2", 4);
    }
}
