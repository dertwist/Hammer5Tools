namespace Hammer5Tools.IntegrationTests.Addons;

using System.IO;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.IO.Addons;
using Hammer5Tools.Core.IO.Cs2;
using Hammer5Tools.Core.IO.Settings;

public class AddonServiceTests
{
    [Test]
    public async Task AddonDiscoveryAndExclusions()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_AddonServiceTest_" + Guid.NewGuid().ToString("N"));
        var settingsFile = Path.Combine(tempDir, "settings.json");

        try
        {
            var binWin64 = Path.Combine(tempDir, "game", "bin", "win64");
            Directory.CreateDirectory(binWin64);
            await File.WriteAllTextAsync(Path.Combine(binWin64, "cs2.exe"), "mock");

            var contentAddons = Cs2Paths.GetContentAddonsPath(tempDir);
            Directory.CreateDirectory(Path.Combine(contentAddons, "de_dust2_cs2"));
            Directory.CreateDirectory(Path.Combine(contentAddons, "de_nuke_cs2"));
            Directory.CreateDirectory(Path.Combine(contentAddons, "addon_template")); // Should be excluded
            Directory.CreateDirectory(Path.Combine(contentAddons, "workshop_items")); // Should be excluded

            var settingsService = new JsonSettingsService(settingsFile);
            settingsService.Update(s => s.Cs2PathOverride = tempDir);

            var locator = new Cs2Locator(settingsService);
            var service = new AddonService(locator, settingsService);

            var addons = service.Addons;
            await Assert.That(addons).Count().IsEqualTo(2);
            await Assert.That(addons.Select(a => a.Name)).Contains("de_dust2_cs2");
            await Assert.That(addons.Select(a => a.Name)).Contains("de_nuke_cs2");
            await Assert.That(addons.Select(a => a.Name)).DoesNotContain("addon_template");
        }
        finally
        {
            if (Directory.Exists(tempDir))
            {
                Directory.Delete(tempDir, recursive: true);
            }
        }
    }

    [Test]
    public async Task AddonLifecycleCreateAndSwitchAndDelete()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_AddonServiceTest_" + Guid.NewGuid().ToString("N"));
        var settingsFile = Path.Combine(tempDir, "settings.json");

        try
        {
            var binWin64 = Path.Combine(tempDir, "game", "bin", "win64");
            Directory.CreateDirectory(binWin64);
            await File.WriteAllTextAsync(Path.Combine(binWin64, "cs2.exe"), "mock");

            var settingsService = new JsonSettingsService(settingsFile);
            settingsService.Update(s => s.Cs2PathOverride = tempDir);

            var locator = new Cs2Locator(settingsService);
            var service = new AddonService(locator, settingsService);

            var created = service.CreateAddon("surf_test");
            await Assert.That(created).IsNotNull();
            await Assert.That(Directory.Exists(created.ContentPath)).IsTrue();
            await Assert.That(Directory.Exists(Path.Combine(created.ContentPath, "maps"))).IsTrue();
            await Assert.That(Directory.Exists(Path.Combine(created.ContentPath, "materials"))).IsTrue();
            await Assert.That(service.ActiveAddon?.Name).IsEqualTo("surf_test");
            await Assert.That(settingsService.Settings.SelectedAddon).IsEqualTo("surf_test");

            var deleted = service.DeleteAddon("surf_test");
            await Assert.That(deleted).IsTrue();
            await Assert.That(Directory.Exists(created.ContentPath)).IsFalse();
            await Assert.That(service.Addons.Any(a => a.Name == "surf_test")).IsFalse();
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
