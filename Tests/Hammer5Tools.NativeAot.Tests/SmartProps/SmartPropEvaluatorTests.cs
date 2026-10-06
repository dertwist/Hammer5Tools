using Hammer5Tools.Core.Format.SmartProps;

namespace Hammer5Tools.Core.Tests.SmartProps;

public sealed class SmartPropEvaluatorTests
{
    [Test]
    public async Task DeserializedTextPreservesNumericLookingStringsAsStrings()
    {
        // The KV3 text parser types a value by content, not by the source grammar's quotes â€”
        // a quoted "1" comes back exactly as typed (Int32) as an unquoted 1 would. Any KV3
        // property whose value is semantically always a string (m_Expression, in particular â€”
        // see SmartPropJsonConverter's guard on the way back) must not lose that distinction
        // when this deserializer hands it to the GUI/Core as JSON.
        const string text = """
            <!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
            {
                a = "1"
                b = "hello"
                c = 1
                m_Expression = "1"
            }
            """;

        var json = SmartPropDocumentSerializer.DeserializeText(text);

        // Plain properties keep the parser's own (content-based) typing â€” only m_Expression,
        // which is always expression source text, is special-cased back to a string.
        await Assert.That(json).Contains("\"a\":1");
        await Assert.That(json).Contains("\"b\":\"hello\"");
        await Assert.That(json).Contains("\"c\":1");
        await Assert.That(json).Contains("\"m_Expression\":\"1\"");
    }

    [Test]
    public async Task LinearScaleResolvesCorrectlyAlongsideNumericLookingSiblingExpressions()
    {
        // Reproduces a real authored file: m_vModelScale's other components are written as
        // m_Expression = "1" (a habit of Hammer's own editor). Round-tripped through KV3 text,
        // those come back as JSON numbers (see DeserializedTextPreservesNumericLookingStringsAsStrings),
        // which used to make VRF's resolver silently default the *entire* m_vModelScale vector
        // to (1,1,1) â€” masking a correctly-evaluated LinearScale() in the very same array.
        const string text = """
            <!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
            {
                generic_data_type = "CSmartPropRoot"
                m_Children =
                [
                    {
                        _class = "CSmartPropElement_FitOnLine"
                        m_nElementID = 1
                        m_vStart = { m_Components = [0.0, 0.0, 0.0] }
                        m_vEnd = { m_Components = [200.0, 0.0, 0.0] }
                        m_Children = [
                        {
                            _class = "CSmartPropElement_PickOne"
                            m_nElementID = 2
                            m_SelectionCriteria = [
                            {
                                _class = "CSmartPropSelectionCriteria_LinearLength"
                                m_bAllowScale = true
                                m_flLength = 128.0
                                m_flMinLength = 64.0
                                m_flMaxLength = 256.0
                            }]
                            m_Children = [
                            {
                                _class = "CSmartPropElement_Model"
                                m_nElementID = 3
                                m_sModelName = "models/segment.vmdl"
                                m_vModelScale =
                                {
                                    m_Components = [
                                    { m_Expression = "LinearScale()" },
                                    { m_Expression = "1" },
                                    { m_Expression = "1" }]
                                }
                            }]
                        }]
                    }
                ]
            }
            """;

        var result = SmartPropEvaluator.EvaluateText(text);

        // sizer length 200 over an authored 128-unit segment: scale = 200 / 128 = 1.5625.
        await Assert.That(result.Diagnostics).IsEmpty();
        var scaleX = MathF.Sqrt(
            (result.Models[0].Transform.M11 * result.Models[0].Transform.M11)
            + (result.Models[0].Transform.M12 * result.Models[0].Transform.M12)
            + (result.Models[0].Transform.M13 * result.Models[0].Transform.M13));
        await Assert.That(scaleX).IsEqualTo(1.5625f).Within(0.001f);
    }

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
        await Assert.That(result.Widgets).Count().IsEqualTo(2);
        var element = result.Widgets.Single(widget => widget.Type == "element");
        await Assert.That(element.ElementId).IsEqualTo(14);

        var pickOne = result.Widgets.Single(widget => widget.Type == "pickone");
        await Assert.That(pickOne.ElementId).IsEqualTo(14);
        await Assert.That(pickOne.Shape).IsEqualTo("DIAMOND");
        await Assert.That(pickOne.Size).IsEqualTo(11f);
    }

    [Test]
    public async Task BendsRigidModelAlongQuarterCircleWithAutoRadius()
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
                  "m_bRigidDeformation": true,
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

        // At the box's far end the local frame has swept the full 90 degrees too: the model's
        // own local X axis (unrotated, so originally (1,0,0)) now points along world Y.
        await Assert.That(result.Models[0].Transform.M11).IsEqualTo(0f).Within(0.01f);
        await Assert.That(result.Models[0].Transform.M12).IsEqualTo(1f).Within(0.01f);
        await Assert.That(result.Models[0].Transform.M13).IsEqualTo(0f).Within(0.01f);

        // Opted out of mesh deformation via m_bRigidDeformation â€” no cage payload attached.
        await Assert.That(result.Models[0].Deformer).IsNull();
    }

    [Test]
    public async Task NonRigidModelUnderBendKeepsStraightTransformAndGetsDeformerCage()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_BendDeformer",
                "m_nElementID": 1,
                "m_vSize": { "m_Components": [100, 20, 20] },
                "m_flBendAngle": 90,
                "m_flBendPoint": 0,
                "m_Children": [{
                  "_class": "CSmartPropElement_Model",
                  "m_nElementID": 2,
                  "m_sModelName": "models/pipe.vmdl",
                  "m_Modifiers": [{
                    "_class": "CSmartPropOperation_Translate",
                    "m_vPosition": { "m_Components": [50, 0, 0] }
                  }]
                }]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        // Default (no m_bRigidDeformation, no RigidDeformation modifier): the instance transform
        // is left exactly as VRF's raw, unbent placement â€” the viewport warps the mesh instead.
        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(1);
        var model = result.Models[0];
        await Assert.That(model.Transform.M41).IsEqualTo(50f).Within(0.01f);
        await Assert.That(model.Transform.M42).IsEqualTo(0f).Within(0.01f);
        await Assert.That(model.Transform.M43).IsEqualTo(0f).Within(0.01f);

        await Assert.That(model.Deformer).IsNotNull();
        var deformer = model.Deformer!;
        await Assert.That(deformer.ControlPoints.Count).IsEqualTo(8);
        await Assert.That(deformer.Midpoints.Count).IsEqualTo(8);
        await Assert.That(deformer.Size.X).IsEqualTo(100f).Within(0.01f);
        // The deformer frame and volume frame are both identity here (no modifiers on the
        // deformer, no m_vOrigin/m_vAngles), so the far corner (x=sizeX) should land exactly
        // where the rigid-path math already proved it does: (R, R, 0) for a 90-degree auto bend.
        var expected = 100f / (MathF.PI / 2f);
        var farCorner = deformer.ControlPoints[4];
        await Assert.That(farCorner.X).IsEqualTo(expected).Within(0.01f);
        await Assert.That(farCorner.Y).IsEqualTo(expected).Within(0.01f);
    }

    [Test]
    public async Task RigidDeformationModifierOptsOutOfMeshDeformation()
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
                  "m_Modifiers": [
                    {
                      "_class": "CSmartPropOperation_Translate",
                      "m_vPosition": { "m_Components": [100, 0, 0] }
                    },
                    {
                      "_class": "CSmartPropOperation_RigidDeformation",
                      "m_bEnabled": true
                    }
                  ]
                }]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        var expected = 100f / (MathF.PI / 2f);
        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models[0].Transform.M41).IsEqualTo(expected).Within(0.01f);
        await Assert.That(result.Models[0].Deformer).IsNull();
    }

    [Test]
    public async Task HandlesBendAngleBeyondAFullTurnWithoutNaN()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_BendDeformer",
                "m_nElementID": 1,
                "m_vSize": { "m_Components": [100, 20, 20] },
                "m_flBendAngle": 630,
                "m_flBendPoint": 0.5,
                "m_Children": [{
                  "_class": "CSmartPropElement_Model",
                  "m_nElementID": 2,
                  "m_sModelName": "models/segment.vmdl",
                  "m_Modifiers": [{
                    "_class": "CSmartPropOperation_Translate",
                    "m_vPosition": { "m_Components": [77, 5, 3] }
                  }]
                }]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        // A single Bezier segment per edge can't represent a nearly-two-turn bend exactly (the
        // authored range goes up to 720 degrees), but it must stay finite and well-formed â€”
        // this only guards against the handle-length formula blowing up near a full turn.
        await Assert.That(result.Diagnostics).IsEmpty();
        var transform = result.Models[0].Transform;
        await Assert.That(float.IsFinite(transform.M41)).IsTrue();
        await Assert.That(float.IsFinite(transform.M42)).IsTrue();
        await Assert.That(float.IsFinite(transform.M43)).IsTrue();
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
        const string json = """
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
                  "m_bRigidDeformation": true,
                  "m_Modifiers": [{
                    "_class": "CSmartPropOperation_Translate",
                    "m_vPosition": { "m_Components": [100, 0, 0] }
                  }]
                }]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        // The swept angle is always bendAngle * (x/sizeX) â€” independent of radius â€” so a child
        // at the box's far end (x = sizeX) still sweeps exactly 90 degrees; only the radius (and
        // so the arc's length) is different from the auto-radius case.
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
        // frame, so it's left exactly as VRF's unbent placement gives it (Y stays 0 â€” a bent
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
              "m_bRigidDeformation": true,
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
        // or ignore it â€” assert the nested result visibly differs from the inner-only one.
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
        await Assert.That(result.Widgets).Count().IsEqualTo(2);
        await Assert.That(result.Widgets.Any(w => w.ElementId == 13 && w.Type == "locator")).IsTrue();
        await Assert.That(result.Widgets.Any(w => w.ElementId == 4 && w.Type == "element")).IsTrue();
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

    [Test]
    public async Task MidpointDeformerAppliesFullOffsetAtMidpointAndNoneBeyondRadius()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_MidpointDeformer",
                "m_nElementID": 1,
                "m_vStart": { "m_Components": [0, 0, 0] },
                "m_vEnd": { "m_Components": [200, 0, 0] },
                "m_fRadius": 50,
                "m_fFalloff": 1,
                "m_vOffset": { "m_Components": [0, 0, 40] },
                "m_Children": [
                  {
                    "_class": "CSmartPropElement_Model",
                    "m_nElementID": 2,
                    "m_sModelName": "models/at_midpoint.vmdl",
                    "m_Modifiers": [{
                      "_class": "CSmartPropOperation_Translate",
                      "m_vPosition": { "m_Components": [100, 0, 0] }
                    }]
                  },
                  {
                    "_class": "CSmartPropElement_Model",
                    "m_nElementID": 3,
                    "m_sModelName": "models/far.vmdl",
                    "m_Modifiers": [{
                      "_class": "CSmartPropOperation_Translate",
                      "m_vPosition": { "m_Components": [-500, 0, 0] }
                    }]
                  }
                ]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);
        var atMidpoint = result.Models.Single(model => model.ElementId == 2);
        var far = result.Models.Single(model => model.ElementId == 3);

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(atMidpoint.Transform.M43).IsEqualTo(40f).Within(0.01f);
        await Assert.That(far.Transform.M43).IsEqualTo(0f).Within(0.01f);
    }

    [Test]
    public async Task GridExpandsIntoWTimesLInstancesCenteredOnOrigin()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_Layout2DGrid",
                "m_nElementID": 1,
                "m_nCountW": 3,
                "m_nCountL": 3,
                "m_flSpacingWidth": 100,
                "m_flSpacingLength": 100,
                "m_Children": [{
                  "_class": "CSmartPropElement_Model",
                  "m_nElementID": 2,
                  "m_sModelName": "models/grid.vmdl"
                }]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(9);
        await Assert.That(result.Models.Select(model => model.Transform.M41)).Contains(-100f);
        await Assert.That(result.Models.Select(model => model.Transform.M41)).Contains(100f);
        await Assert.That(result.Models.Any(model => model.Transform.M41 == 0f && model.Transform.M42 == 0f)).IsTrue();
    }

    [Test]
    public async Task PlaceInSphereScattersWithinRadiusShell()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_PlaceInSphere",
                "m_nElementID": 1,
                "m_nCountMin": 6,
                "m_nCountMax": 6,
                "m_flPositionRadiusInner": 50,
                "m_flPositionRadiusOuter": 100,
                "m_Children": [{
                  "_class": "CSmartPropElement_Model",
                  "m_nElementID": 2,
                  "m_sModelName": "models/sphere.vmdl"
                }]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(6);
        foreach (var model in result.Models)
        {
            var distance = new System.Numerics.Vector3(model.Transform.M41, model.Transform.M42, model.Transform.M43).Length();
            await Assert.That(distance).IsGreaterThanOrEqualTo(49.9f);
            await Assert.That(distance).IsLessThanOrEqualTo(100.1f);
        }
    }

    [Test]
    public async Task PlaceMultipleExpandsIntoCountInstancesWithVaryingRandomOffsets()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_PlaceMultiple",
                "m_nElementID": 1,
                "m_nCount": 5,
                "m_Children": [{
                  "_class": "CSmartPropElement_Model",
                  "m_nElementID": 2,
                  "m_sModelName": "models/multi.vmdl",
                  "m_Modifiers": [{
                    "_class": "CSmartPropOperation_RandomOffset",
                    "m_vRandomPositionMin": { "m_Components": [-100, -100, 0] },
                    "m_vRandomPositionMax": { "m_Components": [100, 100, 0] }
                  }]
                }]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);
        var distinctPositions = result.Models
            .Select(model => (model.Transform.M41, model.Transform.M42))
            .Distinct()
            .Count();

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(5);
        await Assert.That(distinctPositions).IsGreaterThan(1);
    }

    [Test]
    public async Task PlaceMultipleWithoutCountFieldStillEmitsOneInstance()
    {
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_PlaceMultiple",
                "m_nElementID": 1,
                "m_Children": [{
                  "_class": "CSmartPropElement_Model",
                  "m_nElementID": 2,
                  "m_sModelName": "models/single.vmdl"
                }]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(1);
    }

    [Test]
    public async Task SizerDrivenVariableSeedsFromInitialExtentSoFitOnLineActuallyScales()
    {
        // Reproduces the real authoring pattern (e.g. a rope's "height" variable driven entirely
        // by a CreateSizer, never given its own m_DefaultValue): without seeding, "height" reads
        // as its raw declared default (0), the FitOnLine line collapses to zero length, and the
        // model renders unscaled instead of stretched to the sizer's initial 96-unit extent.
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Variables": [{
                "_class": "CSmartPropVariable_Float",
                "m_VariableName": "height",
                "m_DefaultValue": 0.0
              }],
              "m_Children": [{
                "_class": "CSmartPropElement_Group",
                "m_nElementID": 1,
                "m_Modifiers": [{
                  "_class": "CSmartPropOperation_CreateSizer",
                  "m_OutputVariableMaxZ": "height",
                  "m_flInitialMaxZ": 96.0,
                  "m_flInitialMinZ": 0.0
                }],
                "m_Children": [{
                  "_class": "CSmartPropElement_FitOnLine",
                  "m_nElementID": 2,
                  "m_nScaleMode": "SCALE_MAXIMIZE",
                  "m_vEnd": { "m_Components": [0.0, 0.0, { "m_SourceName": "height" }] },
                  "m_Children": [{
                    "_class": "CSmartPropElement_Group",
                    "m_nElementID": 3,
                    "m_SelectionCriteria": [{
                      "_class": "CSmartPropSelectionCriteria_LinearLength",
                      "m_bAllowScale": true,
                      "m_flLength": 60.0,
                      "m_flMinLength": 0.0,
                      "m_flMaxLength": 4096.0
                    }],
                    "m_Children": [{
                      "_class": "CSmartPropElement_Model",
                      "m_nElementID": 4,
                      "m_sModelName": "models/rope_tiling.vmdl",
                      "m_vModelScale": {
                        "m_Components": [1.0, 1.0, { "m_Expression": "LinearScale()" }]
                      }
                    }]
                  }]
                }]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(1);
        // 96-unit sizer extent over a 60-unit authored piece: scale = 96 / 60 = 1.6.
        await Assert.That(result.Models[0].Transform.M33).IsEqualTo(1.6f).Within(0.01f);
    }

    [Test]
    public async Task FitOnLineRepeatsAFixedLengthPieceToCoverTheLine()
    {
        // A piece whose criteria disallows scaling can't be stretched to close the gap — FitOnLine
        // must instead repeat it as many whole times as fit.
        const string json = """
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_FitOnLine",
                "m_nElementID": 1,
                "m_vStart": { "m_Components": [0.0, 0.0, 0.0] },
                "m_vEnd": { "m_Components": [0.0, 0.0, 200.0] },
                "m_Children": [{
                  "_class": "CSmartPropElement_PickOne",
                  "m_nElementID": 2,
                  "m_SelectionCriteria": [{
                    "_class": "CSmartPropSelectionCriteria_LinearLength",
                    "m_bAllowScale": false,
                    "m_flLength": 50.0,
                    "m_flMinLength": 50.0,
                    "m_flMaxLength": 50.0
                  }],
                  "m_Children": [{
                    "_class": "CSmartPropElement_Model",
                    "m_nElementID": 3,
                    "m_sModelName": "models/segment.vmdl"
                  }]
                }]
              }]
            }
            """;

        var result = SmartPropEvaluator.EvaluateJson(json);

        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(4);
        var positions = result.Models.Select(model => model.Transform.M43).OrderBy(z => z).ToArray();
        await Assert.That(positions).IsEquivalentTo(new[] { 0f, 50f, 100f, 150f });
    }

    [Test]
    public async Task ScaleModesProduceDifferentPieceCountsForTheSameLine()
    {
        static string BuildJson(string scaleMode) => $$"""
            {
              "generic_data_type": "CSmartPropRoot",
              "m_Children": [{
                "_class": "CSmartPropElement_FitOnLine",
                "m_nElementID": 1,
                "m_nScaleMode": "{{scaleMode}}",
                "m_vStart": { "m_Components": [0.0, 0.0, 0.0] },
                "m_vEnd": { "m_Components": [0.0, 0.0, 200.0] },
                "m_Children": [{
                  "_class": "CSmartPropElement_Group",
                  "m_nElementID": 2,
                  "m_SelectionCriteria": [{
                    "_class": "CSmartPropSelectionCriteria_LinearLength",
                    "m_bAllowScale": true,
                    "m_flLength": 60.0,
                    "m_flMinLength": 30.0,
                    "m_flMaxLength": 120.0
                  }],
                  "m_Children": [{
                    "_class": "CSmartPropElement_Model",
                    "m_nElementID": 3,
                    "m_sModelName": "models/segment.vmdl",
                    "m_vModelScale": { "m_Components": [1.0, 1.0, { "m_Expression": "LinearScale()" }] }
                  }]
                }]
              }]
            }
            """;

        // A 200-unit line with a 60-unit piece stretchable between 30 and 120 units:
        // SCALE_MAXIMIZE favors the fewest, most-stretched pieces (2 pieces @ 200/120=1.667x each);
        // SCALE_EQUALLY favors the count closest to natural size (200/60=3.33 -> 3 pieces @ 1.11x each).
        var maximize = SmartPropEvaluator.EvaluateJson(BuildJson("SCALE_MAXIMIZE"));
        var equally = SmartPropEvaluator.EvaluateJson(BuildJson("SCALE_EQUALLY"));

        await Assert.That(maximize.Diagnostics).IsEmpty();
        await Assert.That(equally.Diagnostics).IsEmpty();
        await Assert.That(maximize.Models).Count().IsEqualTo(2);
        await Assert.That(equally.Models).Count().IsEqualTo(3);
        await Assert.That(maximize.Models[0].Transform.M33).IsEqualTo(200f / 120f).Within(0.01f);
        await Assert.That(equally.Models[0].Transform.M33).IsEqualTo(200f / 180f).Within(0.01f);
    }
}
