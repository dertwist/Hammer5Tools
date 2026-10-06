namespace Hammer5Tools.Core.Tests.Addons;

using System.IO;
using Hammer5Tools.Core.Addons;

public class AddonModelTests
{
    [Test]
    public async Task AddonPropertiesAndMapDetection()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_AddonModelTest_" + Guid.NewGuid().ToString("N"));
        var contentDir = Path.Combine(tempDir, "content", "csgo_addons", "test_addon");
        var gameDir = Path.Combine(tempDir, "game", "csgo_addons", "test_addon");

        try
        {
            Directory.CreateDirectory(Path.Combine(contentDir, "maps"));
            Directory.CreateDirectory(gameDir);

            var addon = new Addon("test_addon", contentDir, gameDir);

            await Assert.That(addon.Name).IsEqualTo("test_addon");
            await Assert.That(addon.HasContent).IsTrue();
            await Assert.That(addon.HasGame).IsTrue();
            await Assert.That(addon.HasMaps).IsFalse();
            await Assert.That(addon.HasPrimaryMap).IsFalse();

            await File.WriteAllTextAsync(Path.Combine(contentDir, "maps", "test_addon.vmap"), "<vmap>");

            await Assert.That(addon.HasMaps).IsTrue();
            await Assert.That(addon.HasPrimaryMap).IsTrue();
        }
        finally
        {
            if (Directory.Exists(tempDir))
            {
                Directory.Delete(tempDir, recursive: true);
            }
        }
    }
}
