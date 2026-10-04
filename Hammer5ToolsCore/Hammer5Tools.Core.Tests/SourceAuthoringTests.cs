using System.Text.Json;
using System.Text.Json.Nodes;
using Hammer5Tools.Core.Format.Authoring;
using Hammer5Tools.Core.IO.Automation;

namespace Hammer5Tools.Core.Tests;

public sealed class SourceAuthoringTests
{
    [Test]
    public async Task PropertyPreviewsReportTruncationWithoutWriting()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        var path = Path.Combine(root, "preview.vmat");
        var parameters = Enumerable.Range(0, 60).ToDictionary(index => "parameter" + index, index => index);
        var result = JsonNode.Parse(CoreApi.AuthorSourceAssets(JsonSerializer.Serialize(new { path, parameters, dry_run = true }), "vmat", false))!;
        await Assert.That(result["modified_count"]!.GetValue<int>()).IsEqualTo(61);
        await Assert.That(result["modified_fields"]!.AsArray().Count).IsEqualTo(50);
        await Assert.That(result["fields_truncated"]!.GetValue<bool>()).IsTrue();
        await Assert.That(Directory.Exists(root)).IsFalse();
    }

    [Test]
    public async Task AuthoringSerializationWorksWithoutReflection()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try
        {
            var path = JsonSerializer.Serialize(Path.Combine(root, "new.vmat"), AutomationJsonContext.Default.String);
            var response = CoreApi.AuthorSourceAssets("{\"path\":" + path + ",\"slots\":{\"TextureColor\":\"materials/a.png\"}}", "vmat", false);
            await Assert.That(response.Contains("content_length", StringComparison.Ordinal)).IsTrue();
        }
        finally { Directory.Delete(root, true); }
    }
    [Test]
    public async Task Updates49MaterialsPreservingUnknownBlocksAndIsIdempotent()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        File.WriteAllText(Path.Combine(root, "ao.png"), "reference fixture");
        try
        {
            var paths = Enumerable.Range(0, 49).Select(index => Path.Combine(root, $"material {index}.vmat")).ToArray();
            foreach (var path in paths) File.WriteAllText(path, "Layer0 { shader \"csgo_environment.vfx\" Unknown { nested \"preserve\" } }");
            var json = JsonSerializer.Serialize(new { addon_root = root, items = paths.Select(path => new { path, action = "update", set_slots = new { TextureAmbientOcclusion = "ao.png" } }) });
            var result = JsonNode.Parse(CoreApi.AuthorSourceAssets(json, "vmat", true))!;
            await Assert.That(result["changed"]!.GetValue<int>()).IsEqualTo(49);
            await Assert.That(result["failed"]!.GetValue<int>()).IsEqualTo(0);
            await Assert.That(File.ReadAllText(paths[0]).Contains("preserve", StringComparison.Ordinal)).IsTrue();
            await Assert.That(Directory.GetFiles(root, "*.bak").Length).IsEqualTo(49);
            var repeat = JsonNode.Parse(CoreApi.AuthorSourceAssets(json, "vmat", true))!;
            await Assert.That(repeat["skipped"]!.GetValue<int>()).IsEqualTo(49);
            await Assert.That(Directory.GetFiles(root, "*.bak").Length).IsEqualTo(49);
        }
        finally { Directory.Delete(root, true); }
    }

    [Test]
    public async Task ValidatesAllItemsBeforeWritingAndReportsReplacementFailure()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try
        {
            var first = Path.Combine(root, "first.vmat");
            var second = Path.Combine(root, "second.vmat");
            using var invalid = JsonDocument.Parse(JsonSerializer.Serialize(new { addon_root = root, items = new object[] {
                new { path = first, slots = new { TextureColor = "missing.png" } }, new { path = second } } }));
            await Assert.That(() => SourceAssetAuthoring.Batch(invalid.RootElement, "vmat")).Throws<FileNotFoundException>();
            await Assert.That(File.Exists(first)).IsFalse();
            using var valid = JsonDocument.Parse(JsonSerializer.Serialize(new { items = new[] { new { path = first }, new { path = second } } }));
            var calls = 0;
            var result = SourceAssetAuthoring.Batch(valid.RootElement, "vmat", (staged, destination) =>
            {
                if (++calls == 2) throw new IOException("injected replacement failure");
                return SafeAssetWrites.Replace(staged, destination);
            });
            await Assert.That(result["changed"]!.GetValue<int>()).IsEqualTo(1);
            await Assert.That(result["failed"]!.GetValue<int>()).IsEqualTo(1);
            await Assert.That(File.Exists(second)).IsFalse();
            await Assert.That(Directory.GetFiles(root, "*.tmp").Length).IsEqualTo(0);
        }
        finally { Directory.Delete(root, true); }
    }

    [Test]
    public async Task SharedMaterialAndModelEditPreserveUnknownModelFields()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        File.WriteAllText(Path.Combine(root, "mesh.fbx"), "fixture");
        try
        {
            _ = CoreApi.AuthorSourceAssets(JsonSerializer.Serialize(new { path = Path.Combine(root, "shared.vmat") }), "vmat", false);
            var models = new[] { "first.vmdl", "second.vmdl" };
            var batch = JsonSerializer.Serialize(new { addon_root = root, items = models.Select(path => new { path, mesh_rel_path = "mesh.fbx", material_remaps = new[] { new { from = "material", to = "shared.vmat" } } }) });
            var result = JsonNode.Parse(CoreApi.AuthorSourceAssets(batch, "vmdl", true))!;
            await Assert.That(result["changed"]!.GetValue<int>()).IsEqualTo(2);
            var path = Path.Combine(root, "first.vmdl");
            var text = File.ReadAllText(path);
            var end = text.LastIndexOf('}');
            File.WriteAllText(path, text.Insert(end, " unknownCustom = { untouched = \"yes\" }\n"));
            _ = CoreApi.AuthorSourceAssets(JsonSerializer.Serialize(new { path, action = "update", updates = new { import_scale = 2.0 } }), "vmdl", false);
            await Assert.That(File.ReadAllText(path).Contains("unknownCustom", StringComparison.Ordinal)).IsTrue();
            await Assert.That(File.ReadAllText(path).Contains("shared.vmat", StringComparison.Ordinal)).IsTrue();
        }
        finally { Directory.Delete(root, true); }
    }
}
