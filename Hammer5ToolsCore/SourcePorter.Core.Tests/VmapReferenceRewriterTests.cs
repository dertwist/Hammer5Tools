using System.Text;

using Datamodel;
using Hammer5Tools.Core.Format.Vmap;
using DM = Datamodel.Datamodel;

namespace SourcePorter.Core.Tests;

public sealed class VmapReferenceRewriterTests
{
    [Fact]
    public void Rewrite_updates_body_and_prefix_references_in_one_pass()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"h5t_vmap_rewrite_{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, "rewrite.vmap");
        try
        {
            WriteMap(path);

            var result = VmapReferenceRewriter.Rewrite(path, new Dictionary<string, string>
            {
                ["models/old"] = "models/new",
                ["models/old_long"] = "models/replaced",
            });

            Assert.True(result.IsSuccess);
            Assert.True(result.Value);
            var document = new ValveMapReader().Read(path);
            Assert.Equal(["models/new", "models/replaced"], document.AssetReferences);
            Assert.Equal("models/new", document.Nodes.Single(node => node.ClassName == "CMapEntity").Properties["model"]);
            Assert.DoesNotContain("models/old", File.ReadAllText(path));
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    [Fact]
    public void Rewrite_does_not_change_a_map_without_matches()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"h5t_vmap_rewrite_{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, "rewrite.vmap");
        try
        {
            WriteMap(path);
            var before = File.ReadAllBytes(path);

            var result = VmapReferenceRewriter.Rewrite(path, new Dictionary<string, string>
            {
                ["models/missing"] = "models/new",
            });

            Assert.True(result.IsSuccess);
            Assert.False(result.Value);
            Assert.Equal(before, File.ReadAllBytes(path));
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    [Fact]
    public void Rewrite_preserves_binary_prefix_metadata()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"h5t_vmap_rewrite_{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, "rewrite.vmap");
        try
        {
            WriteMap(path, "binary", 9);
            var before = File.ReadAllBytes(path);
            Assert.Contains("models/old", Encoding.UTF8.GetString(before));
            Assert.NotNull(VmapReferenceRewriter.PrefixEnd(before));

            var result = VmapReferenceRewriter.Rewrite(path, new Dictionary<string, string>
            {
                ["models/old"] = "models/new",
            });

            Assert.True(result.IsSuccess);
            Assert.True(result.Value);
            var output = File.ReadAllBytes(path);
            var outputText = Encoding.UTF8.GetString(output);
            Assert.DoesNotContain("models/old", outputText);
            Assert.Contains("models/new", outputText);
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    private static void WriteMap(string path, string encoding = "keyvalues2", int encodingVersion = 4)
    {
        var model = new DM("vmap", 29);
        model.PrefixAttributes["map_asset_references"] = new[] { "models/old", "models/old_long" };
        model.PrefixAttributes["asset_preview_thumbnail"] = new byte[] { 0x01, 0xA2, 0xFF };
        model.PrefixAttributes["asset_preview_thumbnail_format"] = "jpg";
        var root = new Element(model, "", null, "CMapRootElement");
        model.Root = root;
        var world = new Element(model, "", null, "CMapWorld");
        root["world"] = world;
        var children = new ElementArray();
        world["children"] = children;
        children.Add(new Element(model, "", null, "CMapEntity")
        {
            ["model"] = "models/old",
        });
        model.Save(path, encoding, encodingVersion);
    }
}
