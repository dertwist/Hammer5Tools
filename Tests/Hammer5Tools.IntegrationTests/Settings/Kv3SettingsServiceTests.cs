namespace Hammer5Tools.IntegrationTests.Settings;

using System.IO;
using Hammer5Tools.Core.IO.Settings;
using Hammer5Tools.Core.Settings;

public class Kv3SettingsServiceTests
{
    [Test]
    public async Task PersistsAndLoadsAcrossInstancesInKv3()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_Kv3SettingsTest_" + Guid.NewGuid().ToString("N"));
        var settingsFile = Path.Combine(tempDir, "settings.kv3");

        try
        {
            var service1 = new Kv3SettingsService(settingsFile);
            service1.Update(s =>
            {
                s.SelectedAddon = "test_addon";
                s.Cs2PathOverride = @"D:\Steam\steamapps\common\Counter-Strike Global Offensive";
                s.Theme = "Light";
                s.Editor.SoundEventPlayOnClick = false;
                s.Editor.LaunchOptions.Retail = false;
            });

            await Assert.That(File.Exists(settingsFile)).IsTrue();
            var savedContent = await File.ReadAllTextAsync(settingsFile);
            await Assert.That(savedContent).Contains("test_addon");
            await Assert.That(savedContent).Contains("selectedAddon");

            var service2 = new Kv3SettingsService(settingsFile);
            await Assert.That(service2.Settings.SelectedAddon).IsEqualTo("test_addon");
            await Assert.That(service2.Settings.Cs2PathOverride).IsEqualTo(@"D:\Steam\steamapps\common\Counter-Strike Global Offensive");
            await Assert.That(service2.Settings.Theme).IsEqualTo("Light");
            await Assert.That(service2.Settings.Editor.SoundEventPlayOnClick).IsFalse();
            await Assert.That(service2.Settings.Editor.LaunchOptions.Retail).IsFalse();
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
    public async Task MigratesFromLegacyJsonWhenKv3Missing()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_Kv3SettingsTest_" + Guid.NewGuid().ToString("N"));
        var settingsKv3 = Path.Combine(tempDir, "settings.kv3");
        var settingsJson = Path.Combine(tempDir, "settings.json");

        try
        {
            Directory.CreateDirectory(tempDir);
            var jsonContent = """
                {
                    "selectedAddon": "migrated_addon",
                    "theme": "Vintage Steam",
                    "editor": {
                        "soundEventPlayOnClick": false
                    }
                }
                """;
            await File.WriteAllTextAsync(settingsJson, jsonContent);

            var service = new Kv3SettingsService(settingsKv3);
            await Assert.That(service.Settings.SelectedAddon).IsEqualTo("migrated_addon");
            await Assert.That(service.Settings.Theme).IsEqualTo("Vintage Steam");
            await Assert.That(service.Settings.Editor.SoundEventPlayOnClick).IsFalse();
            await Assert.That(File.Exists(settingsKv3)).IsTrue();
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
    public async Task RecoversFromCorruptKv3()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_Kv3SettingsTest_" + Guid.NewGuid().ToString("N"));
        var settingsFile = Path.Combine(tempDir, "settings.kv3");

        try
        {
            Directory.CreateDirectory(tempDir);
            await File.WriteAllTextAsync(settingsFile, "<!-- kv3 --> INVALID KV3 CONTENT {{{");

            var service = new Kv3SettingsService(settingsFile);

            await Assert.That(service.Settings).IsNotNull();
            await Assert.That(service.Settings.Theme).IsEqualTo("Standard");
            await Assert.That(service.Settings.SelectedAddon).IsNull();
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
