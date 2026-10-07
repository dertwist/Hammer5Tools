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
    public async Task RoundTripPreservesQuotedStringsAndNestedValues()
    {
        var source = SoundEventDocument.DefaultHeader + "\n{ sound = { type = \"csgo_mega\" source = resource:\"sounds/a.vsnd\" nested = { value = \"quoted text\" } } }";
        var document = SoundEventDocument.Parse(source);
        var restored = SoundEventDocument.Parse(document.Serialize());
        await Assert.That(restored.Events[0].GetValue("source")).Contains("resource:");
        await Assert.That(restored.Events[0].GetValue("nested")).Contains("quoted text");
        using var stream = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(document.Serialize()));
        ValveKeyValue.KVSerializer.Create(ValveKeyValue.KVSerializationFormat.KeyValues3Text).Deserialize(stream);
    }

    [Test]
    public async Task ParseEmptyOrInvalidStringReturnsEmptyDocument()
    {
        var doc = SoundEventDocument.Parse(string.Empty);
        await Assert.That(doc.Events).IsEmpty();

        var doc2 = SoundEventDocument.Parse("not a kv3");
        await Assert.That(doc2.Events).IsEmpty();
    }
    [Test]
    public async Task InheritedEventsDoNotGainAnExplicitTypeDuringRoundTrip()
    {
        var document = SoundEventDocument.ParseValidated(SoundEventDocument.DefaultHeader + "\n{ event = { base = \"amb.base\" } }");
        await Assert.That(document.Events[0].HasExplicitType).IsFalse();
        await Assert.That(document.Serialize().Contains("type =", StringComparison.Ordinal)).IsFalse();
        document.Events[0].Type = "csgo_mega";
        await Assert.That(document.Events[0].HasExplicitType).IsTrue();
        await Assert.That(document.Serialize()).Contains("type =");
    }

    [Test]
    public async Task StringValuesPreserveApostrophesUnicodeAndEscapes()
    {
        const string value = "Author's café \"quoted\" path\\file";
        var source = SoundEventDocument.DefaultHeader + "\n{ event = { comment = \"Author's café \\\"quoted\\\" path\\\\file\" } }";
        var document = SoundEventDocument.Parse(source);
        var restored = SoundEventDocument.Parse(document.Serialize());
        await Assert.That(document.Events[0].GetValue("comment")).Contains("Author's café");
        using var stream = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(restored.Serialize()));
        var data = ValveKeyValue.KVSerializer.Create(ValveKeyValue.KVSerializationFormat.KeyValues3Text).Deserialize(stream);
        await Assert.That((string)data.Root["event"]["comment"]).IsEqualTo(value);
    }

    [Test]
    public async Task TemplateSaveRetainsStandalonePropertiesAndBackup()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-sound-template-{Guid.NewGuid():N}");
        try
        {
            var service = new Hammer5Tools.Core.IO.SoundEvents.SoundEventService(null!, Microsoft.Extensions.Logging.Abstractions.NullLogger<Hammer5Tools.Core.IO.SoundEvents.SoundEventService>.Instance);
            var sound = new SoundEvent("example");
            sound.SetValue("volume", "1.5");
            sound.SetValue("soundevent_01", "[\"ambient.birds\", \"ambient.wind\"]");
            var path = Path.Combine(root, "test.kv3");
            await service.SaveTemplateAsync(path, sound);
            var first = await File.ReadAllTextAsync(path);
            using var stream = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(first));
            var data = ValveKeyValue.KVSerializer.Create(ValveKeyValue.KVSerializationFormat.KeyValues3Text).Deserialize(stream);
            await Assert.That(data.Root["volume"].ToString()).IsEqualTo("1.5");
            await Assert.That(first.Contains("example", StringComparison.Ordinal)).IsFalse();
            sound.SetValue("volume", "2");
            await service.SaveTemplateAsync(path, sound);
            await Assert.That(await File.ReadAllTextAsync(path + ".bak")).IsEqualTo(first);
        }
        finally
        {
            if (Directory.Exists(root)) Directory.Delete(root, true);
        }
    }

    [Test]
    [Arguments(0, 0.5, 0.75)]
    [Arguments(1, 0.59375, 0.84375)]
    [Arguments(2, 0.4375, 0.675)]
    [Arguments(3, 0.5, 0.75)]
    [Arguments(4, 0.7055484625, 0.9555484625)]
    public async Task SamplingMatchesLegacyTangentModes(int mode, double midpoint, double secondMidpoint)
    {
        SoundCurvePoint[] authored = [new(0, 0, 0.25, 0.5, mode, mode), new(2, 1, 0.75, 0.2, mode, mode), new(4, 0.5, 0.5, -0.25, mode, mode)];
        var prepared = SoundCurve.Prepare(authored);
        await Assert.That(Math.Abs(SoundCurve.Sample(1, prepared) - midpoint) < 0.000001).IsTrue();
        await Assert.That(Math.Abs(SoundCurve.Sample(3, prepared) - secondMidpoint) < 0.000001).IsTrue();
        await Assert.That(SoundCurve.Sample(-1, prepared)).IsEqualTo(0);
        await Assert.That(Math.Abs(SoundCurve.Sample(5, prepared) - 0.5) < 0.000001).IsTrue();
        await Assert.That(authored[0].RightSlope).IsEqualTo(0.5);
    }

}
