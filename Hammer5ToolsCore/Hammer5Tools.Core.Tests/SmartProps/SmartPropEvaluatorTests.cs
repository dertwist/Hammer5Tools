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
    public async Task EvaluatesEditorWidgetsAtTheirModifierPosition()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_Group",
                "m_nElementID": 4,
                "m_Modifiers": [
                  {
                    "_class": "CSmartPropOperation_Translate",
                    "m_vPosition": { "m_Components": [12, 3, -2] }
                  },
                  {
                    "_class": "CSmartPropOperation_CreateLocator",
                    "m_nElementID": 9,
                    "m_vOffset": { "m_Components": [1, 2, 3] },
                    "m_flDisplayScale": 2
                  },
                  {
                    "_class": "CSmartPropOperation_Translate",
                    "m_vPosition": { "m_Components": [100, 0, 0] }
                  }
                ]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Widgets).Count().IsEqualTo(2);
        var group = result.Widgets.Single(widget => widget.Type == "group");
        await Assert.That(group.ElementId).IsEqualTo(4);
        await Assert.That(group.Transform.M41).IsEqualTo(112f);
        await Assert.That(group.Transform.M42).IsEqualTo(3f);
        await Assert.That(group.Transform.M43).IsEqualTo(-2f);

        var widget = result.Widgets.Single(widget => widget.Type == "locator");
        await Assert.That(widget.Type).IsEqualTo("locator");
        await Assert.That(widget.ElementId).IsEqualTo(9);
        await Assert.That(widget.Transform.M41).IsEqualTo(12f);
        await Assert.That(widget.Transform.M42).IsEqualTo(3f);
        await Assert.That(widget.Transform.M43).IsEqualTo(-2f);
        await Assert.That(widget.Offset).IsEqualTo(new System.Numerics.Vector3(1f, 2f, 3f));
        await Assert.That(widget.Scale).IsEqualTo(2f);
    }

    [Test]
    public async Task EvaluatesPickOneEditorHandle()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_PickOne",
                "m_nElementID": 14,
                "m_HandleShape": "DIAMOND",
                "m_HandleSize": 11,
                "m_vHandleOffset": [4, 5, 6],
                "m_Children": []
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Widgets).Count().IsEqualTo(1);
        await Assert.That(result.Widgets[0].Type).IsEqualTo("pickone");
        await Assert.That(result.Widgets[0].ElementId).IsEqualTo(14);
        await Assert.That(result.Widgets[0].Shape).IsEqualTo("DIAMOND");
        await Assert.That(result.Widgets[0].Size).IsEqualTo(11f);
    }

    [Test]
    public async Task BendsModelAlongQuarterCircleWithAutoRadius()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_BendDeformer",
                "m_nElementID": 1,
                "m_vSize": { "m_Components": [100, 0, 0] },
                "m_flBendAngle": 90,
                "m_flBendPoint": 0,
                "m_Children": [{
                  "_class": "CSmartPropElement_Model",
                  "m_nElementID": 2,
                  "m_sModelName": "models/segment.vmdl",
                  "m_Modifiers": [{
                    "_class": "CSmartPropOperation_Translate",
                    "m_vPosition": { "m_Components": [100, 0, 0] }
                  }]
                }]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        // Auto radius R = sizeX / (angle in radians) = 100 / (pi/2). The child sits at the
        // far end of the deformer's local X (pivot at bendPoint=0), so it sweeps the full
        // 90 degrees: it lands at (R*sin(90), R - R*cos(90), 0) = (R, R, 0).
        var expected = 100f / (MathF.PI / 2f);
        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(1);
        await Assert.That(result.Models[0].Transform.M41).IsEqualTo(expected).Within(0.01f);
        await Assert.That(result.Models[0].Transform.M42).IsEqualTo(expected).Within(0.01f);
        await Assert.That(result.Models[0].Transform.M43).IsEqualTo(0f).Within(0.01f);
    }

    [Test]
    public async Task DisabledDeformationLeavesModelStraight()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_BendDeformer",
                "m_nElementID": 1,
                "m_bDeformationEnabled": false,
                "m_vSize": { "m_Components": [100, 0, 0] },
                "m_flBendAngle": 90,
                "m_Children": [{
                  "_class": "CSmartPropElement_Model",
                  "m_nElementID": 2,
                  "m_sModelName": "models/segment.vmdl",
                  "m_Modifiers": [{
                    "_class": "CSmartPropOperation_Translate",
                    "m_vPosition": { "m_Components": [100, 0, 0] }
                  }]
                }]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models[0].Transform.M41).IsEqualTo(100f).Within(0.01f);
        await Assert.That(result.Models[0].Transform.M42).IsEqualTo(0f).Within(0.01f);
    }

    [Test]
    public async Task ExplicitBendRadiusOverridesAutoRadius()
    {
        var childX = 40f * MathF.PI / 2f;
        var json = $$"""
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_BendDeformer",
                "m_nElementID": 1,
                "m_vSize": { "m_Components": [100, 0, 0] },
                "m_flBendAngle": 90,
                "m_flBendPoint": 0,
                "m_flBendRadius": 40,
                "m_Children": [{
                  "_class": "CSmartPropElement_Model",
                  "m_nElementID": 2,
                  "m_sModelName": "models/segment.vmdl",
                  "m_Modifiers": [{
                    "_class": "CSmartPropOperation_Translate",
                    "m_vPosition": { "m_Components": [{{childX}}, 0, 0] }
                  }]
                }]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        // With an explicit radius, phi = x / radius directly (independent of m_vSize), so a
        // child placed at radius*(pi/2) sweeps exactly 90 degrees at that fixed radius.
        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models[0].Transform.M41).IsEqualTo(40f).Within(0.01f);
        await Assert.That(result.Models[0].Transform.M42).IsEqualTo(40f).Within(0.01f);
    }

    [Test]
    public async Task SkipsBendDeformerNestedInsidePlaceOnPath()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_PlaceOnPath",
                "m_nElementID": 1,
                "m_DefaultPath": [[0, 0, 0], [100, 0, 0]],
                "m_flSpacing": 1000,
                "m_Children": [{
                  "_class": "CSmartPropElement_BendDeformer",
                  "m_nElementID": 2,
                  "m_vSize": { "m_Components": [100, 0, 0] },
                  "m_flBendAngle": 90,
                  "m_Children": [{
                    "_class": "CSmartPropElement_Model",
                    "m_nElementID": 3,
                    "m_sModelName": "models/segment.vmdl",
                    "m_Modifiers": [{
                      "_class": "CSmartPropOperation_Translate",
                      "m_vPosition": { "m_Components": [100, 0, 0] }
                    }]
                  }]
                }]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        // A BendDeformer under a repeating PlaceOnPath can't be represented by one probed
        // frame, so it's left exactly as VRF's unbent placement gives it (Y stays 0 — a bent
        // result would have moved it off-axis).
        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(1);
        await Assert.That(result.Models[0].Transform.M42).IsEqualTo(0f).Within(0.01f);
    }

    [Test]
    public async Task AppliesNestedBendDeformersInnerThenOuter()
    {
        const string innerModel = """
            {
              "_class": "CSmartPropElement_Model",
              "m_nElementID": 2,
              "m_sModelName": "models/segment.vmdl",
              "m_Modifiers": [{
                "_class": "CSmartPropOperation_Translate",
                "m_vPosition": { "m_Components": [100, 0, 0] }
              }]
            }
            """;
        var innerOnlyJson = $$"""
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_BendDeformer",
                "m_nElementID": 10,
                "m_vSize": { "m_Components": [100, 0, 0] },
                "m_flBendAngle": 90,
                "m_Children": [{{innerModel}}]
              }]
            }
            """;
        var nestedJson = $$"""
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_BendDeformer",
                "m_nElementID": 20,
                "m_vSize": { "m_Components": [200, 0, 0] },
                "m_flBendAngle": 45,
                "m_Children": [{
                  "_class": "CSmartPropElement_BendDeformer",
                  "m_nElementID": 10,
                  "m_vSize": { "m_Components": [100, 0, 0] },
                  "m_flBendAngle": 90,
                  "m_Children": [{{innerModel}}]
                }]
              }]
            }
            """;

        var innerOnly = SmartPropEvaluator.EvaluateJson(innerOnlyJson).Models.Single(m => m.ElementId == 2);
        var nested = SmartPropEvaluator.EvaluateJson(nestedJson).Models.Single(m => m.ElementId == 2);

        // The outer deformer must further bend the already inner-bent position, not replace
        // or ignore it — assert the nested result visibly differs from the inner-only one.
        var delta = System.Numerics.Vector3.Distance(
            new(innerOnly.Transform.M41, innerOnly.Transform.M42, innerOnly.Transform.M43),
            new(nested.Transform.M41, nested.Transform.M42, nested.Transform.M43));
        await Assert.That(delta).IsGreaterThan(1f);
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
                  "m_sModelName": "models/nested.vmdl",
                  "m_Modifiers": [{
                    "_class": "CSmartPropOperation_CreateLocator",
                    "m_nElementID": 13
                  }]
                }]
              }
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(root, nested);

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(1);
        await Assert.That(result.Models[0].ElementId).IsEqualTo(8);
        await Assert.That(result.Models[0].ModelName).IsEqualTo("models/nested.vmdl");
        await Assert.That(result.Widgets).Count().IsEqualTo(1);
        await Assert.That(result.Widgets[0].ElementId).IsEqualTo(13);
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
        var editorResult = SmartPropEvaluator.EvaluateJson(json);
        var serializedResult = SmartPropEvaluator.EvaluateText(serializedText);

        await Assert.That(sourceResult.Diagnostics).IsEmpty();
        await Assert.That(serializedResult.Diagnostics).IsEmpty();
        await Assert.That(editorResult.Widgets).IsNotEmpty();
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
