namespace Hammer5Tools.App.Tests;

using Avalonia.Controls;
using Avalonia.Headless;
using Avalonia.Input;
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
    public async Task SmartPropLauncherReusesAStandaloneDocumentWithoutOpeningTheShell()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var tools = fixture.Services.GetRequiredService<ToolWindowService>();
            var window = (StandaloneToolWindow)tools.Open(StartupTool.SmartProps);
            try
            {
                await Assert.That(window.Document is Features.SmartProps.SmartPropEditorViewModel).IsTrue();
                await Assert.That(ReferenceEquals(window, tools.Open(StartupTool.SmartProps))).IsTrue();
                await Assert.That(tools.GetDocuments().Count).IsEqualTo(1);
            }
            finally
            {
                window.Close();
                Dispatcher.UIThread.RunJobs();
            }

            return true;
        }, CancellationToken.None);
    }

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
                shell.OpenSmartPropEditor();
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
                await Assert.That(await tools.SwitchAddonAsync(second)).IsTrue();
                Dispatcher.UIThread.RunJobs();
                await Assert.That(addons.ActiveAddon!.Name).IsEqualTo("second");
                await Assert.That(ReferenceEquals(sound.Document, document)).IsTrue();
                await Assert.That(document.IsDirty).IsTrue();
                await Assert.That(document.DocumentPath).IsNull();
                await Assert.That(sound.GetVisualDescendants().OfType<ComboBox>().Any(combo => combo.Name == "AddonSelector")).IsFalse();
                var menu = sound.GetVisualDescendants().OfType<Menu>().Single();
                await Assert.That(menu.Items.OfType<MenuItem>().Select(item => item.Header).Contains("_File")).IsTrue();
                var newDocument = sound.OpenDocumentAsync(null);
                ClickDialog("Cancel", sound, map);
                await Assert.That(await newDocument).IsFalse();
                await Assert.That(ReferenceEquals(sound.Document, document)).IsTrue();

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

    [Test]
    public async Task AddonChangesKeepIndependentShellEditorsAndDynamicMenus()
    {
        using var fixture = new Fixture(allowMain: true);
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var tools = fixture.Services.GetRequiredService<ToolWindowService>();
            var main = (MainWindow)tools.Open(StartupTool.Main);
            var shell = (ShellViewModel)main.DataContext!;
            shell.OpenSmartPropEditor();
            shell.OpenSoundEventEditor();
            var smartProp = shell.Documents.OfType<Features.SmartProps.SmartPropEditorViewModel>().Single();
            var sound = shell.Documents.OfType<SoundEventEditorViewModel>().Single();
            try
            {
                await smartProp.InitialLoadTask;
                await sound.Initialization;
                smartProp.IsDirty = true;
                sound.IsDirty = true;
                var map = new Features.MapBuilder.MapBuilderViewModel(null,
                    fixture.Services.GetRequiredService<Core.MapBuilder.IMapBuilderService>(),
                    fixture.Services.GetRequiredService<Core.Settings.ISettingsService>(),
                    fixture.Services.GetRequiredService<IDialogService>(), cs2Locator: fixture.Services.GetRequiredService<Core.Cs2.ICs2Locator>());
                shell.DockTool(map);
                await Assert.That(map is Features.MapBuilder.MapBuilderViewModel).IsTrue();
                await Assert.That(shell.FileMenu.Items.Any(item => item.Header == "Add VMAP...")).IsTrue();
                var second = fixture.Services.GetRequiredService<IAddonService>().Addons.Single(addon => addon.Name == "second");
                await Assert.That(await shell.SwitchAddonAsync(second)).IsTrue();
                await Assert.That(shell.Documents.Contains(smartProp)).IsTrue();
                await Assert.That(shell.Documents.Contains(sound)).IsTrue();
                await Assert.That(shell.Documents.Contains(map!)).IsTrue();
                await Assert.That(smartProp.IsDirty && sound.IsDirty).IsTrue();
                shell.ActiveDocument = smartProp;
                await Assert.That(shell.FileMenu.Items.Any(item => item.Header == "Save as...")).IsTrue();
                await Assert.That(shell.ElementMenu.IsVisible).IsTrue();
            }
            finally
            {
                smartProp.IsDirty = false;
                sound.IsDirty = false;
                main.Close();
                Dispatcher.UIThread.RunJobs();
            }
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task StandaloneMapBuilderUsesEachMapAddonWithoutChangingTheSharedSelection()
    {
        using var fixture = new Fixture();
        var service = new RecordingMapBuildService();
        using var builder = new Features.MapBuilder.MapBuilderViewModel(null, service,
            cs2Locator: fixture.Services.GetRequiredService<Core.Cs2.ICs2Locator>());
        var path = Path.Combine(fixture.Root, "content", "csgo_addons", "second", "maps", "test.vmap");
        builder.Maps.Add(path);
        await builder.StartBuildCommand.ExecuteAsync(null);
        await Assert.That(service.Addon).IsEqualTo("second");
        await Assert.That(service.Map).IsEqualTo(path);
        await Assert.That(fixture.Services.GetRequiredService<IAddonService>().ActiveAddon!.Name).IsEqualTo("first");

        using var outside = new Features.MapBuilder.MapBuilderViewModel(null, service,
            cs2Locator: fixture.Services.GetRequiredService<Core.Cs2.ICs2Locator>());
        outside.Maps.Add(Path.Combine(fixture.Root, "outside.vmap"));
        await outside.StartBuildCommand.ExecuteAsync(null);
        await Assert.That(outside.Status).Contains("content/csgo_addons");
        await Assert.That(service.Map).IsEqualTo(path);
    }

    [Test]
    public async Task SoundFileResourcesComeFromItsOwnFolderInsteadOfTheSelectedAddon()
    {
        using var fixture = new Fixture();
        var content = Path.Combine(fixture.Root, "content", "csgo_addons", "second");
        Directory.CreateDirectory(Path.Combine(content, "sounds"));
        await File.WriteAllTextAsync(Path.Combine(content, "sounds", "second.wav"), "");
        using var editor = new SoundEventEditorViewModel(null, fixture.Services.GetRequiredService<Core.SoundEvents.ISoundEventService>(),
            fixture.Services.GetRequiredService<IDialogService>(), Path.Combine(content, "soundevents", "test.vsndevts"),
            fixture.Services.GetRequiredService<Core.Cs2.ICs2Locator>());
        await editor.Initialization;
        await Assert.That(editor.AddonSounds.Single()).IsEqualTo(Path.Combine("sounds", "second.wav"));
        await Assert.That(fixture.Services.GetRequiredService<IAddonService>().ActiveAddon!.Name).IsEqualTo("first");
    }

    private sealed class RecordingMapBuildService : Core.MapBuilder.IMapBuilderService
    {
        public string? Addon { get; private set; }
        public string? Map { get; private set; }
        public IReadOnlyList<Core.MapBuilder.MapBuildJob> Jobs => [];
        public event EventHandler<Core.MapBuilder.MapBuildJob>? JobUpdated { add { } remove { } }
        public Task<Core.MapBuilder.MapBuildJob> EnqueueBuildAsync(string addonName, string mapName, Core.MapBuilder.MapBuildOptions options)
        {
            Addon = addonName;
            Map = mapName;
            return Task.FromResult(new Core.MapBuilder.MapBuildJob { AddonName = addonName, MapName = mapName });
        }
        public Task<Core.MapBuilder.MapBuildJob> EnqueueBuildAsync(string addonName, string mapName, Core.MapBuilder.MapBuildPreset preset, bool clearVrad = true, bool launchAfter = false) => throw new NotSupportedException();
        public Task RunMapAsync(string addonName, string mapName, bool buildCubemaps = false, CancellationToken ct = default) => Task.CompletedTask;
        public void CancelJob(string jobId) { }
    }

    [Test]
    public async Task StandaloneFileMenuSavesAndCreatesDocumentsThroughKeyboardInput()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var path = Path.Combine(fixture.Root, "standalone.vsndevts");
            await fixture.Services.GetRequiredService<Core.SoundEvents.ISoundEventService>()
                .SaveDocumentAsync(path, new Core.SoundEvents.SoundEventDocument());
            var tools = fixture.Services.GetRequiredService<ToolWindowService>();
            var window = (StandaloneToolWindow)tools.Open(StartupTool.SoundEvents);
            try
            {
                await window.OpenDocumentAsync(path);
                var sound = (SoundEventEditorViewModel)window.Document;
                await sound.Initialization;
                sound.AddEventCommand.Execute(null);
                var file = window.GetVisualDescendants().OfType<Menu>().Single().Items.OfType<MenuItem>().First();
                file.IsSubMenuOpen = true;
                Dispatcher.UIThread.RunJobs();
                var save = file.Items.OfType<MenuItem>().Single(item => Equals(item.Header, "Save"));
                save.Focus();
                window.KeyPress(Key.Enter, RawInputModifiers.None, PhysicalKey.Enter, null);
                if (sound.SaveCommand is CommunityToolkit.Mvvm.Input.IAsyncRelayCommand { ExecutionTask: { } saving }) await saving;
                await Assert.That(sound.IsDirty).IsFalse();
                await Assert.That(await File.ReadAllTextAsync(path)).Contains("sound_event_1");

                file.IsSubMenuOpen = true;
                Dispatcher.UIThread.RunJobs();
                var create = file.Items.OfType<MenuItem>().Single(item => Equals(item.Header, "New"));
                create.Focus();
                window.KeyPress(Key.Enter, RawInputModifiers.None, PhysicalKey.Enter, null);
                if (create.Command is CommunityToolkit.Mvvm.Input.IAsyncRelayCommand { ExecutionTask: { } creating }) await creating;
                await Assert.That(ReferenceEquals(window.Document, sound)).IsFalse();
                await Assert.That(window.Document.DocumentPath).IsNull();
            }
            finally
            {
                window.Document.IsDirty = false;
                window.Close();
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
                var opening = sound.OpenDocumentAsync(path);
                using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5));
                while (!sound.OwnedWindows.Any()) await Task.Delay(10, timeout.Token);
                ClickDialog("Close", sound);
                await opening;
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
