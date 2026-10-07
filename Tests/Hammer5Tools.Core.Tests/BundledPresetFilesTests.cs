namespace Hammer5Tools.Core.Tests;

using Hammer5Tools.Core.IO;

public class BundledPresetFilesTests
{
    [Test]
    public async Task PublishedAndDevelopmentBuildsResolveTheSamePresetCategories()
    {
        var root = Path.Combine(Path.GetTempPath(), "h5t-preset-layout");
        foreach (var category in new[] { "addons", "soundeventeditor", "smartpropeditor", "hotkeys" })
        {
            var expected = Path.Combine(root, "presets", category);
            await Assert.That(BundledPresetFiles.GetDirectory(category, root)).IsEqualTo(expected);
            await Assert.That(BundledPresetFiles.GetDirectory(category, Path.Combine(root, "bin") + Path.DirectorySeparatorChar)).IsEqualTo(expected);
        }
    }
}
