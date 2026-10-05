namespace Hammer5Tools.IntegrationTests.Settings;

using System.IO;
using Hammer5Tools.Core.IO.Settings;
using Hammer5Tools.Core.Settings;

public class JsonSettingsServiceTests
{
    [Test]
    public async Task PersistsAndLoadsAcrossInstances()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_SettingsTest_" + Guid.NewGuid().ToString("N"));
        var settingsFile = Path.Combine(tempDir, "settings.json");

        try
        {
            var service1 = new JsonSettingsService(settingsFile);
            service1.Update(s =>
            {
                s.SelectedAddon = "test_addon";
                s.Cs2PathOverride = @"D:\Steam\steamapps\common\Counter-Strike Global Offensive";
                s.Theme = "Light";
            });

            await Assert.That(File.Exists(settingsFile)).IsTrue();

            var service2 = new JsonSettingsService(settingsFile);
            await Assert.That(service2.Settings.SelectedAddon).IsEqualTo("test_addon");
            await Assert.That(service2.Settings.Cs2PathOverride).IsEqualTo(@"D:\Steam\steamapps\common\Counter-Strike Global Offensive");
            await Assert.That(service2.Settings.Theme).IsEqualTo("Light");
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
    public async Task RecoversFromCorruptJson()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_SettingsTest_" + Guid.NewGuid().ToString("N"));
        var settingsFile = Path.Combine(tempDir, "settings.json");

        try
        {
            Directory.CreateDirectory(tempDir);
            await File.WriteAllTextAsync(settingsFile, "{ NOT_VALID_JSON :::: ");

            var service = new JsonSettingsService(settingsFile);

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

    [Test]
    public async Task SettingsChangedEventFiresOnUpdate()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_SettingsTest_" + Guid.NewGuid().ToString("N"));
        var settingsFile = Path.Combine(tempDir, "settings.json");

        try
        {
            var service = new JsonSettingsService(settingsFile);
            AppSettings? captured = null;
            service.SettingsChanged += (_, s) => captured = s;

            service.Update(s => s.SelectedAddon = "event_addon");

            await Assert.That(captured).IsNotNull();
            await Assert.That(captured!.SelectedAddon).IsEqualTo("event_addon");
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
    public async Task LegacyIniMigrationImportsValues()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_SettingsTest_" + Guid.NewGuid().ToString("N"));
        var settingsFile = Path.Combine(tempDir, "settings.json");
        var iniFile = Path.Combine(tempDir, "settings.ini");

        try
        {
            Directory.CreateDirectory(tempDir);
            var iniContent = """
                [PATHS]
                manual_cs2_path=C:\CustomCS2Path
                archive=C:\Archive

                [LAUNCH]
                addon=legacy_addon

                [APP]
                theme_level=1
                minimize_to_tray=true

                [SoundEventEditor]
                play_on_click=false
                """;

            await File.WriteAllTextAsync(iniFile, iniContent);

            var service = new JsonSettingsService(settingsFile);

            await Assert.That(service.Settings.Cs2PathOverride).IsEqualTo(@"C:\CustomCS2Path");
            await Assert.That(service.Settings.SelectedAddon).IsEqualTo("legacy_addon");
            await Assert.That(service.Settings.ArchivePath).IsEqualTo(@"C:\Archive");
            await Assert.That(service.Settings.Theme).IsEqualTo("Light");
            await Assert.That(service.Settings.Editor.MinimizeToTray).IsTrue();
            await Assert.That(service.Settings.Editor.SoundEventPlayOnClick).IsFalse();
            await Assert.That(File.Exists(settingsFile)).IsTrue();
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
