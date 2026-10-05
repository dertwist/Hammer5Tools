namespace Hammer5Tools.Core.Tests.DetailProps;

using Hammer5Tools.Core.DetailProps;

public class DetailPropBaselineTests
{
    [Test]
    public async Task EditingDensityPreservesBaselineFieldsAndMetadata()
    {
        var source = DetailPropDocument.DefaultHeader + """

        {
            generic_data_type = "CDetailPropType"
            editor_info = { author = "mapper" }
            grass =
            {
                m_flDensity = 1.234567
                custom_type = 17
                m_Models =
                [
                    {
                        m_ModelName = resource_name:"models/grass.vmdl"
                        m_flRandomScaleMin = 0.812345
                        m_MaterialGroup = "winter"
                        m_vRandomRotationMax = [0.0, 360.0, 0.0]
                        custom_model = "keep me"
                    }
                ]
            }
        }
        """;
        var document = DetailPropDocument.Parse(source);
        await Assert.That(document.Types).Count().IsEqualTo(1);
        document.Types[0].Density = 2.345678f;
        var output = document.Serialize();
        await Assert.That(output).Contains("generic_data_type");
        await Assert.That(output).Contains("mapper");
        await Assert.That(output).Contains("custom_type");
        await Assert.That(output).Contains("custom_model");
        await Assert.That(output).Contains("resource_name:");
        await Assert.That(output).Contains("winter");
        var reparsed = DetailPropDocument.Parse(output);
        await Assert.That(reparsed.Types[0].Density).IsEqualTo(2.345678f);
    }
}
