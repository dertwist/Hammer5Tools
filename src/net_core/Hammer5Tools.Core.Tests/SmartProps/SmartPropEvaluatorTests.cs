using Hammer5Tools.Core.SmartProps;

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
        var result = SmartPropEvaluator.EvaluateText(text);

        await Assert.That(text).Contains("CSmartPropRoot");
        await Assert.That(text).Contains("_class");
        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(1);
        await Assert.That(result.Models[0].ElementId).IsEqualTo(9);
        await Assert.That(result.Models[0].ModelName).IsEqualTo("models/roundtrip.vmdl");
    }
}
