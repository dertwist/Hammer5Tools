using Hammer5Tools.Core.Format.SmartProps;

namespace Hammer5Tools.Core.Tests.SmartProps;

public sealed class SmartPropTraversalTests
{
    private const string NestedPlacements = """
        {
          "generic_data_type": "CSmartPropRoot",
          "m_Children": [{
            "_class": "CSmartPropElement_PlaceMultiple", "m_nElementID": 1, "m_nCount": 2,
            "m_Children": [{
              "_class": "CSmartPropElement_Layout2DGrid", "m_nElementID": 2,
              "m_nCountW": 2, "m_nCountL": 3, "m_flSpacingWidth": 10, "m_flSpacingLength": 20,
              "m_Children": [{
                "_class": "CSmartPropElement_Model", "m_nElementID": 3, "m_sModelName": "model.vmdl",
                "m_Modifiers": [{ "_class": "CSmartPropOperation_CreateLocator", "m_nElementID": 4 }]
              }]
            }]
          }]
        }
        """;

    [Test]
    public async Task ComposesNestedPlacementsAndWidgetsWithoutChangingAuthoredIds()
    {
        var json = SmartPropEvaluator.EvaluateJson(NestedPlacements);
        var text = SmartPropEvaluator.EvaluateText(SmartPropDocumentSerializer.SerializeJson(NestedPlacements));
        await Assert.That(json.Diagnostics).IsEmpty();
        await Assert.That(json.Models).Count().IsEqualTo(12);
        await Assert.That(json.Models.All(model => model.ElementId == 3)).IsTrue();
        var locators = json.Widgets.Where(widget => widget.Type == "locator").ToArray();
        await Assert.That(locators).Count().IsEqualTo(12);
        await Assert.That(locators.All(widget => widget.ElementId == 4)).IsTrue();
        await Assert.That(locators.Select(widget => widget.Transform)).IsEquivalentTo(json.Models.Select(model => model.Transform));
        await Assert.That(text.Models).IsEquivalentTo(json.Models);
        await Assert.That(text.Widgets.Select(widget => widget.Transform)).IsEquivalentTo(json.Widgets.Select(widget => widget.Transform));
    }

    [Test]
    public async Task AppliesLimitDuringNestedExpansion()
    {
        var result = SmartPropEvaluator.EvaluateJson(NestedPlacements, new SmartPropEvaluationOptions(maximumModels: 5));
        await Assert.That(result.Models).Count().IsEqualTo(5);
        await Assert.That(result.Diagnostics.Single().Code).IsEqualTo("smartprop.model_limit_reached");
    }

    [Test]
    public async Task CancellationReturnsNoPartialPlacements()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var result = SmartPropEvaluator.EvaluateJson(NestedPlacements,
            new SmartPropEvaluationOptions(cancellationToken: cancellation.Token));
        await Assert.That(result.Models).IsEmpty();
        await Assert.That(result.Widgets).IsEmpty();
        await Assert.That(result.Diagnostics.Single().Code).IsEqualTo("smartprop.cancelled");
    }

    [Test]
    public async Task SphereFallsBackToMinimumCountWhenMaximumIsZero()
    {
        const string json = """
            { "_class": "CSmartPropElement_PlaceInSphere", "m_nCountMin": 3, "m_nCountMax": 0,
              "m_Children": [{ "_class": "CSmartPropElement_Model", "m_nElementID": 2, "m_sModelName": "model.vmdl" }] }
            """;
        var result = SmartPropEvaluator.EvaluateJson(json);
        await Assert.That(result.Diagnostics).IsEmpty();
        await Assert.That(result.Models).Count().IsEqualTo(3);
    }

    [Test]
    public async Task SphereCountOneStillPlacesWithinTheAuthoredShell()
    {
        const string json = """
            { "_class": "CSmartPropElement_PlaceInSphere", "m_nElementID": 1,
              "m_nCountMin": 1, "m_nCountMax": 1,
              "m_flPositionRadiusInner": 50, "m_flPositionRadiusOuter": 100,
              "m_Children": [{ "_class": "CSmartPropElement_Model", "m_nElementID": 2, "m_sModelName": "model.vmdl" }] }
            """;
        var first = SmartPropEvaluator.EvaluateJson(json);
        var second = SmartPropEvaluator.EvaluateJson(json);
        await Assert.That(first.Diagnostics).IsEmpty();
        await Assert.That(first.Models.Single().Transform.Translation.Length()).IsGreaterThanOrEqualTo(50f);
        await Assert.That(first.Models.Single().Transform.Translation.Length()).IsLessThanOrEqualTo(100f);
        await Assert.That(second.Models).IsEquivalentTo(first.Models);
    }
}
