namespace Hammer5Tools.Core.Tests.SoundEvents;

using Hammer5Tools.Core.SoundEvents;

public class SoundEventDocumentTests
{
    [Test]
    public async Task ParseAndSerializeRoundTripPreservesEvents()
    {
        var kv3 = """
            <!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
            {
            	"weapon_ak47.single" =
            	{
            		type = "csgo_mega"
            		volume = 0.95
            		vsnd_files = [ "sounds/weapons/ak47/ak47_shoot.vsnd" ]
            	}
            	"ambient.wind" =
            	{
            		type = "csgo_ambient"
            		volume = 0.5
            	}
            }
            """;

        var doc = SoundEventDocument.Parse(kv3);

        await Assert.That(doc.Events).Count().IsEqualTo(2);
        await Assert.That(doc.Events[0].Name).IsEqualTo("weapon_ak47.single");
        await Assert.That(doc.Events[0].Type).IsEqualTo("csgo_mega");
        await Assert.That(doc.Events[0].GetValue("volume")).IsEqualTo("0.95");
        await Assert.That(doc.Events[1].Name).IsEqualTo("ambient.wind");

        // Add a property and serialize
        doc.Events[0].SetValue("pitch", "1.05");
        var serialized = doc.Serialize();

        await Assert.That(serialized).Contains("weapon_ak47.single");
        await Assert.That(serialized).Contains("pitch = 1.05");
        await Assert.That(serialized).Contains("ambient.wind");
    }

    [Test]
    public async Task ParseEmptyOrInvalidStringReturnsEmptyDocument()
    {
        var doc = SoundEventDocument.Parse(string.Empty);
        await Assert.That(doc.Events).IsEmpty();

        var doc2 = SoundEventDocument.Parse("not a kv3");
        await Assert.That(doc2.Events).IsEmpty();
    }
}
