using System.Text.Json.Nodes;

namespace Hammer5Tools.Core.Tests.SmartProps;

public sealed class SmartPropEditorTests
{
    [Test]
    public async Task ComponentTemplatesAndPasteAssignFreshIds()
    {
        var json = CoreApi.EditSmartPropDocument(CoreApi.CreateSmartPropDocument(), [], "add-group");
        json = CoreApi.EditSmartPropDocument(json, ["m_Children", "0"], "add-component", "\"CSmartPropOperation_Translate\"");
        var modifier = JsonNode.Parse(json)!["m_Children"]![0]!["m_Modifiers"]![0]!;
        await Assert.That(modifier["m_vPosition"] is not null).IsTrue();
        var firstId = modifier["m_nElementID"]!.GetValue<int>();
        json = CoreApi.EditSmartPropDocument(json, ["m_Children", "0"], "paste-component", modifier.ToJsonString());
        var modifiers = JsonNode.Parse(json)!["m_Children"]![0]!["m_Modifiers"]!.AsArray();
        await Assert.That(modifiers.Count).IsEqualTo(2);
        await Assert.That(modifiers[1]!["m_nElementID"]!.GetValue<int>() > firstId).IsTrue();
        var rejected = false;
        try
        {
            CoreApi.EditSmartPropDocument(json, ["m_Children", "0"], "add-component", "\"Unknown\"");
        }
        catch (InvalidDataException)
        {
            rejected = true;
        }
        await Assert.That(rejected).IsTrue();
    }

    [Test]
    public async Task DuplicateReassignsDescendantIdsAndPreservesOtherData()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "custom": { "label": "keep me" },
              "m_Children": [{
                "_class": "CSmartPropElement_Group", "m_nElementID": 10,
                "m_Children": [{ "_class": "CSmartPropElement_Model", "m_nElementID": 20, "m_sModelName": "models/test.vmdl" }]
              }]
            }
            """;
        var edited = CoreApi.EditSmartPropDocument(json, ["m_Children", "0"], "duplicate");
        var root = JsonNode.Parse(edited)!;
        await Assert.That(root["m_Children"]!.AsArray().Count).IsEqualTo(2);
        await Assert.That(root["m_Children"]![1]!["m_nElementID"]!.GetValue<int>()).IsEqualTo(21);
        await Assert.That(root["m_Children"]![1]!["m_Children"]![0]!["m_nElementID"]!.GetValue<int>()).IsEqualTo(22);
        await Assert.That(root["custom"]!["label"]!.GetValue<string>()).IsEqualTo("keep me");
        await Assert.That(root["m_Children"]![0]!["m_nElementID"]!.GetValue<int>()).IsEqualTo(10);
    }

    [Test]
    public async Task HierarchyEditsRoundTripThroughCoreKv3()
    {
        var json = CoreApi.EditSmartPropDocument(CoreApi.CreateSmartPropDocument(), [], "add-group");
        json = CoreApi.EditSmartPropDocument(json, ["m_Children", "0"], "add-model");
        json = CoreApi.EditSmartPropDocument(json, ["m_Children", "0", "m_Children", "0"], "duplicate");
        json = CoreApi.EditSmartPropDocument(json, ["m_Children", "0", "m_Children", "1"], "up");
        json = CoreApi.EditSmartPropDocument(json, ["m_Children", "0", "m_Children", "1"], "remove");
        var parsed = JsonNode.Parse(CoreApi.ParseSmartPropDocument(CoreApi.SerializeSmartPropDocument(json)))!;
        var model = parsed["m_Children"]![0]!["m_Children"]![0]!;
        await Assert.That(model["_class"]!.GetValue<string>()).IsEqualTo("CSmartPropElement_Model");
        await Assert.That(model["m_nElementID"]!.GetValue<int>()).IsEqualTo(2);
        await Assert.That(parsed["m_Children"]![0]!["m_Children"]!.AsArray().Count).IsEqualTo(1);
    }

    [Test]
    public async Task SourceRoundTripPreservesNullAndUnknownMetadata()
    {
        const string json = """
            { "generic_data_type": "CSmartPropRoot", "custom": { "unset": null, "text": "hello" }, "m_Children": [] }
            """;
        var parsed = JsonNode.Parse(CoreApi.ParseSmartPropDocument(CoreApi.SerializeSmartPropDocument(json)))!;
        await Assert.That(parsed["custom"]!["unset"] is null).IsTrue();
        await Assert.That(parsed["custom"]!["text"]!.GetValue<string>()).IsEqualTo("hello");
    }

    [Test]
    public async Task SaveRetainsOriginalAndInvalidInputCannotOverwriteIt()
    {
        var folder = Path.Combine(Path.GetTempPath(), "h5t-editor-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(folder);
        try
        {
            var path = Path.Combine(folder, "test.vsmart");
            var original = CoreApi.SerializeSmartPropDocument(CoreApi.CreateSmartPropDocument());
            File.WriteAllText(path, original);
            var edited = CoreApi.EditSmartPropDocument(CoreApi.CreateSmartPropDocument(), [], "add-model");
            var backup = CoreApi.SaveSmartPropDocument(path, edited);
            await Assert.That(File.ReadAllText(backup!)).IsEqualTo(original);
            var saved = File.ReadAllText(path);
            var rejected = false;
            try
            {
                CoreApi.SaveSmartPropDocument(path, "{\"m_Children\":42}");
            }
            catch (InvalidDataException)
            {
                rejected = true;
            }
            await Assert.That(rejected).IsTrue();
            await Assert.That(File.ReadAllText(path)).IsEqualTo(saved);
            await Assert.That(Directory.GetFiles(folder, "*.tmp").Length).IsEqualTo(0);
        }
        finally
        {
            Directory.Delete(folder, true);
        }
    }

    [Test]
    public async Task ExistingPresetsRemainReadable()
    {
        var paths = Directory.GetFiles(Path.Combine(AppContext.BaseDirectory, "Fixtures"), "*.vsmart", SearchOption.AllDirectories);
        await Assert.That(paths.Length > 0).IsTrue();
        foreach (var path in paths)
        {
            var json = CoreApi.ParseSmartPropDocument(File.ReadAllText(path));
            await Assert.That(JsonNode.Parse(json) is JsonObject).IsTrue();
        }
    }

    [Test]
    public async Task PreviewResolvesNestedResourcesFromTheEditedDocument()
    {
        var folder = Path.Combine(Path.GetTempPath(), "h5t-preview-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(folder);
        try
        {
            var path = Path.Combine(folder, "root.vsmart");
            var original = CoreApi.SerializeSmartPropDocument(CoreApi.CreateSmartPropDocument());
            File.WriteAllText(path, original);
            var child = Path.Combine(folder, "child.vsmart");
            File.WriteAllText(child, CoreApi.SerializeSmartPropDocument("""
                {"generic_data_type":"CSmartPropRoot","m_Children":[
                  {"_class":"CSmartPropElement_Model","m_nElementID":7,"m_sModelName":"models/nested.vmdl"}]}
                """));
            var edited = JsonNode.Parse(CoreApi.CreateSmartPropDocument())!.AsObject();
            edited["m_Children"] = new JsonArray(new JsonObject
            {
                ["_class"] = "CSmartPropElement_SmartProp",
                ["m_nElementID"] = 1,
                ["m_sSmartProp"] = child,
            });
            var scene = CoreApi.BuildSmartPropPreview(edited.ToJsonString(), "", sourcePath: path);
            await Assert.That(scene.Instances.Count).IsEqualTo(1);
            await Assert.That(scene.Instances[0].Placement.ModelName).IsEqualTo("models/nested.vmdl");
            await Assert.That(scene.Instances[0].Geometry is null).IsTrue();
            await Assert.That(File.ReadAllText(path)).IsEqualTo(original);
            var loaded = JsonNode.Parse(CoreApi.LoadSmartPropResource(child, ""))!;
            await Assert.That(loaded["m_Children"]![0]!["m_nElementID"]!.GetValue<int>()).IsEqualTo(7);
        }
        finally
        {
            Directory.Delete(folder, true);
        }
    }
}
