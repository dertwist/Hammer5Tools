namespace Hammer5Tools.Core.Tests;

using Hammer5Tools.Core.Format.SmartProps;

public class SmartPropEvaluationTests
{
    [Test]
    public async Task ModelsRetainInheritedTransforms()
    {
        var result = SmartPropEvaluator.EvaluateJson("""
            {
              "_class": "CSmartPropElement_Group", "m_nElementID": 1,
              "m_Modifiers": [{ "_class": "CSmartPropOperation_Translate", "m_vPosition": [100, 20, 30] }],
              "m_Children": [{ "_class": "CSmartPropElement_Model", "m_nElementID": 7, "m_sModelName": "models/example.vmdl" }]
            }
            """);

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models.Count).IsEqualTo(1);
        await Assert.That(result.Models[0].ElementId).IsEqualTo(7);
        await Assert.That(result.Models[0].ModelName).IsEqualTo("models/example.vmdl");
        await Assert.That(result.Models[0].Transform.Translation).IsEqualTo(new Vector3(100, 20, 30));
    }

    [Test]
    public async Task NestedDocumentsStopCyclesWithoutDiscardingModels()
    {
        var result = SmartPropEvaluator.EvaluateJson(
            """{ "_class": "CSmartPropElement_SmartProp", "m_nElementID": 1, "m_sSmartProp": "nested.vsmart" }""",
            """
            {
              "nested.vsmart": {
                "_class": "CSmartPropElement_Group", "m_nElementID": 2,
                "m_Children": [
                  { "_class": "CSmartPropElement_Model", "m_nElementID": 3, "m_sModelName": "models/nested.vmdl" },
                  { "_class": "CSmartPropElement_SmartProp", "m_nElementID": 4, "m_sSmartProp": "nested.vsmart" }
                ]
              }
            }
            """);

        await Assert.That(result.Models.Count).IsEqualTo(1);
        await Assert.That(result.Models[0].ModelName).IsEqualTo("models/nested.vmdl");
    }

    [Test]
    public async Task PathIntervalsKeepTheirPlacementOrder()
    {
        var result = SmartPropEvaluator.EvaluateJson("""
            {
              "_class": "CSmartPropElement_PlaceOnPath", "m_nElementID": 1,
              "m_flSpacing": 5, "m_DefaultPath": [[0, 0, 0], [10, 0, 0]],
              "m_Children": [{ "_class": "CSmartPropElement_Model", "m_nElementID": 2, "m_sModelName": "models/path.vmdl" }]
            }
            """);

        await Assert.That(result.Models.Count).IsEqualTo(3);
        await Assert.That(result.Models[0].Transform.Translation).IsEqualTo(Vector3.Zero);
        await Assert.That(result.Models[1].Transform.Translation).IsEqualTo(new Vector3(5, 0, 0));
        await Assert.That(result.Models[2].Transform.Translation).IsEqualTo(new Vector3(10, 0, 0));
    }
}
