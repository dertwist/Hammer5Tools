namespace Hammer5Tools.Core.Tests;

using Hammer5Tools.Core.Cs2;

public class Cs2ContentPathTests
{
    [Test]
    public async Task ContentFilesResolveTheirOwnAddonAndRejectOutsidePaths()
    {
        var root = Path.Combine(Path.GetTempPath(), "cs2-content-paths");
        await Assert.That(Cs2Paths.GetContentAddonName(root, Path.Combine(root, "content", "csgo_addons", "second", "maps", "nested", "test.vmap"))).IsEqualTo("second");
        await Assert.That(Cs2Paths.GetContentAddonName(root, Path.Combine(root, "content", "csgo_addons_other", "second", "test.vmap"))).IsNull();
        await Assert.That(Cs2Paths.GetContentAddonName(root, Path.Combine(root, "content", "csgo_addons", "second", "..", "..", "test.vmap"))).IsNull();
        await Assert.That(Cs2Paths.GetContentAddonName(root, "test.vmap")).IsNull();
    }
}
