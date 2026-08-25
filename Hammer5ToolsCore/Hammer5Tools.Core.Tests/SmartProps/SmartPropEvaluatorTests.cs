using Hammer5Tools.Core.Format.SmartProps;

namespace Hammer5Tools.Core.Tests.SmartProps;

public sealed class SmartPropEvaluatorTests
{
    [Test]
    public async Task EvaluatesUncompiledEditorDataThroughVrf()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [
                {
                  "_class": "CSmartPropElement_Model",
                  "m_nElementID": 7,
                  "m_sModelName": "models/example.vmdl"
                }
              ]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(1);
        await Assert.That(result.Models[0].ElementId).IsEqualTo(7);
        await Assert.That(result.Models[0].ModelName).IsEqualTo("models/example.vmdl");
    }

    [Test]
    public async Task ReportsMalformedEditorData()
    {
        var result = SmartPropEvaluator.EvaluateJson("{");

        await Assert.That(result.Models).IsEmpty();
        await Assert.That(result.Diagnostics).Count().IsEqualTo(1);
        await Assert.That(result.Diagnostics[0].Code).IsEqualTo("smartprop.invalid_json");
    }

    [Test]
    public async Task SerializedDocumentRoundTripsThroughVrfParser()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [
                {
                  "_class": "CSmartPropElement_Model",
                  "m_nElementID": 9,
                  "m_sModelName": "models/roundtrip.vmdl"
                }
              ]
            }
            """;

        var text = SmartPropDocumentSerializer.SerializeJson(json);
        var roundTripJson = SmartPropDocumentSerializer.DeserializeText(text);
        var result = SmartPropEvaluator.EvaluateText(text);

        await Assert.That(text).Contains("CSmartPropRoot");
        await Assert.That(text).Contains("_class");
        await Assert.That(roundTripJson).Contains("models/roundtrip.vmdl");
        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(1);
        await Assert.That(result.Models[0].ElementId).IsEqualTo(9);
        await Assert.That(result.Models[0].ModelName).IsEqualTo("models/roundtrip.vmdl");
    }

    [Test]
    public async Task ResolvesNestedSmartPropDocuments()
    {
        const string root = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_SmartProp",
                "m_nElementID": 4,
                "m_sSmartProp": "smartprops/nested.vsmart"
              }]
            }
            """;
        const string nested = """
            {
              "smartprops/nested.vsmart": {
                "generic_data_type": "CSmartPropRoot",
                "m_Children": [{
                  "_class": "CSmartPropElement_Model",
                  "m_nElementID": 8,
                  "m_sModelName": "models/nested.vmdl"
                }]
              }
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(root, nested);

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(1);
        await Assert.That(result.Models[0].ElementId).IsEqualTo(8);
        await Assert.That(result.Models[0].ModelName).IsEqualTo("models/nested.vmdl");
    }

    [Test]
    public async Task HonorsTheConfiguredNestedResourceDepth()
    {
        const string root = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_SmartProp",
                "m_nElementID": 4,
                "m_sSmartProp": "smartprops/nested.vsmart"
              }]
            }
            """;
        const string nested = """
            {
              "smartprops/nested.vsmart": {
                "generic_data_type": "CSmartPropRoot",
                "m_Children": [{
                  "_class": "CSmartPropElement_SmartProp",
                  "m_nElementID": 8,
                  "m_sSmartProp": "smartprops/leaf.vsmart"
                }]
              },
              "smartprops/leaf.vsmart": {
                "generic_data_type": "CSmartPropRoot",
                "m_Children": [{
                  "_class": "CSmartPropElement_Model",
                  "m_nElementID": 12,
                  "m_sModelName": "models/leaf.vmdl"
                }]
              }
            }
            """;
        var options = new SmartPropEvaluationOptions(maximumDepth: 1);

        var result = SmartPropEvaluator.EvaluateJson(root, nested, options);

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).IsEmpty();
    }

    [Test]
    public async Task RejectsNonPositiveNestedResourceDepth()
    {
        var options = new SmartPropEvaluationOptions(maximumDepth: 0);

        await Assert.That(() => SmartPropEvaluator.EvaluateJson("{}", options))
            .Throws<ArgumentOutOfRangeException>();
    }

    [Test]
    public async Task ProductionFixturePreservesEvaluationAcrossSerialization()
    {
        var fixturePath = Directory.GetFiles(
            Path.Combine(AppContext.BaseDirectory, "Fixtures"),
            "example_expressions.vsmart",
            SearchOption.AllDirectories).Single();
        var sourceText = await File.ReadAllTextAsync(fixturePath);

        var json = SmartPropDocumentSerializer.DeserializeText(sourceText);
        var serializedText = SmartPropDocumentSerializer.SerializeJson(json);
        var sourceResult = SmartPropEvaluator.EvaluateText(sourceText);
        var serializedResult = SmartPropEvaluator.EvaluateText(serializedText);

        await Assert.That(sourceResult.Diagnostics).IsEmpty();
        await Assert.That(serializedResult.Diagnostics).IsEmpty();
        await Assert.That(serializedResult.Models).Count().IsEqualTo(sourceResult.Models.Count);
    }

    [Test]
    public async Task AllEditorPresetsPreserveEvaluationAcrossSerialization()
    {
        var fixtureDirectory = Path.Combine(AppContext.BaseDirectory, "Fixtures");
        var fixturePaths = Directory.GetFiles(fixtureDirectory, "*.vsmart", SearchOption.AllDirectories);

        await Assert.That(fixturePaths.Length).IsGreaterThan(1);
        foreach (var fixturePath in fixturePaths)
        {
            var sourceText = await File.ReadAllTextAsync(fixturePath);
            var json = SmartPropDocumentSerializer.DeserializeText(sourceText);
            var serializedText = SmartPropDocumentSerializer.SerializeJson(json);
            var sourceResult = SmartPropEvaluator.EvaluateText(sourceText);
            var serializedResult = SmartPropEvaluator.EvaluateText(serializedText);

            await Assert.That(sourceResult.Diagnostics).IsEmpty();
            await Assert.That(serializedResult.Diagnostics).IsEmpty();
            await Assert.That(serializedResult.Models).Count().IsEqualTo(sourceResult.Models.Count);
        }
    }
}
