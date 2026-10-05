namespace Hammer5Tools.IntegrationTests.Workshop;

using Hammer5Tools.Core.IO.Cs2;
using Hammer5Tools.Core.IO.Settings;
using Hammer5Tools.Core.IO.Workshop;
using Hammer5Tools.Core.Workshop;
using SteamDatabase.ValvePak;

public class WorkshopPackagingTests
{
    [Test]
    public async Task ChunkedPackagesPreservePayloadsAcrossArchiveBoundaries()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"h5t-chunks-{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        try
        {
            var path = Path.Combine(directory, "sample_dir.vpk");
            using (var writer = new CS2WorkshopManager.ChunkedPackage { WriteChunkSize = 4 })
            {
                writer.AddFile("materials/first.vmat_c", [1, 2, 3]);
                writer.AddFile("materials/second.vmat_c", [4, 5, 6]);
                writer.Write(path);
            }
            using var package = new Package();
            package.Read(path);
            var first = package.FindEntry("materials/first.vmat_c")!;
            var second = package.FindEntry("materials/second.vmat_c")!;
            package.ReadEntry(first, out var firstData, validateCrc: true);
            package.ReadEntry(second, out var secondData, validateCrc: true);
            await Assert.That(firstData.SequenceEqual(new byte[] { 1, 2, 3 })).IsTrue();
            await Assert.That(secondData.SequenceEqual(new byte[] { 4, 5, 6 })).IsTrue();
            await Assert.That(first.ArchiveIndex).IsEqualTo((ushort)0);
            await Assert.That(second.ArchiveIndex).IsEqualTo((ushort)1);
            package.VerifyHashes();
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    [Test]
    public async Task WritesReadableVpkUsingUpstreamPackingRules()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-pack-{Guid.NewGuid():N}");
        try
        {
            var game = Path.Combine(root, "game", "csgo");
            var addon = Path.Combine(root, "game", "csgo_addons", "sample");
            var content = Path.Combine(root, "content", "csgo_addons", "sample");
            Directory.CreateDirectory(game);
            Directory.CreateDirectory(Path.Combine(addon, "materials"));
            Directory.CreateDirectory(Path.Combine(addon, "scripts"));
            Directory.CreateDirectory(content);
            await File.WriteAllTextAsync(Path.Combine(game, "gameinfo.gi"), """
                "GameInfo"
                {
                    "AddonConfig"
                    {
                        "VpkDirectories"
                        {
                            "include" "materials/"
                            "include" "scripts/"
                        }
                    }
                }
                """);
            await File.WriteAllTextAsync(Path.Combine(content, "publish_rules.txt"), "\"publish_rules\" { \"exclude\" \"scripts/\" }");
            await File.WriteAllTextAsync(Path.Combine(addon, "materials", "included.vmat_c"), "compiled material fixture");
            await File.WriteAllTextAsync(Path.Combine(addon, "materials", "blocked.exe"), "blocked");
            await File.WriteAllTextAsync(Path.Combine(addon, "scripts", "excluded.txt"), "excluded");
            var settings = new JsonSettingsService(Path.Combine(root, "settings.json"));
            settings.Update(value => value.Cs2PathOverride = root);
            var service = new WorkshopManagerService(new Cs2Locator(settings));
            var manifest = await service.AnalyzeAddonFilesAsync("sample", excludeUnused: false);
            await Assert.That(manifest).Contains("materials/included.vmat_c");
            await Assert.That(manifest).Count().IsEqualTo(1);
            var output = Path.Combine(root, "packages", "sample_dir.vpk");
            await Assert.That(await service.BuildWorkshopPackageAsync(new WorkshopPackConfig
            {
                AddonName = "sample",
                ExcludeUnusedContent = false,
                OutputVpkPath = output,
            })).IsTrue();
            using var package = new Package();
            package.Read(output);
            await Assert.That(package.Entries!["vmat_c"]).Count().IsEqualTo(1);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    [Test]
    public async Task RejectsWritingPackageIntoTheAddonBeingPacked()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-pack-{Guid.NewGuid():N}");
        try
        {
            Directory.CreateDirectory(Path.Combine(root, "game", "csgo"));
            await File.WriteAllTextAsync(Path.Combine(root, "game", "csgo", "gameinfo.gi"), "\"GameInfo\" {}");
            var addon = Path.Combine(root, "game", "csgo_addons", "sample");
            Directory.CreateDirectory(addon);
            var settings = new JsonSettingsService(Path.Combine(root, "settings.json"));
            settings.Update(value => value.Cs2PathOverride = root);
            var service = new WorkshopManagerService(new Cs2Locator(settings));
            await Assert.That(async () => await service.BuildWorkshopPackageAsync(new WorkshopPackConfig
            {
                AddonName = "sample",
                ExcludeUnusedContent = false,
                OutputVpkPath = Path.Combine(addon, "sample_dir.vpk"),
            })).Throws<ArgumentException>();
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }
}
