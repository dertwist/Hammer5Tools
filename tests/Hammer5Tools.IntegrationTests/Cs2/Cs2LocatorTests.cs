namespace Hammer5Tools.IntegrationTests.Cs2;

using System.IO;
using Hammer5Tools.Core.Settings;
using Hammer5Tools.Infrastructure.Cs2;
using Hammer5Tools.Infrastructure.Settings;

public class Cs2LocatorTests
{
    [Test]
    public async Task SteamVdfParserParsesLibraryFolders()
    {
        var vdf = """
            "libraryfolders"
            {
                "0"
                {
                    "path"    "/home/user/.steam/steam"
                    "label"   ""
                    "apps"
                    {
                        "220"   "12345"
                    }
                }
                "1"
                {
                    "path"    "/mnt/storage/SteamLibrary"
                    "label"   ""
                    "apps"
                    {
                        "730"   "54321"
                    }
                }
            }
            """;

        var libraries = SteamVdfParser.ParseLibraryFolders(vdf);

        await Assert.That(libraries).Count().IsEqualTo(2);
        // CS2 library comes first
        await Assert.That(libraries[0]).Contains("SteamLibrary");
        await Assert.That(libraries[1]).Contains(".steam");
    }

    [Test]
    public async Task SteamVdfParserExtractsInstallDir()
    {
        var acf = """
            "AppState"
            {
                "appid"         "730"
                "Universe"      "1"
                "name"          "Counter-Strike 2"
                "installdir"    "Counter-Strike Global Offensive"
                "StateFlags"    "4"
            }
            """;

        var dir = SteamVdfParser.ParseInstallDir(acf);
        await Assert.That(dir).IsEqualTo("Counter-Strike Global Offensive");
    }

    [Test]
    public async Task SettingsOverrideTakesPrecedence()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_Cs2LocatorTest_" + Guid.NewGuid().ToString("N"));
        var mockCs2 = Path.Combine(tempDir, "CustomCS2");
        var settingsFile = Path.Combine(tempDir, "settings.json");

        try
        {
            var binWin64 = Path.Combine(mockCs2, "game", "bin", "win64");
            Directory.CreateDirectory(binWin64);
            await File.WriteAllTextAsync(Path.Combine(binWin64, "cs2.exe"), "mock");

            var settingsService = new JsonSettingsService(settingsFile);
            settingsService.Update(s => s.Cs2PathOverride = mockCs2);

            var locator = new Cs2Locator(settingsService);

            await Assert.That(locator.ResolvedCs2Path).IsEqualTo(mockCs2);
            await Assert.That(locator.IsValidCs2Path(mockCs2)).IsTrue();
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
