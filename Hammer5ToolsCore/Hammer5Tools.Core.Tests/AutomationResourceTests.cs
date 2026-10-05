using System.Numerics;
using System.Runtime.InteropServices;
using System.Text.Json;
using Hammer5Tools.Core.Format.Materials;
using Hammer5Tools.Core.Format.Resources;
using SkiaSharp;

namespace Hammer5Tools.Core.Tests;

public sealed class AutomationResourceTests
{
    [Test]
    public async Task BoundsRespectNegativeNonuniformScaleAndPivotTranslation()
    {
        var model = new CompiledModel([0, 0, 0, 10, 20, 30], [], [], [0, 1, 0], Vector3.Zero, new Vector3(10, 20, 30), [], []);
        using var request = JsonDocument.Parse("{\"scale\":[-2,3,4],\"position\":[5,6,7]}");
        var result = ModelInspection.Summarize(model, request.RootElement, "fixture.vmdl_c");
        await Assert.That(result["minimum"]![0]!.GetValue<float>()).IsEqualTo(-15);
        await Assert.That(result["maximum"]![2]!.GetValue<float>()).IsEqualTo(127);
        await Assert.That(result["dimensions"]![1]!.GetValue<float>()).IsEqualTo(60);
        await Assert.That(result["pivot_to_ground_offset"]!.GetValue<float>()).IsEqualTo(-7);
        await Assert.That(result["physics_bounds"] is null).IsTrue();
    }

    [Test]
    public async Task ExplicitPngChannelsRoundTripIncludingAlphaAndConstantInspection()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try
        {
            var source = Path.Combine(root, "source.png");
            using (var bitmap = new SKBitmap(new SKImageInfo(2, 1, SKColorType.Rgba8888, SKAlphaType.Unpremul)))
            {
                Marshal.Copy(new byte[] { 10, 20, 30, 40, 50, 60, 70, 80 }, 0, bitmap.GetPixels(), 8);
                using var data = bitmap.Encode(SKEncodedImageFormat.Png, 100);
                using var file = File.Create(source);
                data.SaveTo(file);
            }
            var output = Path.Combine(root, "packed.png");
            using var pack = JsonDocument.Parse(JsonSerializer.Serialize(new
            {
                path = output,
                channels = new
                {
                    r = new { path = source, channel = "b" },
                    g = 11,
                    b = new { path = source, channel = "r" },
                    a = new { path = source, channel = "a" }
                }
            }));
            var result = TexturePreparation.Execute(pack.RootElement, "pack");
            await Assert.That(result["failed"]!.GetValue<int>()).IsEqualTo(0);
            using var inspect = JsonDocument.Parse(JsonSerializer.Serialize(new { input = output }));
            var channels = TexturePreparation.Execute(inspect.RootElement, "inspect")["channels"]!;
            await Assert.That(channels["g"]!["constant"]!.GetValue<bool>()).IsTrue();
            await Assert.That(channels["r"]!["minimum"]!.GetValue<int>()).IsEqualTo(30);
            await Assert.That(channels["r"]!["maximum"]!.GetValue<int>()).IsEqualTo(70);
            await Assert.That(channels["a"]!["minimum"]!.GetValue<int>()).IsEqualTo(40);
            var split = Path.Combine(root, "alpha.png");
            using var splitRequest = JsonDocument.Parse(JsonSerializer.Serialize(new { input = output, outputs = new[] { new { path = split, channel = "a" } }, dry_run = true }));
            _ = TexturePreparation.Execute(splitRequest.RootElement, "split");
            await Assert.That(File.Exists(split)).IsFalse();
            using var actualSplit = JsonDocument.Parse(JsonSerializer.Serialize(new { input = output, outputs = new[] { new { path = split, channel = "a" } } }));
            _ = TexturePreparation.Execute(actualSplit.RootElement, "split");
            using var splitInspect = JsonDocument.Parse(JsonSerializer.Serialize(new { input = split }));
            var splitChannels = TexturePreparation.Execute(splitInspect.RootElement, "inspect")["channels"]!;
            await Assert.That(splitChannels["r"]!["minimum"]!.GetValue<int>()).IsEqualTo(40);
            await Assert.That(splitChannels["a"]!["minimum"]!.GetValue<int>()).IsEqualTo(255);
        }
        finally { Directory.Delete(root, true); }
    }
}
