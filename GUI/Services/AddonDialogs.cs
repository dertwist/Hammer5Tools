namespace Hammer5Tools.App.Services;

using System.IO.Compression;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Layout;
using Avalonia.Media.Imaging;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.IO.Addons;

public sealed record AddonCreationRequest(string Name, string? PresetPath, string? PresetName);

public partial class DialogService
{
    public async Task<AddonCreationRequest?> ConfigureAddonAsync(string? selectedPreset)
    {
        var presets = await Task.Run(() => AddonPresetFiles.Discover());
        var window = CreateDialog("Create addon", 520, 440);
        var name = new TextBox { Name = "AddonName", PlaceholderText = "Lowercase letters, numbers and underscores" };
        string[] presetNames = ["Empty addon", .. presets.Select(item => item.Name)];
        var preset = new ComboBox { ItemsSource = presetNames, SelectedIndex = 0, HorizontalAlignment = HorizontalAlignment.Stretch };
        var image = new Image { Height = 180, Stretch = Avalonia.Media.Stretch.Uniform };
        var error = new TextBlock { TextWrapping = Avalonia.Media.TextWrapping.Wrap };
        name.TextChanged += (_, _) => error.Text = string.Empty;
        var create = new Button { Content = "Create", HorizontalAlignment = HorizontalAlignment.Right };
        var cancel = new Button { Content = "Cancel" };
        Bitmap? thumbnail = null;
        var version = 0;
        preset.SelectionChanged += async (_, _) =>
        {
            var current = ++version;
            thumbnail?.Dispose();
            thumbnail = null;
            image.Source = null;
            error.Text = string.Empty;
            if (preset.SelectedIndex <= 0) return;
            var chosen = presets[preset.SelectedIndex - 1];
            try
            {
                var bytes = await Task.Run(() => AddonPresetFiles.ReadThumbnail(chosen));
                if (current != version || bytes is null) return;
                using var stream = new MemoryStream(bytes);
                thumbnail = new Bitmap(stream);
                image.Source = thumbnail;
            }
            catch (Exception)
            {
                if (current == version) error.Text = "Preset preview unavailable. The preset can still be copied.";
            }
        };
        create.Click += (_, _) =>
        {
            var addonName = name.Text?.Trim() ?? string.Empty;
            if (addonName.Length == 0 || addonName.Any(character => !(character is >= 'a' and <= 'z' or >= '0' and <= '9' or '_')))
            {
                error.Text = "Use lowercase letters, numbers and underscores for the addon name.";
                return;
            }
            var selected = preset.SelectedIndex > 0 ? presets[preset.SelectedIndex - 1] : null;
            window.Close(new AddonCreationRequest(addonName, selected?.Path, selected?.Name));
        };
        cancel.Click += (_, _) => window.Close();
        window.Content = new StackPanel
        {
            Margin = new Thickness(12),
            Spacing = 10,
            Children =
        {
            new TextBlock { Text = "Addon name" }, name, image,
            new TextBlock { Text = "Preset" }, preset, error,
            new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Spacing = 8, Children = { cancel, create } },
        }
        };
        var selectedIndex = presets.ToList().FindIndex(item => item.Name == selectedPreset);
        preset.SelectedIndex = selectedIndex >= 0 ? selectedIndex + 1 : presets.Count > 0 ? 1 : 0;
        try
        {
            return await window.ShowDialog<AddonCreationRequest?>(MainWindow);
        }
        finally
        {
            version++;
            image.Source = null;
            thumbnail?.Dispose();
        }
    }

    public async Task<bool> ExportAddonAsync(Addon addon, string? archiveDirectory = null)
    {
        var window = CreateDialog($"Export {addon.Name}", 850, 720);
        window.CanResize = true;
        window.MinWidth = 600;
        window.MinHeight = 500;
        var options = new AddonExportOptions();
        var controls = new StackPanel { Spacing = 6 };
        CheckBox Toggle(string label, bool value, Action<bool> change)
        {
            var check = new CheckBox { Content = label, IsChecked = value };
            check.IsCheckedChanged += (_, _) => change(check.IsChecked == true);
            controls.Children.Add(check);
            return check;
        }
        Toggle("Skip non-default folders in content/", false, value => options.SkipNonDefaultContentFolders = value);
        Toggle("Include compiled maps", true, value => options.IncludeCompiledMaps = value);
        Toggle("Include compiled materials and textures", true, value => options.IncludeCompiledMaterials = value);
        Toggle("Include compiled models", true, value => options.IncludeCompiledModels = value);
        Toggle("Include other compiled folders (sounds, particles, scripts…)", false, value => options.IncludeOtherCompiledFolders = value);
        Toggle("Ignore version-control files", true, value => options.IgnoreVersionControl = value);
        var ignored = new TextBox { Text = options.IgnoredExtensions };
        controls.Children.Add(new TextBlock { Text = "Ignore file extensions (comma separated)" });
        controls.Children.Add(ignored);
        var compression = new ComboBox { ItemsSource = new[] { "Fastest", "Normal", "Ultra (Slow)" }, SelectedIndex = 1 };
        controls.Children.Add(new TextBlock { Text = "Archive compression" });
        controls.Children.Add(compression);
        var refresh = new Button { Content = "Refresh file list" };
        var all = new Button { Content = "Select all" };
        var none = new Button { Content = "Select none" };
        var list = new StackPanel { Spacing = 2 };
        var selection = new Dictionary<string, CheckBox>(StringComparer.OrdinalIgnoreCase);
        IReadOnlyList<AddonExportFile> files = [];
        var status = new TextBlock { TextWrapping = Avalonia.Media.TextWrapping.Wrap };
        var progress = new ProgressBar { Minimum = 0, Maximum = 1 };
        var export = new Button { Content = "Export…" };
        var cancel = new Button { Content = "Cancel" };
        using var cancellation = new CancellationTokenSource();
        var busy = false;
        var selecting = false;
        var closeRequested = false;
        string? scannedFilters = null;
        string FilterKey() => $"{options.SkipNonDefaultContentFolders}/{options.IncludeCompiledMaps}/{options.IncludeCompiledMaterials}/{options.IncludeCompiledModels}/{options.IncludeOtherCompiledFolders}/{options.IgnoreVersionControl}/{ignored.Text}";
        void FiltersChanged()
        {
            if (busy) return;
            export.IsEnabled = scannedFilters == FilterKey();
            if (!export.IsEnabled) status.Text = "Refresh the file list to apply the changed filters.";
        }
        void UpdateSelection()
        {
            if (selecting) return;
            var chosen = files.Where(file => selection.TryGetValue(file.ArchivePath, out var check) && check.IsChecked == true).ToArray();
            status.Text = $"Selected: {chosen.Length} files ({chosen.Sum(file => file.Size) / 1048576d:F2} MB)";
        }
        async Task RefreshAsync()
        {
            if (busy) return;
            busy = true;
            refresh.IsEnabled = export.IsEnabled = false;
            controls.IsEnabled = false;
            try
            {
                options.IgnoredExtensions = ignored.Text ?? string.Empty;
                files = await Task.Run(() => AddonArchive.ListFiles(addon, options));
                scannedFilters = FilterKey();
                list.Children.Clear();
                selection.Clear();
                foreach (var file in files)
                {
                    var check = new CheckBox { Content = $"{file.ArchivePath} ({file.Size / 1024d:F1} KB)", IsChecked = true };
                    check.IsCheckedChanged += (_, _) => UpdateSelection();
                    selection.Add(file.ArchivePath, check);
                    list.Children.Add(check);
                }
                UpdateSelection();
            }
            catch (Exception ex)
            {
                files = [];
                selection.Clear();
                list.Children.Clear();
                status.Text = ex.Message;
            }
            finally
            {
                busy = false;
                refresh.IsEnabled = export.IsEnabled = controls.IsEnabled = true;
                if (closeRequested) window.Close();
            }
        }
        foreach (var check in controls.Children.OfType<CheckBox>())
            check.IsCheckedChanged += (_, _) => FiltersChanged();
        ignored.TextChanged += (_, _) => FiltersChanged();
        refresh.Click += async (_, _) => await RefreshAsync();
        all.Click += (_, _) => { selecting = true; foreach (var check in selection.Values) check.IsChecked = true; selecting = false; UpdateSelection(); };
        none.Click += (_, _) => { selecting = true; foreach (var check in selection.Values) check.IsChecked = false; selecting = false; UpdateSelection(); };
        export.Click += async (_, _) =>
        {
            if (busy) return;
            options.SelectedFiles = selection.Where(pair => pair.Value.IsChecked == true).Select(pair => pair.Key).ToHashSet(StringComparer.OrdinalIgnoreCase);
            if (options.SelectedFiles.Count == 0) { status.Text = "Select at least one file."; return; }
            var filename = !string.IsNullOrWhiteSpace(archiveDirectory) && Directory.Exists(archiveDirectory)
                ? Path.Combine(archiveDirectory, $"{addon.Name}.zip") : $"{addon.Name}.zip";
            string? destination;
            try
            {
                destination = await SaveFileAsync("Export addon", filename);
            }
            catch (Exception ex)
            {
                status.Text = ex.Message;
                return;
            }
            if (destination is null) return;
            busy = true;
            controls.IsEnabled = refresh.IsEnabled = export.IsEnabled = list.IsEnabled = all.IsEnabled = none.IsEnabled = false;
            cancel.Content = "Cancel export";
            progress.Maximum = options.SelectedFiles.Count;
            options.Compression = compression.SelectedIndex switch { 0 => CompressionLevel.Fastest, 2 => CompressionLevel.SmallestSize, _ => CompressionLevel.Optimal };
            try
            {
                var updates = new Progress<int>(completed =>
                {
                    progress.Value = completed;
                    status.Text = $"Exporting {completed}/{options.SelectedFiles.Count} files…";
                });
                await Task.Run(() => AddonArchive.Export(addon, destination, options, updates, cancellation.Token));
                busy = false;
                window.Close(true);
            }
            catch (OperationCanceledException)
            {
                busy = false;
                window.Close(false);
            }
            catch (Exception ex) { status.Text = ex.Message; }
            finally
            {
                busy = false;
                controls.IsEnabled = refresh.IsEnabled = export.IsEnabled = list.IsEnabled = all.IsEnabled = none.IsEnabled = true;
                cancel.Content = "Close";
                if (closeRequested) window.Close();
            }
        };
        cancel.Click += (_, _) => { if (busy) cancellation.Cancel(); else window.Close(); };
        window.Closing += (_, args) =>
        {
            if (!busy) return;
            args.Cancel = true;
            closeRequested = true;
            cancellation.Cancel();
        };
        var panel = new DockPanel { Margin = new Thickness(12), LastChildFill = true };
        DockPanel.SetDock(controls, Dock.Top);
        panel.Children.Add(controls);
        var actions = new StackPanel
        {
            Spacing = 8,
            Children = { status, progress,
            new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8, Children = { refresh, all, none, export, cancel } } }
        };
        DockPanel.SetDock(actions, Dock.Bottom);
        panel.Children.Add(actions);
        panel.Children.Add(new ScrollViewer { Content = list, Margin = new Thickness(0, 10) });
        window.Content = panel;
        window.Opened += async (_, _) => await RefreshAsync();
        return await window.ShowDialog<bool>(MainWindow);
    }
}
