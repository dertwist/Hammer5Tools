namespace Hammer5Tools.Core.Tests;

using System.IO.Compression;
using Hammer5Tools.Core.Addons;

public sealed class AddonArchiveTests
{
    [Test]
    public async Task ExportImportPreservesLegacyLayoutAndRefusesOverwrite()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-archive-{Guid.NewGuid():N}");
        try
        {
            var content = Path.Combine(root, "source", "content");
            var game = Path.Combine(root, "source", "game");
            Directory.CreateDirectory(content);
            Directory.CreateDirectory(game);
            File.WriteAllText(Path.Combine(content, "test.vsmart"), "source");
            File.WriteAllText(Path.Combine(game, "test.vsmart_c"), "compiled");
            var archive = Path.Combine(root, "test.zip");
            AddonArchive.Export(new Addon("test", content, game), archive);
            var install = Path.Combine(root, "target");
            await Assert.That(AddonArchive.Import(archive, install)).IsEqualTo("test");
            await Assert.That(File.ReadAllText(Path.Combine(install, "content", "csgo_addons", "test", "test.vsmart"))).IsEqualTo("source");
            await Assert.That(File.ReadAllText(Path.Combine(install, "game", "csgo_addons", "test", "test.vsmart_c"))).IsEqualTo("compiled");
            await Assert.That(() => AddonArchive.Import(archive, install)).Throws<IOException>();
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    [Test]
    public async Task ImportRejectsTraversalBeforeWritingAnyFiles()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-archive-{Guid.NewGuid():N}");
        Directory.CreateDirectory(root);
        try
        {
            var archive = Path.Combine(root, "unsafe.zip");
            using (var zip = ZipFile.Open(archive, ZipArchiveMode.Create))
            {
                zip.CreateEntry("content/csgo_addons/test/../../escape.txt");
            }
            var target = Path.Combine(root, "target");
            await Assert.That(() => AddonArchive.Import(archive, target)).Throws<InvalidDataException>();
            await Assert.That(Directory.Exists(target)).IsFalse();
            await Assert.That(() => AddonArchive.ValidateName("../test")).Throws<ArgumentException>();
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }
}
