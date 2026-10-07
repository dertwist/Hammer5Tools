namespace Hammer5Tools.Core.Tests.LoadingScreens;

using Hammer5Tools.Core.LoadingScreens;
using Microsoft.Extensions.DependencyInjection;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.Formats.Gif;
using SixLabors.ImageSharp.Formats.Webp;
using SixLabors.ImageSharp.PixelFormats;

public sealed class TimelineExportTests
{
    [Test]
    [Arguments("GIF")]
    [Arguments("WEBP")]
    public async Task ExportPreservesFrameOrderTimingLoopingAndReplacesWithBackup(string format)
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-animation-{Guid.NewGuid():N}");
        Directory.CreateDirectory(root);
        try
        {
            using var services = new ServiceCollection().AddLogging().AddHammer5ToolsCore().BuildServiceProvider();
            var exporter = services.GetRequiredService<ILoadingScreenService>();
            var firstPath = Path.Combine(root, "first.png");
            var secondPath = Path.Combine(root, "second.png");
            using (var first = new Image<Rgba32>(32, 24, new Rgba32(255, 0, 0))) await first.SaveAsPngAsync(firstPath);
            using (var second = new Image<Rgba32>(16, 24, new Rgba32(0, 0, 255))) await second.SaveAsPngAsync(secondPath);
            var output = Path.Combine(root, $"camera_timeline.{format.ToLowerInvariant()}");
            await File.WriteAllTextAsync(output, "previous animation");
            var exported = await exporter.ExportTimelineAsync([firstPath, secondPath], root, "camera", format, "High");
            await Assert.That(exported).IsEqualTo(output);
            await Assert.That(await File.ReadAllTextAsync(output + ".bak")).IsEqualTo("previous animation");
            using var animation = await Image.LoadAsync<Rgba32>(output);
            await Assert.That(animation.Width).IsEqualTo(32);
            await Assert.That(animation.Height).IsEqualTo(24);
            await Assert.That(animation.Frames.Count).IsEqualTo(2);
            await Assert.That(animation.Frames[0][16, 12].R > 240).IsTrue();
            await Assert.That(animation.Frames[1][16, 12].B > 240).IsTrue();
            if (format == "GIF")
            {
                await Assert.That(animation.Metadata.GetGifMetadata().RepeatCount).IsEqualTo((ushort)0);
                foreach (var frame in animation.Frames) await Assert.That(frame.Metadata.GetGifMetadata().FrameDelay).IsEqualTo(50);
            }
            else
            {
                await Assert.That(animation.Metadata.GetWebpMetadata().RepeatCount).IsEqualTo((ushort)0);
                foreach (var frame in animation.Frames) await Assert.That(frame.Metadata.GetWebpMetadata().FrameDelay).IsEqualTo(500u);
            }
            var bytes = await File.ReadAllBytesAsync(output);
            using var cancellation = new CancellationTokenSource();
            cancellation.Cancel();
            await Assert.That(async () => await exporter.ExportTimelineAsync([firstPath], root, "camera", format, "Low", cancellation.Token)).Throws<OperationCanceledException>();
            await Assert.That(async () => await exporter.ExportTimelineAsync([firstPath, Path.Combine(root, "missing.png")], root, "camera", format, "Low")).Throws<FileNotFoundException>();
            await Assert.That(await File.ReadAllBytesAsync(output)).IsEquivalentTo(bytes);
            await Assert.That(Directory.GetFiles(root, ".*")).IsEmpty();
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }
}
