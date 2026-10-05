namespace Hammer5Tools.IntegrationTests.Launcher;

using System.IO;
using Hammer5Tools.Infrastructure.Addons;
using Hammer5Tools.Infrastructure.Cs2;
using Hammer5Tools.Infrastructure.Settings;

public class Cs2LaunchArgumentTests
{
    [Test]
    public async Task BuildLaunchArgumentsContainsAllRequiredFlags()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_LauncherTest_" + Guid.NewGuid().ToString("N"));
        var settingsFile = Path.Combine(tempDir, "settings.json");

        try
        {
            var settingsService = new JsonSettingsService(settingsFile);
            var locator = new Cs2Locator(settingsService);
            var addonService = new AddonService(locator, settingsService);
            var launcher = new Cs2Launcher(locator, addonService, settingsService);

            var args = launcher.BuildLaunchArguments();

            await Assert.That(args).Contains("-tools");
            await Assert.That(args).Contains("-insecure");
            await Assert.That(args).Contains("-concommandpipe");
            await Assert.That(args).Contains("-con_logfile hammer5tools_console.log");
            await Assert.That(args).Contains("-disable_workshop_command_filtering");
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
    public async Task BuildLaunchArgumentsIncludesAddonAndNcmMode()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "H5T_LauncherTest_" + Guid.NewGuid().ToString("N"));
        var settingsFile = Path.Combine(tempDir, "settings.json");

        try
        {
            var settingsService = new JsonSettingsService(settingsFile);
            settingsService.Update(s =>
            {
                s.SelectedAddon = "de_inferno_cs2";
                s.Editor.LaunchNcmMode = true;
                s.Editor.CustomLaunchArgs = "-vconsole";
            });

            var locator = new Cs2Locator(settingsService);
            var addonService = new AddonService(locator, settingsService);
            var launcher = new Cs2Launcher(locator, addonService, settingsService);

            var args = launcher.BuildLaunchArguments(additionalArgs: "-dev");

            await Assert.That(args).Contains("-addon de_inferno_cs2");
            await Assert.That(args).Contains("-noworkshoppreview");
            await Assert.That(args).Contains("-vconsole");
            await Assert.That(args).Contains("-dev");
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
