using Hammer5Tools.Core.Format.SmartProps;

namespace Hammer5Tools.Core.Tests.SmartProps;

public sealed class SmartPropMaterialEvaluatorTests
{
    /// <summary>
    /// A model under a Group whose modifiers carry the material operations. The tint operations
    /// are stacked so mode handling is actually exercised: the outer REPLACE sets a half-red
    /// base, the inner MULTIPLY_CURRENT halves its green.
    /// </summary>
    private const string Document = """
        <!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
        {
            generic_data_type = "CSmartPropRoot"
            m_Children =
            [
                {
                    _class = "CSmartPropElement_Group"
                    m_nElementID = 1
                    m_Modifiers =
                    [
                        {
                            _class = "CSmartPropOperation_SetTintColor"
                            m_nElementID = 2
                            m_SelectionMode = "SPECIFIC"
                            m_ColorSelection = 1
                            m_Mode = "REPLACE"
                            m_ColorChoices = [{ m_Color = [255, 255, 255] }, { m_Color = [128, 255, 255] }]
                        },
                    ]
                    m_Children =
                    [
                        {
                            _class = "CSmartPropElement_Group"
                            m_nElementID = 3
                            m_Modifiers =
                            [
                                {
                                    _class = "CSmartPropOperation_SetTintColor"
                                    m_nElementID = 4
                                    m_SelectionMode = "SPECIFIC"
                                    m_ColorSelection = 0
                                    m_Mode = "MULTIPLY_CURRENT"
                                    m_ColorChoices = [{ m_Color = [255, 128, 255] }]
                                },
                                {
                                    _class = "CSmartPropOperation_MaterialTint"
                                    m_nElementID = 5
                                    m_Material = "Materials\\Models\\Crate.vmat"
                                    m_SelectionMode = "SPECIFIC_COLOR"
                                    m_Color = [0, 255, 0]
                                },
                                {
                                    _class = "CSmartPropOperation_MaterialOverride"
                                    m_nElementID = 6
                                    m_bClearCurrentOverrides = false
                                    m_MaterialReplacements =
                                    [
                                        {
                                            m_OriginalMaterial = "materials/models/crate.vmat"
                                            m_ReplacementMaterial = "materials/models/crate_snow.vmat"
                                        },
                                    ]
                                },
                            ]
                            m_Children =
                            [
                                {
                                    _class = "CSmartPropElement_Model"
                                    m_nElementID = 7
                                    m_sModelName = "models/crate.vmdl"
                                },
                            ]
                        },
                    ]
                },
            ]
        }
        """;

    [Test]
    public async Task MaterialOperationsInheritDownTheElementTree()
    {
        var result = SmartPropEvaluator.EvaluateJson(SmartPropDocumentSerializer.DeserializeText(Document));

        var model = result.Models.Single(model => model.ElementId == 7);

        // REPLACE picked choice 1 = (0.5, 1, 1); MULTIPLY_CURRENT then folded (1, 0.5, 1) in.
        var tint = model.TintColor!.Value;
        await Assert.That(tint.X).IsEqualTo(128f / 255f).Within(0.001f);
        await Assert.That(tint.Y).IsEqualTo(128f / 255f).Within(0.001f);
        await Assert.That(tint.Z).IsEqualTo(1f).Within(0.001f);

        // The authored name is Windows-cased with backslashes; it has to come back in the same
        // normalized form a compiled model's own material path reduces to, or nothing matches.
        var materialTint = model.MaterialTints!.Single();
        await Assert.That(materialTint.Material).IsEqualTo("materials/models/crate.vmat");
        await Assert.That(materialTint.Color.Y).IsEqualTo(1f).Within(0.001f);
        await Assert.That(materialTint.Color.X).IsEqualTo(0f).Within(0.001f);

        var replacement = model.MaterialOverrides!.Single();
        await Assert.That(replacement.OriginalMaterial).IsEqualTo("materials/models/crate.vmat");
        await Assert.That(replacement.ReplacementMaterial).IsEqualTo("materials/models/crate_snow.vmat");
    }

    [Test]
    public async Task DisabledOperationsAreIgnored()
    {
        var disabled = Document.Replace(
            "_class = \"CSmartPropOperation_MaterialTint\"",
            "_class = \"CSmartPropOperation_MaterialTint\"\n                                    m_bEnabled = false",
            StringComparison.Ordinal);

        var result = SmartPropEvaluator.EvaluateJson(SmartPropDocumentSerializer.DeserializeText(disabled));

        var model = result.Models.Single(model => model.ElementId == 7);
        await Assert.That(model.MaterialTints ?? []).IsEmpty();
        // The sibling operations on the same element still applied.
        await Assert.That(model.MaterialOverrides!.Count).IsEqualTo(1);
    }
}
