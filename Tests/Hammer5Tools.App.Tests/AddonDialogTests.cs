namespace Hammer5Tools.App.Tests;

using Avalonia.Controls;
using Avalonia.Headless;
using Avalonia.Interactivity;
using Avalonia.Threading;
using Avalonia.VisualTree;
using Hammer5Tools.App.Features.Preferences;
using Hammer5Tools.App.Services;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.IO.Settings;

[NotInParallel]
public sealed class AddonDialogTests
{
    [Test]
    public async Task CreateDialogOffersBundledPresetsAndValidatesTheName()
    {
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var owner = new Window { Width = 900, Height = 750 };
            owner.Show();
            using var service = new DialogService { OwnerWindow = () => owner };
            try
            {
                var request = service.ConfigureAddonAsync("hammer5tools");
                var dialog = await WaitForDialog(owner);
                var preset = dialog.GetVisualDescendants().OfType<ComboBox>().Single();
                await Assert.That(preset.ItemCount >= 3).IsTrue();
                await Assert.That(preset.SelectedItem).IsEqualTo("hammer5tools");
                var input = dialog.GetVisualDescendants().OfType<TextBox>().Single(control => control.Name == "AddonName");
                var create = dialog.GetVisualDescendants().OfType<Button>().Single(button => Equals(button.Content, "Create"));
                input.Text = "../invalid";
                create.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                await Assert.That(dialog.IsVisible).IsTrue();
                input.Text = "de_test";
                SaveFrame(dialog, "create-addon");
                create.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                var result = await request;
                await Assert.That(result!.Name).IsEqualTo("de_test");
                await Assert.That(result.PresetName).IsEqualTo("hammer5tools");
            }
            finally { foreach (var child in owner.OwnedWindows.ToArray()) child.Close(); owner.Close(); }
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task ExportDialogShowsFilesAndRequiresRefreshAfterFilterChanges()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-export-ui-{Guid.NewGuid():N}");
        var content = Path.Combine(root, "content", "maps");
        Directory.CreateDirectory(content);
        File.WriteAllText(Path.Combine(content, "test.vmap"), "map");
        try
        {
            await TestAppBuilder.Session.Dispatch(async () =>
            {
                var owner = new Window { Width = 900, Height = 750 };
                owner.Show();
                using var service = new DialogService { OwnerWindow = () => owner };
                try
                {
                    var operation = service.ExportAddonAsync(new Addon("test", Path.Combine(root, "content"), Path.Combine(root, "game")));
                    var dialog = await WaitForDialog(owner);
                    for (var i = 0; i < 200 && !dialog.GetVisualDescendants().OfType<CheckBox>().Any(check => check.Content?.ToString()?.Contains("test.vmap", StringComparison.Ordinal) == true); i++) await Task.Delay(10);
                    await Assert.That(dialog.GetVisualDescendants().OfType<CheckBox>().Any(check => check.Content?.ToString()?.Contains("test.vmap", StringComparison.Ordinal) == true)).IsTrue();
                    SaveFrame(dialog, "export-addon");
                    var export = dialog.GetVisualDescendants().OfType<Button>().Single(button => button.Content?.ToString()?.StartsWith("Export", StringComparison.Ordinal) == true);
                    await Assert.That(export.IsEnabled).IsTrue();
                    dialog.GetVisualDescendants().OfType<CheckBox>().First().IsChecked = true;
                    await Assert.That(export.IsEnabled).IsFalse();
                    dialog.Close();
                    await Assert.That(await operation).IsFalse();
                }
                finally { foreach (var child in owner.OwnedWindows.ToArray()) child.Close(); owner.Close(); }
                return true;
            }, CancellationToken.None);
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    private static async Task<Window> WaitForDialog(Window owner)
    {
        for (var i = 0; i < 200; i++)
        {
            if (owner.OwnedWindows.Count > 0) return owner.OwnedWindows[0];
            await Task.Delay(10);
        }
        throw new InvalidOperationException("The addon dialog did not open.");
    }

    [Test]
    public async Task SettingsLaunchOptionsPreviewAndPersistenceMatchTheSelectedSwitches()
    {
        var root = Path.Combine(Path.GetTempPath(), $"h5t-launch-ui-{Guid.NewGuid():N}");
        Directory.CreateDirectory(root);
        try
        {
            await TestAppBuilder.Session.Dispatch(async () =>
            {
                var settings = new JsonSettingsService(Path.Combine(root, "settings.json"));
                settings.Update(value => value.SelectedAddon = "de_example");
                using var service = new DialogService();
                var model = new PreferencesViewModel(settings, service)
                {
                    LaunchOpenMap = true,
                    LaunchSteam = true,
                    LaunchGpuRayTracing = true,
                    LaunchRetail = true,
                    LaunchNcmMode = true,
                    CustomLaunchArgs = "+exec \"custom file.cfg\"",
                };
                var window = new Window { Content = new PreferencesView { DataContext = model }, Width = 830, Height = 700 };
                window.Show();
                try
                {
                    await Assert.That(model.LaunchPreview).Contains("-asset maps/de_example.vmap");
                    await Assert.That(model.LaunchPreview).Contains("-nocustomermachine");
                    await ((CommunityToolkit.Mvvm.Input.IAsyncRelayCommand)model.ApplyCommand).ExecuteAsync(null);
                    await Assert.That(settings.Settings.Editor.LaunchOptions.OpenMap).IsTrue();
                    await Assert.That(settings.Settings.Editor.LaunchOptions.GpuRayTracing).IsTrue();
                    await Assert.That(settings.Settings.Editor.CustomLaunchArgs).IsEqualTo("+exec \"custom file.cfg\"");
                    window.GetVisualDescendants().OfType<ScrollViewer>().First().ScrollToEnd();
                    SaveFrame(window, "launch-settings");
                }
                finally { window.Close(); }
                return true;
            }, CancellationToken.None);
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    private static void SaveFrame(Window window, string name)
    {
        Dispatcher.UIThread.RunJobs();
        window.UpdateLayout();
        var output = Path.Combine(AppContext.BaseDirectory, "snapshots");
        Directory.CreateDirectory(output);
        using var frame = window.CaptureRenderedFrame() ?? throw new InvalidOperationException("No rendered frame.");
        frame.Save(Path.Combine(output, name + ".png"), Avalonia.Media.Imaging.PngBitmapEncoderOptions.Default);
    }
}
