using Hammer5Tools.Core.IO.Vpk;
using SteamDatabase.ValvePak;

namespace Hammer5Tools.Core.Tests.Resources;

public sealed class VpkIndexTests
{
    [Test]
    public async Task ReadsMountedArchivesAndLooseRoots()
    {
        var root = Path.Combine(Path.GetTempPath(), $"Hammer5Tools.Core.{Guid.NewGuid():N}");
        Directory.CreateDirectory(root);

        try
        {
            var archivePath = Path.Combine(root, "pak01_dir.vpk");
            var looseRoot = Path.Combine(root, "loose");
            var archiveContents = new byte[] { 1, 2, 3 };
            var looseContents = new byte[] { 4, 5, 6 };

            using (var package = new Package())
            {
                package.AddFile("materials/archive.vmat_c", archiveContents);
                package.Write(archivePath);
            }

            var loosePath = Path.Combine(looseRoot, "materials", "loose.vmat_c");
            Directory.CreateDirectory(Path.GetDirectoryName(loosePath)!);
            File.WriteAllBytes(loosePath, looseContents);

            using var index = new VpkIndex();
            index.MountVpk(archivePath);
            index.AddLooseRoot(looseRoot);

            await Assert.That(index.PackageCount).IsEqualTo(1);
            await Assert.That(index.Exists("materials\\archive.vmat_c")).IsTrue();
            await Assert.That(index.TryReadBytes("materials/archive.vmat_c")).IsEquivalentTo(archiveContents);
            await Assert.That(index.TryGetLooseRoot("materials/loose.vmat_c")).IsEqualTo(looseRoot);
            await Assert.That(index.TryReadBytes("materials/loose.vmat_c")).IsEquivalentTo(looseContents);
            var entries = index.EnumerateEntries([".vmat"]);
            await Assert.That(entries).Count().IsEqualTo(1);
            await Assert.That(entries[0].Path).IsEqualTo("materials/archive.vmat");
            await Assert.That(entries[0].Size).IsEqualTo(archiveContents.Length);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }
}
