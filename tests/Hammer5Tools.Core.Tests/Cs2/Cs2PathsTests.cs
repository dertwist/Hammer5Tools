namespace Hammer5Tools.Core.Tests.Cs2;

using System.IO;
using Hammer5Tools.Core.Cs2;

public class Cs2PathsTests
{
    [Test]
    public async Task PathResolutionsMatchExpectedStructure()
    {
        var root = Path.Combine(Path.GetTempPath(), "FakeCS2");

        await Assert.That(Cs2Paths.GetCs2ExePath(root)).IsEqualTo(Path.Combine(root, "game", "bin", "win64", "cs2.exe"));
        await Assert.That(Cs2Paths.GetResourceCompilerPath(root)).IsEqualTo(Path.Combine(root, "game", "bin", "win64", "resourcecompiler.exe"));
        await Assert.That(Cs2Paths.GetContentAddonsPath(root)).IsEqualTo(Path.Combine(root, "content", "csgo_addons"));
        await Assert.That(Cs2Paths.GetGameAddonsPath(root)).IsEqualTo(Path.Combine(root, "game", "csgo_addons"));
        await Assert.That(Cs2Paths.GetAddonContentPath(root, "my_map")).IsEqualTo(Path.Combine(root, "content", "csgo_addons", "my_map"));
        await Assert.That(Cs2Paths.GetAddonGamePath(root, "my_map")).IsEqualTo(Path.Combine(root, "game", "csgo_addons", "my_map"));
    }

    [Test]
    public async Task IsValidCs2PathRequiresValidMarkers()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_Cs2PathTest_" + Guid.NewGuid().ToString("N"));

        try
        {
            Directory.CreateDirectory(tempDir);
            await Assert.That(Cs2Paths.IsValidCs2Path(tempDir)).IsFalse();

            var gameBin = Path.Combine(tempDir, "game", "bin", "win64");
            Directory.CreateDirectory(gameBin);
            var exeFile = Path.Combine(gameBin, "cs2.exe");
            await File.WriteAllTextAsync(exeFile, "mock exe");

            await Assert.That(Cs2Paths.IsValidCs2Path(tempDir)).IsTrue();
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
