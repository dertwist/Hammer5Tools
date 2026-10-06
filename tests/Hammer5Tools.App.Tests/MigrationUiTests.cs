namespace Hammer5Tools.App.Tests;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Data;
using Avalonia.Headless;
using Avalonia.Input;
using Avalonia.Threading;
using Avalonia.VisualTree;
using Dock.Avalonia.Controls;
using Hammer5Tools.App.Features.DetailProps;
using Hammer5Tools.App.Features.Hotkeys;
using Hammer5Tools.App.Features.LoadingScreens;
using Hammer5Tools.App.Features.Preferences;
using Hammer5Tools.App.Features.Shell;
using Hammer5Tools.App.Features.SmartProps;
using Hammer5Tools.App.Features.SoundEvents;
using Hammer5Tools.App.Services;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.IO.Settings;
using Hammer5Tools.Core.Settings;
using Microsoft.Extensions.DependencyInjection;

[NotInParallel]
public class MigrationUiTests
{
    [Test]
    public async Task SmartPropFilesOpenInTheShellAndTrackSaveUndoAndUnsavedEdits()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var path = Path.Combine(fixture.Root, "sample.vsmart");
            await File.WriteAllTextAsync(path, Core.CoreApi.SerializeSmartPropDocument(Core.CoreApi.CreateSmartPropDocument()));
            using var shell = fixture.Services.GetRequiredService<ShellViewModel>();
            var defaults = shell.Documents.Count;
            shell.OpenSmartPropEditorCommand.Execute(null);
            shell.OpenSmartPropEditorCommand.Execute(null);
            await Assert.That(shell.Documents.Count).IsEqualTo(defaults);
            await Assert.That(shell.ActiveDocument is SmartPropEditorViewModel).IsTrue();
            await Assert.That(shell.IsAssetExplorerVisible).IsFalse();
            shell.OnOpenFileFromExplorer(path);
            var document = (SmartPropEditorViewModel)shell.ActiveDocument!;
            var view = document.View;
            var window = new Window { Content = view, Width = 1600, Height = 900 };
            window.Show();
            await document.InitialLoadTask;
            Dispatcher.UIThread.RunJobs();
            await Assert.That(document.DocumentPath).IsEqualTo(path);
            await Assert.That(document.IsDirty).IsFalse();
            var version = view.FindControl<NumericUpDown>("ContentVersion")!;
            version.Value = 7;
            await Assert.That(document.IsDirty).IsTrue();
            document.UndoCommand.Execute(null);
            Dispatcher.UIThread.RunJobs();
            await Assert.That(document.IsDirty).IsFalse();
            document.RedoCommand.Execute(null);
            Dispatcher.UIThread.RunJobs();
            await Assert.That(document.IsDirty).IsTrue();
            await Assert.That(await document.SaveAsync()).IsTrue();
            await Assert.That(document.IsDirty).IsFalse();
            await Assert.That(await File.ReadAllTextAsync(path)).Contains("m_nContentVersion = 7");
            view.FindControl<TextBox>("SourceKv3")!.Text += " invalid";
            Dispatcher.UIThread.RunJobs();
            await Assert.That(document.IsDirty).IsTrue();
            await Assert.That(await document.SaveAsync()).IsFalse();
            shell.OnOpenFileFromExplorer(path);
            await Assert.That(shell.ActiveDocument).IsEqualTo(document);
            window.Close();
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task NumberSliderPreservesAuthoredValuesAndForwardsEdits()
    {
        var control = new Hammer5Tools.App.Controls.NumberSlider { Minimum = 0, Maximum = 1, Value = 2.5 };
        await Assert.That(control.Value).IsEqualTo(2.5);
        var grid = (Grid)control.Content!;
        var number = grid.Children.OfType<NumericUpDown>().Single();
        await Assert.That(number.Value).IsEqualTo(2.5m);
        number.Value = 0.75m;
        await Assert.That(control.Value).IsEqualTo(0.75);
        grid.Children.OfType<Slider>().Single().Value = 0.5;
        await Assert.That(control.Value).IsEqualTo(0.5);
    }

    [Test]
    public async Task NumberSliderCommitsOneUndoEntryOnRelease()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            using var shell = fixture.Services.GetRequiredService<ShellViewModel>();
            var editor = shell.Documents.OfType<DetailPropEditorViewModel>().Single();
            var original = editor.SelectedType!.Density;
            var control = new Hammer5Tools.App.Controls.NumberSlider { Minimum = 0, Maximum = 10, Value = original };
            control.Bind(Hammer5Tools.App.Controls.NumberSlider.ValueProperty,
                new Binding("SelectedType.Density") { Source = editor, Mode = BindingMode.TwoWay });
            var window = new Window { Content = control, Width = 400, Height = 100 };
            window.Show();
            Dispatcher.UIThread.RunJobs();
            var grid = (Grid)control.Content!;
            var slider = grid.Children.OfType<Slider>().Single();
            var number = grid.Children.OfType<NumericUpDown>().Single();
            var thumb = slider.GetVisualDescendants().OfType<Avalonia.Controls.Primitives.Thumb>().Single();
            var start = thumb.TranslatePoint(new Point(thumb.Bounds.Width / 2, thumb.Bounds.Height / 2), window)!.Value;
            var end = slider.TranslatePoint(new Point(slider.Bounds.Width * 0.8, slider.Bounds.Height / 2), window)!.Value;
            window.MouseDown(start, MouseButton.Left);
            window.MouseMove(end);
            await Assert.That(control.Value).IsEqualTo((double)original);
            await Assert.That(editor.Undo.CanUndo).IsFalse();
            await Assert.That(number.Value).IsEqualTo((decimal)slider.Value);
            window.MouseUp(end, MouseButton.Left);
            var committed = (float)slider.Value;
            await Assert.That(committed != original).IsTrue();
            await Assert.That(editor.SelectedType!.Density).IsEqualTo(committed);
            editor.Undo.Undo();
            await Assert.That(editor.SelectedType!.Density).IsEqualTo(original);
            await Assert.That(editor.Undo.CanUndo).IsFalse();
            editor.Undo.Redo();
            await Assert.That(editor.SelectedType!.Density).IsEqualTo(committed);
            editor.Undo.Undo();
            Dispatcher.UIThread.RunJobs();
            start = thumb.TranslatePoint(new Point(thumb.Bounds.Width / 2, thumb.Bounds.Height / 2), window)!.Value;
            window.MouseDown(start, MouseButton.Left);
            window.MouseUp(start, MouseButton.Left);
            await Assert.That(editor.Undo.CanUndo).IsFalse();
            slider.Focus();
            window.KeyPress(Key.Right, RawInputModifiers.None, PhysicalKey.ArrowRight, null);
            window.KeyRelease(Key.Right, RawInputModifiers.None, PhysicalKey.ArrowRight, null);
            await Assert.That(editor.Undo.CanUndo).IsTrue();
            editor.Undo.Undo();
            await Assert.That(editor.SelectedType!.Density).IsEqualTo(original);
            window.Close();
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task MainWindowEnforcesMinimumDimensions()
    {
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            var window = new MainWindow();
            await Assert.That(window.MinWidth).IsEqualTo(800.0);
            await Assert.That(window.MinHeight).IsEqualTo(500.0);
            return true;
        }, CancellationToken.None);
    }

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
                ("preferences", new PreferencesView { DataContext = new PreferencesViewModel(fixture.Settings, fixture.Dialogs) }),
            };
            var output = Path.Combine(AppContext.BaseDirectory, "UiSnapshots");
            Directory.CreateDirectory(output);
            foreach (var (name, view) in views)
            {
                var window = view as Window ?? new Window { Content = view, Width = 1200, Height = 760 };
                window.Width = name == "mapbuilder" ? 1282 : 2214;
                window.Height = name == "mapbuilder" ? 901 : 1110;
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
                    var menu = window.FindControl<Menu>("ApplicationMenu")!;
                    var tabs = window.FindControl<TabControl>("EditorTabs")!;
                    await Assert.That(menu.Parent).IsSameReferenceAs(tabs.Parent);
                    await Assert.That(menu.Bounds.Bottom <= tabs.Bounds.Top).IsTrue();
                    await Assert.That(window.Icon).IsNotNull();
                    var mapBuilder = window.FindControl<Button>("MapBuilderButton")!;
                    var gitSync = window.FindControl<Button>("GitSyncButton")!;
                    await Assert.That(mapBuilder.Command).IsSameReferenceAs(shell.OpenMapBuilderCommand);
                    await Assert.That(gitSync.Command).IsSameReferenceAs(shell.OpenGitSyncCommand);
                    await Assert.That(((Image)mapBuilder.Content!).Source).IsNotNull();
                    await Assert.That(window.FindControl<Button>("PreferencesButton")).IsNull();
                    await Assert.That(mapBuilder.Bounds.Width).IsEqualTo(26.0);
                    await Assert.That(mapBuilder.Bounds.Height).IsEqualTo(26.0);
                    await Assert.That(gitSync.Bounds.Height).IsEqualTo(mapBuilder.Bounds.Height);
                    await Assert.That(window.FindControl<ComboBox>("AddonSelector")!.Bounds.Height).IsEqualTo(26.0);
                    await Assert.That(gitSync.Bounds.Right <= mapBuilder.Bounds.Left).IsTrue();
                    var loading = window.GetVisualDescendants().OfType<LoadingEditorView>().Single();
                    await Assert.That(loading.DataContext).IsSameReferenceAs(shell.ActiveDocument);
                    await Assert.That(window.GetVisualDescendants().OfType<Features.Explorer.AssetExplorerView>().Any()).IsFalse();
                    shell.ActiveDocument = shell.Documents.OfType<SoundEventEditorViewModel>().Single();
                    Dispatcher.UIThread.RunJobs();
                    window.UpdateLayout();
                    var sound = window.GetVisualDescendants().OfType<SoundEventEditorView>().Single();
                    await Assert.That(sound.DataContext).IsSameReferenceAs(shell.ActiveDocument);
                    await Assert.That(window.GetVisualDescendants().OfType<Features.Explorer.AssetExplorerView>().Any()).IsTrue();
                    foreach (var document in shell.Documents)
                    {
                        shell.ActiveDocument = document;
                        Dispatcher.UIThread.RunJobs();
                        window.UpdateLayout();
                        using var editorFrame = window.CaptureRenderedFrame();
                        editorFrame!.Save(Path.Combine(output, $"shell-{document.GetType().Name}.png"), Avalonia.Media.Imaging.PngBitmapEncoderOptions.Default);
                    }
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
    public async Task WorkshopCommandOpensTheUpstreamApplication()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            using var shell = fixture.Services.GetRequiredService<ShellViewModel>();
            await ((CommunityToolkit.Mvvm.Input.IAsyncRelayCommand)shell.OpenWorkshopManagerCommand).ExecuteAsync(null);
            await Assert.That(fixture.Dialogs.WorkshopLaunchCount).IsEqualTo(1);
            await Assert.That(fixture.Dialogs.Errors).IsEmpty();
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task WorkshopIsAnAvaloniaWindowInTheHostProcess()
    {
        await Assert.That(typeof(GUI.MainWindow).IsSubclassOf(typeof(Avalonia.Controls.Window))).IsTrue();
    }

    [Test]
    public async Task IntegratedSmartPropRetainsItsScopedPropertyStyles()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            using var shell = fixture.Services.GetRequiredService<ShellViewModel>();
            shell.OpenSmartPropEditor();
            var editor = shell.Documents.OfType<SmartPropEditorViewModel>().Single().View;
            var window = new Hammer5Tools.App.MainWindow(shell);
            window.Show();
            Avalonia.Threading.Dispatcher.UIThread.RunJobs();
            window.UpdateLayout();
            await editor.InitialLoadTask;
            editor.FindControl<StackPanel>("Fields")!.Children.Add(new SmartPropPropertyRow("m_bEnabled", System.Text.Json.Nodes.JsonValue.Create(true), "Bool", [], []));
            Avalonia.Threading.Dispatcher.UIThread.RunJobs();
            window.UpdateLayout();
            var property = editor.GetVisualDescendants().OfType<TextBlock>().First(control => control.Classes.Contains("propertyName") && control.Classes.Contains("Bool"));
            await Assert.That(((Avalonia.Media.ISolidColorBrush)property.Foreground!).Color.ToString()).IsEqualTo("#ffffbdbe");
            var button = editor.FindControl<Button>("HierarchyAdd")!;
            await Assert.That(button.FontSize).IsEqualTo(12);
            await Assert.That(button.MinHeight).IsEqualTo(22);
            window.Close();
            return true;
        }, CancellationToken.None);
    }

    [Test]
    public async Task ApplicationMenusAreSeparateFromAddonActions()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            using var shell = fixture.Services.GetRequiredService<ShellViewModel>();
            var window = new Hammer5Tools.App.MainWindow(shell);
            var menu = window.FindControl<Menu>("ApplicationMenu")!;
            await Assert.That(menu.Items.OfType<MenuItem>().Select(item => item.Header).Contains("_Editors")).IsTrue();
            window.Show();
            Avalonia.Threading.Dispatcher.UIThread.RunJobs();
            window.UpdateLayout();
            var addonButton = window.FindControl<Button>("AddonActionsButton");
            await Assert.That(addonButton).IsNotNull();
            await Assert.That(addonButton!.Flyout).IsNotNull();
            var flyout = (MenuFlyout)addonButton.Flyout!;
            var actions = flyout.Items.OfType<MenuItem>().Select(item => item.Header).ToArray();
            await Assert.That(actions.Contains("Export addon")).IsTrue();
            await Assert.That(actions.Contains("Remove addon")).IsTrue();
            await Assert.That(actions.Contains("_File")).IsFalse();
            window.Close();
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

    [Test]
    public async Task MapBuilderPresetsPersistEditsWithoutChangingOtherPresets()
    {
        using var fixture = new Fixture();
        await TestAppBuilder.Session.Dispatch(async () =>
        {
            using var builder = new Features.MapBuilder.MapBuilderViewModel(
                fixture.Services.GetRequiredService<IAddonService>(),
                fixture.Services.GetRequiredService<Core.MapBuilder.IMapBuilderService>(), fixture.Settings, fixture.Dialogs);
            builder.SelectedConfiguration = builder.Configurations.Single(configuration => configuration.Name == "Full Compile");
            builder.Options.LightmapResolution = 2048;
            builder.Options.SaveMapPath = true;
            builder.SavePresetCommand.Execute(null);
            fixture.Settings.Load();
            using var reopened = new Features.MapBuilder.MapBuilderViewModel(
                fixture.Services.GetRequiredService<IAddonService>(),
                fixture.Services.GetRequiredService<Core.MapBuilder.IMapBuilderService>(), fixture.Settings, fixture.Dialogs);
            reopened.SelectedConfiguration = reopened.Configurations.Single(configuration => configuration.Name == "Full Compile");
            await Assert.That(reopened.Options.LightmapResolution).IsEqualTo(2048);
            await Assert.That(reopened.Maps.Single()).IsEqualTo("first");
            reopened.SelectedConfiguration = reopened.Configurations[0];
            await Assert.That(reopened.Options.BakeLighting).IsFalse();
            await Assert.That(reopened.Options.LightmapResolution).IsEqualTo(512);
            return true;
        }, CancellationToken.None);
    }

    private sealed class Fixture : IDisposable
    {
        public string Root { get; } = Path.Combine(Path.GetTempPath(), $"h5t-ui-{Guid.NewGuid():N}");
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
            services.AddHammer5ToolsCore();
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
        public int WorkshopLaunchCount { get; private set; }
        public void ShowWorkshopManager() { WorkshopLaunchCount++; }
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
