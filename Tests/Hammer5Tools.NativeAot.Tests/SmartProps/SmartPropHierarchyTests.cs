using System.Text.Json;
using System.Text.Json.Nodes;

namespace Hammer5Tools.Core.Tests.SmartProps;

public sealed class SmartPropHierarchyTests
{
    private const string Document = """
        {"generic_data_type":"CSmartPropRoot","custom":"keep","m_Children":[
          {"_class":"CSmartPropElement_Group","m_nElementID":1,"m_sLabel":"A","m_Children":[
            {"_class":"CSmartPropElement_Model","m_nElementID":2,"m_sLabel":"a","m_nReferenceID":99},
            {"_class":"CSmartPropElement_Model","m_nElementID":3,"m_sLabel":"b"},
            {"_class":"CSmartPropElement_Model","m_nElementID":4,"m_sLabel":"c"}]},
          {"_class":"CSmartPropElement_Group","m_nElementID":5,"m_sLabel":"B","m_Children":[]}]}
        """;

    private static string[] Path(params int[] indices) => indices.SelectMany(index => new[] { "m_Children", index.ToString(System.Globalization.CultureInfo.InvariantCulture) }).ToArray();
    private static JsonNode Edit(string document, string action, string[][] paths, string[]? target = null, string position = "inside", bool copy = false, string? text = null) =>
        JsonNode.Parse(CoreApi.EditSmartPropDocument(document, [], "hierarchy", JsonSerializer.Serialize(new { action, paths, target = target ?? [], position, copy, text })))!;

    [Test]
    public async Task MultiMovePreservesOrderIdsAndMetadata()
    {
        var moved = Edit(Document, "move", [Path(0, 0), Path(0, 1)], Path(1));
        await Assert.That(moved["m_Children"]![0]!["m_Children"]!.AsArray().Count).IsEqualTo(1);
        var children = moved["m_Children"]![1]!["m_Children"]!.AsArray();
        await Assert.That(children[0]!["m_nElementID"]!.GetValue<int>()).IsEqualTo(2);
        await Assert.That(children[1]!["m_nElementID"]!.GetValue<int>()).IsEqualTo(3);
        await Assert.That(children[0]!["m_nReferenceID"]!.GetValue<int>()).IsEqualTo(99);
        await Assert.That(moved["custom"]!.GetValue<string>()).IsEqualTo("keep");
    }

    [Test]
    public async Task MultiReorderUsesTheOriginalDropPosition()
    {
        var moved = Edit(Document, "move", [Path(0, 0), Path(0, 1)], Path(0, 2), "after");
        var labels = moved["m_Children"]![0]!["m_Children"]!.AsArray().Select(node => node!["m_sLabel"]!.GetValue<string>());
        await Assert.That(string.Join(',', labels)).IsEqualTo("c,a,b");
        var up = Edit(Document, "up", [Path(0, 1), Path(0, 2)]);
        await Assert.That(up["m_Children"]![0]!["m_Children"]![0]!["m_sLabel"]!.GetValue<string>()).IsEqualTo("b");
    }

    [Test]
    public async Task SelectedDescendantsAreNotCopiedOrDeletedTwice()
    {
        var copied = JsonNode.Parse(CoreApi.ParseSmartPropDocument(CoreApi.CopySmartPropHierarchy(Document, [Path(0), Path(0, 0)])))!;
        await Assert.That(copied["m_Children"]!.AsArray().Count).IsEqualTo(1);
        var duplicated = Edit(Document, "duplicate", [Path(0), Path(0, 0)]);
        await Assert.That(duplicated["m_Children"]!.AsArray().Count).IsEqualTo(3);
        await Assert.That(duplicated["m_Children"]![1]!["m_nElementID"]!.GetValue<int>()).IsEqualTo(6);
        await Assert.That(duplicated["m_Children"]![1]!["m_Children"]![0]!["m_nElementID"]!.GetValue<int>()).IsEqualTo(7);
        var removed = Edit(Document, "remove", [Path(0), Path(0, 0)]);
        await Assert.That(removed["m_Children"]!.AsArray().Count).IsEqualTo(1);
    }

    [Test]
    public async Task GroupAndClipboardPasteKeepSubtreesAndAssignNewIds()
    {
        var grouped = Edit(Document, "group", [Path(0, 0), Path(1)]);
        var group = grouped["m_Children"]![1]!;
        await Assert.That(group["_class"]!.GetValue<string>()).IsEqualTo("CSmartPropElement_Group");
        await Assert.That(group["m_Children"]!.AsArray().Count).IsEqualTo(2);
        var clipboard = CoreApi.CopySmartPropHierarchy(Document, [Path(0, 0)]);
        var pasted = Edit(Document, "paste", [], Path(0, 1), text: clipboard);
        var child = pasted["m_Children"]![0]!["m_Children"]![3]!;
        await Assert.That(child["m_nElementID"]!.GetValue<int>()).IsEqualTo(6);
        await Assert.That(child["m_nReferenceID"]!.GetValue<int>()).IsEqualTo(99);
    }

    [Test]
    public async Task InvalidCyclesAndLeafParentingAreRejected()
    {
        foreach (var (paths, target, position) in new[]
        {
            (new[] { Path(0) }, Path(0, 0), "inside"),
            (new[] { Path(0) }, Path(0, 0), "before"),
            (new[] { Path(0, 0) }, Path(0, 1), "inside"),
            (new[] { Path(0) }, Path(0), "after")
        })
        {
            var rejected = false;
            try
            {
                Edit(Document, "move", paths, target, position);
            }
            catch (InvalidDataException)
            {
                rejected = true;
            }
            await Assert.That(rejected).IsTrue();
        }
        await Assert.That(JsonNode.Parse(Document)!["m_Children"]!.AsArray().Count).IsEqualTo(2);
    }
}
