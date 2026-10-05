namespace Hammer5Tools.App.Tests;

using Avalonia.Controls;
using Avalonia.Headless;
using Avalonia.Interactivity;
using Avalonia.Threading;
using Avalonia.VisualTree;
using Hammer5Tools.App.Features.Shell;
using Hammer5Tools.App.Features.SoundEvents;
using Hammer5Tools.App.Services;
using Hammer5Tools.App.Services.Lifecycle;
using Hammer5Tools.Core;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.IO.Settings;
using Hammer5Tools.Core.Settings;
using Microsoft.Extensions.DependencyInjection;

[NotInParallel]
public class StandaloneToolTests
{
    [Test]
    public async Task StandaloneToolsReuseWindowsWithoutCreatingTheFullShell()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var tools = fixture.Services.GetRequiredService<ToolWindowService>();
            var sound = (StandaloneToolWindow)tools.Open(StartupTool.SoundEvents);
            var map = (StandaloneToolWindow)tools.Open(StartupTool.MapBuilder);
            try
            {
                await ((SoundEventEditorViewModel)sound.Document).Initialization;
                Dispatcher.UIThread.RunJobs();
                await Assert.That(ReferenceEquals(tools.Open(StartupTool.SoundEvents), sound)).IsTrue();
                await Assert.That(tools.GetDocuments().Count).IsEqualTo(2);
                await Assert.That(sound.GetVisualDescendants().OfType<Features.SoundEvents.SoundEventEditorView>().Any()).IsTrue();
                await Assert.That(map.GetVisualDescendants().OfType<Features.MapBuilder.MapBuilderView>().Any()).IsTrue();
                await Assert.That(fixture.ShellCreated).IsFalse();
                var output = Path.Combine(AppContext.BaseDirectory, "snapshots");
                Directory.CreateDirectory(output);
                foreach (var window in new[] { sound, map })
                {
                    window.UpdateLayout();
                    using var bitmap = window.CaptureRenderedFrame();
                    await Assert.That(bitmap).IsNotNull();
                    bitmap!.Save(Path.Combine(output, $"standalone-{window.Document.GetType().Name}.png"), Avalonia.Media.Imaging.PngBitmapEncoderOptions.Default);
                }
                sound.Close();
                Dispatcher.UIThread.RunJobs();
                await Assert.That(map.IsVisible).IsTrue();
                var reopened = (StandaloneToolWindow)tools.Open(StartupTool.SoundEvents);
                await Assert.That(ReferenceEquals(reopened, sound)).IsFalse();
                await ((SoundEventEditorViewModel)reopened.Document).Initialization;
                reopened.Close();
            }
            finally
            {
                sound.Close();
                map.Close();
                Dispatcher.UIThread.RunJobs();
            }

            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task MainWindowCanOpenAndCloseWhileAStandaloneToolRemainsOpen()
    {
        using var fixture = new Fixture(allowMain: true);
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var tools = fixture.Services.GetRequiredService<ToolWindowService>();
            var map = tools.Open(StartupTool.MapBuilder);
            var main = (MainWindow)tools.Open(StartupTool.Main);
            try
            {
                var shell = (ShellViewModel)main.DataContext!;
                await shell.Documents.OfType<Features.SmartProps.SmartPropEditorViewModel>().Single().InitialLoadTask;
                await Assert.That(ReferenceEquals(tools.Open(StartupTool.Main), main)).IsTrue();
                main.Close();
                Dispatcher.UIThread.RunJobs();
                await Assert.That(main.IsVisible).IsFalse();
                await Assert.That(map.IsVisible).IsTrue();
                await Assert.That(tools.GetDocuments().Count).IsEqualTo(1);
            }
            finally
            {
                main.Close();
                map.Close();
                Dispatcher.UIThread.RunJobs();
            }

            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task CancelledCloseAndAddonChangesPreserveStandaloneEdits()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var tools = fixture.Services.GetRequiredService<ToolWindowService>();
            var sound = (StandaloneToolWindow)tools.Open(StartupTool.SoundEvents);
            var map = (StandaloneToolWindow)tools.Open(StartupTool.MapBuilder);
            var document = sound.Document;
            try
            {
                await ((SoundEventEditorViewModel)document).Initialization;
                document.IsDirty = true;
                sound.Close();
                ClickDialog("Cancel", sound, map);
                await Task.Yield();
                Dispatcher.UIThread.RunJobs();
                await Assert.That(sound.IsVisible).IsTrue();
                await Assert.That(document.IsDirty).IsTrue();

                var addons = fixture.Services.GetRequiredService<IAddonService>();
                var second = addons.Addons.Single(addon => addon.Name == "second");
                var cancelled = tools.SwitchAddonAsync(second);
                ClickDialog("Cancel", sound, map);
                await Assert.That(await cancelled).IsFalse();
                await Assert.That(addons.ActiveAddon!.Name).IsEqualTo("first");
                await Assert.That(ReferenceEquals(sound.Document, document)).IsTrue();

                var changed = tools.SwitchAddonAsync(second);
                ClickDialog("Discard", sound, map);
                await Assert.That(await changed).IsTrue();
                Dispatcher.UIThread.RunJobs();
                await ((SoundEventEditorViewModel)sound.Document).Initialization;
                await Assert.That(addons.ActiveAddon!.Name).IsEqualTo("second");
                await Assert.That(ReferenceEquals(sound.Document, document)).IsFalse();
                await Assert.That(sound.Document.DocumentPath!).Contains(Path.Combine("second", "soundevents"));
            }
            finally
            {
                sound.Document.IsDirty = false;
                sound.Close();
                map.Close();
                Dispatcher.UIThread.RunJobs();
            }

            return true;
        }, CancellationToken.None);
    }

    private static void ClickDialog(string text, params Window[] owners)
    {
        Dispatcher.UIThread.RunJobs();
        var dialog = owners.SelectMany(owner => owner.OwnedWindows).Single();
        dialog.GetVisualDescendants().OfType<Button>().Single(button => Equals(button.Content, text))
            .RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    }

    [Test]
    public async Task FailedStandaloneLoadShowsAnOwnedErrorAndCannotOverwriteTheSource()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var path = Path.Combine(fixture.Root, "content", "csgo_addons", "first", "soundevents", "soundevents_addon.vsndevts");
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            await File.WriteAllTextAsync(path, "invalid soundevents");
            var tools = fixture.Services.GetRequiredService<ToolWindowService>();
            var sound = (StandaloneToolWindow)tools.Open(StartupTool.SoundEvents);
            try
            {
                using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5));
                while (!sound.OwnedWindows.Any()) await Task.Delay(10, timeout.Token);
                ClickDialog("Close", sound);
                await ((SoundEventEditorViewModel)sound.Document).Initialization;
                sound.Document.IsDirty = true;
                var save = sound.Document.SaveAsync();
                ClickDialog("Close", sound);
                await Assert.That(await save).IsFalse();
                await Assert.That(sound.Document.IsDirty).IsTrue();
                await Assert.That(await File.ReadAllTextAsync(path)).IsEqualTo("invalid soundevents");
            }
            finally
            {
                sound.Document.IsDirty = false;
                sound.Close();
                Dispatcher.UIThread.RunJobs();
            }

            return true;
        }, CancellationToken.None);
    }

    private sealed class Fixture : IDisposable
    {
        public string Root { get; } = Path.Combine(Path.GetTempPath(), $"h5t-standalone-{Guid.NewGuid():N}");
        public ServiceProvider Services { get; }
        public bool ShellCreated { get; private set; }

        public Fixture(bool allowMain = false)
        {
            Directory.CreateDirectory(Path.Combine(Root, "game", "csgo"));
            File.WriteAllText(Path.Combine(Root, "game", "csgo", "gameinfo.gi"), "\"GameInfo\" {} ");
            foreach (var name in new[] { "first", "second" })
            {
                Directory.CreateDirectory(Path.Combine(Root, "content", "csgo_addons", name));
                Directory.CreateDirectory(Path.Combine(Root, "game", "csgo_addons", name));
            }

            var settings = new JsonSettingsService(Path.Combine(Root, "settings.json"));
            settings.Update(value => { value.Cs2PathOverride = Root; value.SelectedAddon = "first"; });
            var services = new ServiceCollection();
            services.AddLogging();
            services.AddHammer5ToolsCore();
            services.AddSingleton<ISettingsService>(settings);
            services.AddSingleton<DialogService>();
            services.AddSingleton<IDialogService>(provider => provider.GetRequiredService<DialogService>());
            services.AddSingleton<ToolWindowService>();
            services.AddTransient<ShellViewModel>();
            services.AddTransient<MainWindow>(provider =>
            {
                ShellCreated = true;
                return allowMain ? ActivatorUtilities.CreateInstance<MainWindow>(provider)
                    : throw new InvalidOperationException("Standalone tools must not construct the full shell.");
            });
            Services = services.BuildServiceProvider();
        }

        public void Dispose()
        {
            Services.Dispose();
            Directory.Delete(Root, recursive: true);
        }
    }
}
