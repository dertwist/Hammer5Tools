using System.Numerics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Hammer5Tools.Core.Format.Vmap;

namespace Hammer5Tools.Core.Tests;

public sealed class MapAuthoringTests
{
    [Test]
    public async Task ZooPatternDoesNotTreatDestinationAsACompilerInput()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(Path.Combine(root, "models"));
        var path = Path.Combine(root, "fixture.vmap");
        try
        {
            _ = UnrealMapWriter.Write(new UnrealMapWriteRequest([]), path);
            File.WriteAllText(Path.Combine(root, "models", "a.vmdl"), "fixture");
            File.WriteAllText(Path.Combine(root, "models", "b.vmdl"), "fixture");
            var response = JsonNode.Parse(CoreApi.AuthorMap(JsonSerializer.Serialize(new { path, addon_root = root,
                pattern = "models/*.vmdl", columns = 1, spacing = new[] { 100, 200, 0 } }), "zoo"))!;
            await Assert.That(response["box_count"]!.GetValue<int>()).IsEqualTo(2);
            var document = VmapDocument.LoadInMemory(path);
            await Assert.That(document.WorldChildren[1]["origin"]).IsEqualTo((object)new Vector3(0, 200, 0));
        }
        finally { Directory.Delete(root, true); }
    }

    [Test]
    public async Task Inserts154PropsFromFileAndPreservesExistingDocument()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        var path = Path.Combine(root, "fixture.vmap");
        try
        {
            var result = UnrealMapWriter.Write(new UnrealMapWriteRequest([
                new UnrealMapPlacement(UnrealMapPlacementKind.Entity, "existing", [1, 2, 3], [0, 0, 0], [1, 1, 1],
                    new Dictionary<string, string> { ["classname"] = "info_player_terrorist", ["custom"] = "preserved" }, null)
            ]), path);
            await Assert.That(result.IsSuccess).IsTrue();
            var before = VmapDocument.LoadInMemory(path);
            var existingId = before.WorldChildren[0].ID;
            var manifest = Path.Combine(root, "items.json");
            File.WriteAllText(manifest, JsonSerializer.Serialize(Enumerable.Range(0, 154).Select(index => new { model = "models/example.vmdl", scale = 1, position = new[] { index, 0, 0 } })));
            var json = JsonSerializer.Serialize(new { path, items_file = manifest, dry_run = true });
            var bytes = File.ReadAllBytes(path);
            _ = CoreApi.AuthorMap(json, "insert");
            await Assert.That(File.ReadAllBytes(path).AsSpan().SequenceEqual(bytes)).IsTrue();
            var response = JsonNode.Parse(CoreApi.AuthorMap(JsonSerializer.Serialize(new { path, items_file = manifest }), "insert"))!;
            await Assert.That(response["box_count"]!.GetValue<int>()).IsEqualTo(154);
            var after = VmapDocument.LoadInMemory(path);
            await Assert.That(after.WorldChildren.Count).IsEqualTo(155);
            await Assert.That(after.WorldChildren[0].ID).IsEqualTo(existingId);
            await Assert.That(after.WorldChildren[1]["scales"]).IsEqualTo((object)Vector3.One);
            await Assert.That(after.WorldChildren.Select(node => node.ID).Distinct().Count()).IsEqualTo(155);
            await Assert.That(((Datamodel.Element)after.WorldChildren[0]["entity_properties"]!)["custom"]).IsEqualTo((object)"preserved");
            _ = CoreApi.AuthorMap(JsonSerializer.Serialize(new { path, boxes = new[] { new { size = new[] { 512, 64, 32 } } } }), "insert");
            after = VmapDocument.LoadInMemory(path);
            await Assert.That(after.WorldChildren[^1]["scales"]).IsEqualTo((object)new Vector3(51.2f, 6.4f, 3.2f));
            var saved = File.ReadAllBytes(path);
            await Assert.That(() => CoreApi.AuthorMap(JsonSerializer.Serialize(new { path, boxes = new[] { new { size = new[] { 1, 1, 1 }, scale = 1 } } }), "insert")).Throws<ArgumentException>();
            await Assert.That(File.ReadAllBytes(path).AsSpan().SequenceEqual(saved)).IsTrue();
        }
        finally { Directory.Delete(root, true); }
    }

    [Test]
    public async Task ReparentAndUngroupPreserveWorldPositionAndRejectCycles()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        var path = Path.Combine(root, "fixture.vmap");
        try
        {
            _ = UnrealMapWriter.Write(new UnrealMapWriteRequest([]), path);
            _ = CoreApi.AuthorMap(JsonSerializer.Serialize(new { path, boxes = new[] { new { model = "models/a.vmdl", position = new[] { 20, 30, 40 } } } }), "insert");
            var entity = VmapDocument.LoadInMemory(path).WorldChildren[0].ID.ToString();
            var group = JsonNode.Parse(CoreApi.AuthorMap(JsonSerializer.Serialize(new { path, action = "create", name = "group" }), "group"))!["ids"]![0]!.GetValue<string>();
            _ = CoreApi.AuthorMap(JsonSerializer.Serialize(new { path, id = group, position = new[] { 100, 20, 30 }, angles = new[] { 10, 20, 30 }, scale = 2 }), "transform");
            _ = CoreApi.AuthorMap(JsonSerializer.Serialize(new { path, action = "reparent", id = entity, parent_id = group }), "group");
            var nodes = JsonNode.Parse(CoreApi.AuthorMap(JsonSerializer.Serialize(new { path }), "nodes"))!["nodes"]!.AsArray();
            var node = nodes.Single(node => node!["id"]!.GetValue<string>() == entity)!;
            var position = node["world_origin"]!.AsArray();
            await Assert.That(MathF.Abs(position[0]!.GetValue<float>() - 20) < 0.001f).IsTrue();
            await Assert.That(node["parent_id"]!.GetValue<string>()).IsEqualTo(group);
            await Assert.That(() => CoreApi.AuthorMap(JsonSerializer.Serialize(new { path, action = "reparent", id = group, parent_id = group }), "group")).Throws<ArgumentException>();
            _ = CoreApi.AuthorMap(JsonSerializer.Serialize(new { path, action = "remove", id = group }), "group");
            var after = VmapDocument.LoadInMemory(path);
            await Assert.That(after.WorldChildren.Count).IsEqualTo(1);
            var origin = (Vector3)after.WorldChildren[0]["origin"]!;
            await Assert.That(Vector3.Distance(origin, new Vector3(20, 30, 40)) < 0.001f).IsTrue();
        }
        finally { Directory.Delete(root, true); }
    }
}
