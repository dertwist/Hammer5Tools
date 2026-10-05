namespace Hammer5Tools.Core.Tests.Settings;

using System.Text.Json;
using Hammer5Tools.Core.Settings;

public class AppSettingsTests
{
    [Test]
    public async Task DefaultValuesAreSane()
    {
        var settings = new AppSettings();

        await Assert.That(settings.Theme).IsEqualTo("Standard");
        await Assert.That(settings.UpdateChannel).IsEqualTo("stable");
        await Assert.That(settings.SelectedAddon).IsNull();
        await Assert.That(settings.Cs2PathOverride).IsNull();
        await Assert.That(settings.WindowState.X).IsNull();
        await Assert.That(settings.WindowState.Y).IsNull();
        await Assert.That(settings.WindowState.Width).IsEqualTo(1280.0);
        await Assert.That(settings.WindowState.Height).IsEqualTo(800.0);
        await Assert.That(settings.WindowState.IsMaximized).IsFalse();
        await Assert.That(settings.Editor.SoundEventPlayOnClick).IsTrue();
        await Assert.That(settings.Editor.CustomLaunchArgs).IsEqualTo("-tools");
    }

    [Test]
    public async Task JsonRoundTripPreservesAllFields()
    {
        var original = new AppSettings
        {
            SelectedAddon = "de_dust2_cs2",
            Cs2PathOverride = @"C:\Games\Steam\steamapps\common\Counter-Strike Global Offensive",
            Theme = "Light",
            UpdateChannel = "dev",
            WindowState = new WindowStateSettings
            {
                X = 100,
                Y = 200,
                Width = 1920,
                Height = 1080,
                IsMaximized = true,
            },
            Editor = new EditorPreferences
            {
                SoundEventPlayOnClick = false,
                LaunchNcmMode = true,
                MinimizeToTray = true,
                CustomLaunchArgs = "-tools -dev -vconsole",
            },
        };

        var json = JsonSerializer.Serialize(original, SettingsJsonContext.Default.AppSettings);
        var deserialized = JsonSerializer.Deserialize(json, SettingsJsonContext.Default.AppSettings);

        await Assert.That(deserialized).IsNotNull();
        await Assert.That(deserialized!.SelectedAddon).IsEqualTo("de_dust2_cs2");
        await Assert.That(deserialized.Cs2PathOverride).IsEqualTo(@"C:\Games\Steam\steamapps\common\Counter-Strike Global Offensive");
        await Assert.That(deserialized.Theme).IsEqualTo("Light");
        await Assert.That(deserialized.UpdateChannel).IsEqualTo("dev");
        await Assert.That(deserialized.WindowState.X).IsEqualTo(100.0);
        await Assert.That(deserialized.WindowState.Y).IsEqualTo(200.0);
        await Assert.That(deserialized.WindowState.Width).IsEqualTo(1920.0);
        await Assert.That(deserialized.WindowState.Height).IsEqualTo(1080.0);
        await Assert.That(deserialized.WindowState.IsMaximized).IsTrue();
        await Assert.That(deserialized.Editor.SoundEventPlayOnClick).IsFalse();
        await Assert.That(deserialized.Editor.LaunchNcmMode).IsTrue();
        await Assert.That(deserialized.Editor.MinimizeToTray).IsTrue();
        await Assert.That(deserialized.Editor.CustomLaunchArgs).IsEqualTo("-tools -dev -vconsole");
    }
}
