namespace Hammer5Tools.Core.Tests.DetailProps;

using Hammer5Tools.Core.DetailProps;

public class DetailPropDocumentTests
{
    private const string SampleVdata = """
        <!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
        {
        	grass_low =
        	{
        		m_flDensity = 2.500000
        		m_Models =
        		[
        			{
        				m_ModelName = "models/props/foliage/grass_clump_01.vmdl"
        				m_flMinScale = 0.800000
        				m_flMaxScale = 1.200000
        				m_bRandomYaw = true
        				m_bRandomPitch = false
        				m_bRandomRoll = false
        				m_bAlignToSurface = true
        				m_bUpright = false
        				m_flDensity = 1.000000
        			},
        		]
        	}
        }
        """;

    [Test]
    public async Task ParseExtractsTypesAndModelsCorrectly()
    {
        var doc = DetailPropDocument.Parse(SampleVdata);

        await Assert.That(doc.Types).Count().IsEqualTo(1);
        var type = doc.Types[0];
        await Assert.That(type.Name).IsEqualTo("grass_low");
        await Assert.That(type.Density).IsEqualTo(2.5f);

        await Assert.That(type.Models).Count().IsEqualTo(1);
        var model = type.Models[0];
        await Assert.That(model.ModelName).IsEqualTo("models/props/foliage/grass_clump_01.vmdl");
        await Assert.That(model.MinScale).IsEqualTo(0.8f);
        await Assert.That(model.MaxScale).IsEqualTo(1.2f);
        await Assert.That(model.RandomYaw).IsTrue();
        await Assert.That(model.AlignToSurface).IsTrue();
        await Assert.That(model.Upright).IsFalse();
    }

    [Test]
    public async Task RoundTripMaintainsTypeAndModelHierarchy()
    {
        var doc1 = DetailPropDocument.Parse(SampleVdata);
        var serialized = doc1.Serialize();
        var doc2 = DetailPropDocument.Parse(serialized);

        await Assert.That(doc2.Types).Count().IsEqualTo(1);
        await Assert.That(doc2.Types[0].Name).IsEqualTo("grass_low");
        await Assert.That(doc2.Types[0].Models[0].ModelName).IsEqualTo("models/props/foliage/grass_clump_01.vmdl");
    }
}
