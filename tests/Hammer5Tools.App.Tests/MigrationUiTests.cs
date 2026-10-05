namespace Hammer5Tools.App.Tests;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Headless;
using Avalonia.Threading;
using Avalonia.VisualTree;
using Dock.Avalonia.Controls;
using Hammer5Tools.App.Features.DetailProps;
using Hammer5Tools.App.Features.Hotkeys;
using Hammer5Tools.App.Features.LoadingScreens;
using Hammer5Tools.App.Features.Preferences;
using Hammer5Tools.App.Features.Shell;
using Hammer5Tools.App.Features.SoundEvents;
using Hammer5Tools.App.Services;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.Settings;
using Hammer5Tools.Infrastructure;
using Hammer5Tools.Infrastructure.Settings;
using Microsoft.Extensions.DependencyInjection;

[NotInParallel]
public class MigrationUiTests
{
    [Test]
    public async Task BaselineViewsRenderWithDockedPanelsAndBoundPreferences()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            using var shell = fixture.Services.GetRequiredService<ShellViewModel>();
            await shell.Documents.OfType<SoundEventEditorViewModel>().Single().Initialization;
            var views = new (string Name, Control View)[]
            {
                ("shell", new MainWindow { DataContext = shell }),
                ("detailprops", new DetailPropEditorView { DataContext = shell.Documents.OfType<DetailPropEditorViewModel>().Single() }),
                ("hotkeys", new HotkeyEditorView { DataContext = shell.Documents.OfType<HotkeyEditorViewModel>().Single() }),
                ("loading", new LoadingEditorView { DataContext = shell.Documents.OfType<LoadingEditorViewModel>().Single() }),
                ("soundevents", new SoundEventEditorView { DataContext = shell.Documents.OfType<SoundEventEditorViewModel>().Single() }),
                ("radar", new Features.NavMesh.NavMeshRadarView { DataContext = new Features.NavMesh.NavMeshRadarViewModel(fixture.Services.GetRequiredService<IAddonService>(), fixture.Services.GetRequiredService<Core.NavMesh.INavMeshRadarService>()) }),
                ("assettools", new Features.AssetTools.AssetToolsView { DataContext = new Features.AssetTools.AssetToolsViewModel(fixture.Services.GetRequiredService<IAddonService>(), fixture.Services.GetRequiredService<Core.Workshop.IAssetToolsService>()) }),
                ("gitsync", new Features.GitSync.GitSyncView { DataContext = new Features.GitSync.GitSyncViewModel(fixture.Services.GetRequiredService<IAddonService>(), fixture.Services.GetRequiredService<Core.GitSync.IGitSyncService>()) }),
                ("mapbuilder", new Features.MapBuilder.MapBuilderView { DataContext = new Features.MapBuilder.MapBuilderViewModel(fixture.Services.GetRequiredService<IAddonService>(), fixture.Services.GetRequiredService<Core.MapBuilder.IMapBuilderService>()) }),
                ("workshop", new Features.Workshop.WorkshopManagerView { DataContext = new Features.Workshop.WorkshopManagerViewModel(fixture.Services.GetRequiredService<IAddonService>(), fixture.Services.GetRequiredService<Core.Workshop.IWorkshopManagerService>(), fixture.Dialogs) }),
                ("preferences", new PreferencesView { DataContext = new PreferencesViewModel(fixture.Settings, fixture.Dialogs) }),
            };
            var output = Path.Combine(AppContext.BaseDirectory, "UiSnapshots");
            Directory.CreateDirectory(output);
            foreach (var (name, view) in views)
            {
                var window = view as Window ?? new Window { Content = view, Width = 1200, Height = 760 };
                window.Show();
                Dispatcher.UIThread.RunJobs();
                window.UpdateLayout();
                using var bitmap = window.CaptureRenderedFrame();
                await Assert.That(bitmap).IsNotNull();
                bitmap!.Save(Path.Combine(output, $"{name}.png"), Avalonia.Media.Imaging.PngBitmapEncoderOptions.Default);
                if (name is "shell" or "loading" or "soundevents" or "detailprops")
                {
                    var docks = window.GetVisualDescendants().OfType<DockControl>().ToArray();
                    await Assert.That(docks.Length > 0).IsTrue();
                    await Assert.That(docks.All(dock => dock.Layout is not null)).IsTrue();
                }

                if (name == "shell")
                {
                    await Assert.That(window.GetVisualDescendants().OfType<Features.Explorer.AssetExplorerView>().Any()).IsTrue();
                }

                window.Close();
                if (name is "assettools" or "mapbuilder" && view.DataContext is IDisposable disposable)
                {
                    disposable.Dispose();
                }
            }

            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task DockLayoutRoundTripRetainsPanelSizesAndReconnectsContent()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var first = new global::Hammer5Tools.App.Controls.WorkspaceView
            {
                SettingsService = fixture.Settings,
                LayoutKey = "test-workspace",
                CenterContent = new TextBlock { Text = "Editor" },
                LeftContent = new TextBlock { Text = "Explorer" }
            };
            var window = new Window { Content = first, Width = 1000, Height = 700 };
            window.Show();
            Dispatcher.UIThread.RunJobs();
            var dock = first.GetVisualDescendants().OfType<DockControl>().Single();
            var root = (global::Dock.Model.Mvvm.Controls.RootDock)dock.Layout!;
            var main = (global::Dock.Model.Mvvm.Controls.ProportionalDock)root.VisibleDockables![0];
            ((global::Dock.Model.Mvvm.Controls.ToolDock)main.VisibleDockables![0]).Proportion = 0.4;
            ((global::Dock.Model.Mvvm.Controls.DocumentDock)main.VisibleDockables[2]).Proportion = 0.6;
            window.Close();
            await Assert.That(fixture.Settings.Settings.WorkspaceLayouts.ContainsKey("test-workspace")).IsTrue();

            var explorer = new TextBlock { Text = "Restored explorer" };
            var restored = new global::Hammer5Tools.App.Controls.WorkspaceView
            {
                SettingsService = fixture.Settings,
                LayoutKey = "test-workspace",
                CenterContent = new TextBlock { Text = "Restored editor" },
                LeftContent = explorer
            };
            var secondWindow = new Window { Content = restored, Width = 1000, Height = 700 };
            secondWindow.Show();
            Dispatcher.UIThread.RunJobs();
            var restoredDock = restored.GetVisualDescendants().OfType<DockControl>().Single();
            var restoredRoot = (global::Dock.Model.Mvvm.Controls.RootDock)restoredDock.Layout!;
            var restoredMain = (global::Dock.Model.Mvvm.Controls.ProportionalDock)restoredRoot.VisibleDockables![0];
            var left = (global::Dock.Model.Mvvm.Controls.ToolDock)restoredMain.VisibleDockables![0];
            await Assert.That(left.Proportion).IsEqualTo(0.4);
            await Assert.That(left.VisibleDockables![0].Context).IsSameReferenceAs(explorer);
            secondWindow.Close();
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task CancelledCloseAndSwitchRetainDocumentsAndConfirmedSwitchRebuildsThem()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            using var shell = fixture.Services.GetRequiredService<ShellViewModel>();
            var original = shell.Documents.OfType<DetailPropEditorViewModel>().Single();
            original.SelectedType!.Density = 3.456789f;
            await Assert.That(original.IsDirty).IsTrue();
            fixture.Dialogs.CloseResult = false;
            await shell.CloseDocumentAsync(original);
            await Assert.That(shell.Documents.Contains(original)).IsTrue();
            var next = shell.Addons.Single(addon => addon.Name == "second");
            await Assert.That(await shell.SwitchAddonAsync(next)).IsFalse();
            await Assert.That(shell.SelectedAddon!.Name).IsEqualTo("first");
            fixture.Dialogs.CloseResult = true;
            await Assert.That(await shell.SwitchAddonAsync(next)).IsTrue();
            await Assert.That(shell.Documents.Contains(original)).IsFalse();
            await Assert.That(shell.SelectedAddon!.Name).IsEqualTo("second");
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task PropertyEditsUndoAndRedoAndSaveToTheSelectedDocument()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            using var shell = fixture.Services.GetRequiredService<ShellViewModel>();
            var editor = shell.Documents.OfType<DetailPropEditorViewModel>().Single();
            var originalDensity = editor.SelectedType!.Density;
            editor.SelectedType.Density = 7.123456f;
            await Assert.That(editor.IsDirty).IsTrue();
            editor.Undo.Undo();
            await Assert.That(editor.SelectedType!.Density).IsEqualTo(originalDensity);
            await Assert.That(editor.IsDirty).IsFalse();
            editor.Undo.Redo();
            await Assert.That(editor.SelectedType!.Density).IsEqualTo(7.123456f);
            await Assert.That(await editor.SaveAsync()).IsTrue();
            await Assert.That(editor.IsDirty).IsFalse();
            await Assert.That(File.Exists(editor.DocumentPath)).IsTrue();
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task ThemePalettesMatchThePythonBaseline()
    {
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            foreach (var (name, background, input, text, selection) in new[]
            {
                ("Standard", "#2e2e2e", "#363637", "#e5e5e5", "#515965"),
                ("Bright", "#d1d1d1", "#c8c8c9", "#1a1a1a", "#9aa2ae"),
                ("Vintage Steam", "#58624c", "#4b5442", "#e6e8e4", "#66754f")
            })
            {
                Styles.ThemeService.Apply(name);
                foreach (var (token, color) in new[] { ("Background", background), ("SurfaceInput", input), ("Text", text), ("Selection", selection) })
                {
                    var brush = (Avalonia.Media.SolidColorBrush)Application.Current!.Resources[$"H5T{token}Brush"]!;
                    await Assert.That(brush.Color).IsEqualTo(Avalonia.Media.Color.Parse(color));
                }
            }

            Styles.ThemeService.Apply("Standard");
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task PreferencesApplyPersistsPathsThemeAndLaunchSettings()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var preferences = new PreferencesViewModel(fixture.Settings, fixture.Dialogs)
            {
                Theme = "Bright",
                ArchivePath = "/tmp/h5t-archive",
                CustomLaunchArgs = "-console",
                LoadingUseSavedCameras = false
            };
            await ((CommunityToolkit.Mvvm.Input.IAsyncRelayCommand)preferences.ApplyCommand).ExecuteAsync(null);
            await Assert.That(fixture.Settings.Settings.Theme).IsEqualTo("Bright");
            await Assert.That(fixture.Settings.Settings.ArchivePath).IsEqualTo("/tmp/h5t-archive");
            await Assert.That(fixture.Settings.Settings.Editor.CustomLaunchArgs).IsEqualTo("-console");
            await Assert.That(fixture.Settings.Settings.Editor.LoadingUseSavedCameras).IsFalse();
            Styles.ThemeService.Apply("Dark");
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task FailedSaveRetainsDirtyStateAndReportsTheError()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            using var shell = fixture.Services.GetRequiredService<ShellViewModel>();
            var editor = shell.Documents.OfType<DetailPropEditorViewModel>().Single();
            editor.SelectedType!.Density = 7;
            File.WriteAllText(Path.Combine(shell.SelectedAddon!.ContentPath, "scripts"), "blocks the destination directory");
            await Assert.That(await editor.SaveAsync()).IsFalse();
            await Assert.That(editor.IsDirty).IsTrue();
            await Assert.That(fixture.Dialogs.Errors.Count).IsEqualTo(1);
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task InvalidSoundDocumentCannotBeOverwrittenBySaving()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var addon = fixture.Services.GetRequiredService<IAddonService>().ActiveAddon!;
            var path = Path.Combine(addon.ContentPath, "soundevents", "soundevents_addon.vsndevts");
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            await File.WriteAllTextAsync(path, "invalid original source");
            using var shell = fixture.Services.GetRequiredService<ShellViewModel>();
            var editor = shell.Documents.OfType<SoundEventEditorViewModel>().Single();
            await editor.Initialization;
            await Assert.That(await editor.SaveAsync()).IsFalse();
            await Assert.That(await File.ReadAllTextAsync(path)).IsEqualTo("invalid original source");
            await Assert.That(fixture.Dialogs.Errors.Count).IsEqualTo(2);
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task LoadingDescriptionReadsExistingFieldsAndSupportsUndo()
    {
        using var fixture = new Fixture();
        var addon = fixture.Services.GetRequiredService<IAddonService>().ActiveAddon!;
        await File.WriteAllTextAsync(Path.Combine(addon.ContentPath, "addoninfo.txt"),
            "\"AddonInfo\" { \"addonTitle\" \"Original\" \"addonAuthor\" \"Author\" \"addonDescription\" \"Description\" \"custom\" \"keep\" }");
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            using var shell = fixture.Services.GetRequiredService<ShellViewModel>();
            var editor = shell.Documents.OfType<LoadingEditorViewModel>().Single();
            await editor.Initialization;
            await Assert.That(editor.Author).IsEqualTo("Author");
            await Assert.That(editor.Description).IsEqualTo("Description");
            editor.MapTitle = "Changed";
            editor.Undo.Undo();
            await Assert.That(editor.MapTitle).IsEqualTo("Original");
            await Assert.That(editor.IsDirty).IsFalse();
            editor.Undo.Redo();
            await Assert.That(await editor.SaveAsync()).IsTrue();
            await Assert.That(await File.ReadAllTextAsync(Path.Combine(addon.ContentPath, "addoninfo.txt"))).Contains("custom");
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task CancelledPresetSaveRemainsDirty()
    {
        using var fixture = new Fixture();
        using var editor = new HotkeyEditorViewModel(fixture.Services.GetRequiredService<ICs2Locator>(), fixture.Dialogs);
        editor.SelectedBinding = editor.FilteredBindings[0];
        editor.NewKeyInput = "Ctrl+Shift+S";
        editor.ApplyBindingCommand.Execute(null);
        await Assert.That(await editor.SaveAsync()).IsFalse();
        await Assert.That(editor.IsDirty).IsTrue();
    }

    private sealed class Fixture : IDisposable
    {
        private readonly string Root = Path.Combine(Path.GetTempPath(), $"h5t-ui-{Guid.NewGuid():N}");
        public JsonSettingsService Settings { get; }
        public TestDialogs Dialogs { get; } = new();
        public ServiceProvider Services { get; }

        public Fixture()
        {
            Directory.CreateDirectory(Path.Combine(Root, "game", "csgo"));
            File.WriteAllText(Path.Combine(Root, "game", "csgo", "gameinfo.gi"), "\"GameInfo\" {} ");
            Settings = new JsonSettingsService(Path.Combine(Root, "settings.json"));
            Settings.Update(settings => { settings.Cs2PathOverride = Root; settings.SelectedAddon = "first"; });
            foreach (var name in new[] { "first", "second" })
            {
                Directory.CreateDirectory(Path.Combine(Root, "content", "csgo_addons", name));
                Directory.CreateDirectory(Path.Combine(Root, "game", "csgo_addons", name));
            }

            var services = new ServiceCollection();
            services.AddLogging();
            services.AddInfrastructure();
            services.AddSingleton<ISettingsService>(Settings);
            services.AddSingleton<IDialogService>(Dialogs);
            services.AddTransient<ShellViewModel>();
            Services = services.BuildServiceProvider();
        }

        public void Dispose()
        {
            Services.Dispose();
            Directory.Delete(Root, recursive: true);
        }
    }

    private sealed class TestDialogs : IDialogService
    {
        public List<string> Errors { get; } = [];
        public bool CloseResult { get; set; } = true;
        public void ShowUtility(string title, object viewModel, double width = 960, double height = 650) { }
        public Task<bool> ConfirmCloseAsync(IReadOnlyList<DocumentViewModel> documents) { return Task.FromResult(CloseResult); }
        public Task<string?> OpenFileAsync(string title, string pattern) { return Task.FromResult<string?>(null); }
        public Task<string?> SaveFileAsync(string title, string filename) { return Task.FromResult<string?>(null); }
        public Task<string?> PickFolderAsync(string title) { return Task.FromResult<string?>(null); }
        public Task ShowErrorAsync(string message) { Errors.Add(message); return Task.CompletedTask; }
        public void CloseUtilities() { }
    }
}

public static class TestAppBuilder
{
    public static HeadlessUnitTestSession Session { get; } = HeadlessUnitTestSession.StartNew(typeof(TestAppBuilder));

    [After(Assembly)]
    public static async Task StopUiSession()
    {
        await Task.Run(Session.Dispose);
    }

    public static AppBuilder BuildAvaloniaApp()
    {
        return AppBuilder.Configure<App>().UseSkia().UseHeadless(new AvaloniaHeadlessPlatformOptions { UseHeadlessDrawing = false });
    }
}
