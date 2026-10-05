using System.Text.Json.Nodes;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Input.Platform;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;
using Avalonia.Threading;
using Hammer5Tools.Core;

namespace Hammer5Tools.App.Features.SmartProps;

public sealed partial class SmartPropEditorView
{
    private HashSet<string>? hierarchySelectionOverride;
    private readonly Dictionary<string, bool> hierarchyExpansion = [];
    private readonly Dictionary<string, string[]> hierarchySelectionSnapshots = [];
    private string previousHierarchyFilter = "";
    private readonly HashSet<string> favoriteElementClasses = [];
    private static readonly string FavoriteElementsPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Hammer5ToolsAvalonia", "hierarchy-favorites.json");
    private IReadOnlyList<ViewportInstance> hierarchyScene = [];
    private string? isolatedHierarchyKey;

    private void SetupHierarchy()
    {
        try
        {
            if (File.Exists(FavoriteElementsPath))
            {
                favoriteElementClasses.UnionWith(System.Text.Json.JsonSerializer.Deserialize<string[]>(File.ReadAllText(FavoriteElementsPath)) ?? []);
            }
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException or System.Text.Json.JsonException)
        {
            Report(exception);
        }
        HierarchyAdd.Flyout = ElementPicker(false);
        HierarchyFavorites.Flyout = ElementPicker(true);
        var menu = new ContextMenu();
        foreach (var (header, action) in new[]
        {
            ("New element", "add"), ("New from preset…", "preset"), ("Rename", "rename"),
            ("Delete", "remove"), ("Duplicate", "duplicate"), ("Group selected", "group"),
            ("Copy", "copy"), ("Cut", "cut"), ("Paste", "paste"), ("Paste with replacement…", "paste-replace"),
            ("Move up", "up"), ("Move down", "down"), ("Bulk model import…", "import"),
            ("Isolate in 3D viewport", "isolate"), ("Expand all", "expand"), ("Collapse all", "collapse")
        })
        {
            var item = new MenuItem { Header = header };
            item.Click += async (_, _) => await HierarchyAction(action);
            menu.Items.Add(item);
        }
        Hierarchy.ContextMenu = menu;
        Hierarchy.ActionRequested += async action => await HierarchyAction(action);
        Hierarchy.RenameRequested += async (row, label) => await ApplyHierarchy(new JsonObject
        {
            ["action"] = "rename",
            ["target"] = Segments(row.Path),
            ["label"] = label
        });
        Hierarchy.MoveRequested += async (paths, target, position, copy) =>
        {
            if (target is not null && position == "inside")
            {
                hierarchyExpansion[RowKey(target)] = true;
                target.Expanded = true;
            }
            await ApplyHierarchy(new JsonObject
            {
                ["action"] = "move",
                ["paths"] = Paths(paths),
                ["target"] = Segments(target?.Path ?? []),
                ["position"] = position,
                ["copy"] = copy
            });
        };
        Hierarchy.FilesDropped += async (paths, target) => await ImportHierarchyFiles(paths, target?.Path ?? []);
    }

    private Flyout ElementPicker(bool favoritesOnly)
    {
        var search = new TextBox { PlaceholderText = "Find element…" };
        var items = new StackPanel();
        var flyout = new Flyout
        {
            Content = new StackPanel
            {
                Width = 290,
                Spacing = 4,
                Children = { search, new ScrollViewer { MaxHeight = 420, Content = items } }
            }
        };
        void Populate()
        {
            items.Children.Clear();
            foreach (var className in Presentation["componentClasses"]!.AsArray().Select(item => item!.ToString()).Where(name => name.StartsWith("CSmartPropElement_", StringComparison.Ordinal)))
            {
                var name = FriendlyName(className);
                if (!name.Contains(search.Text ?? "", StringComparison.OrdinalIgnoreCase) || favoritesOnly && favoriteElementClasses.Count > 0 && !favoriteElementClasses.Contains(className))
                {
                    continue;
                }
                var row = new Grid { ColumnDefinitions = new ColumnDefinitions("*,24") };
                var add = new Button { Content = name, HorizontalAlignment = global::Avalonia.Layout.HorizontalAlignment.Stretch };
                add.Click += async (_, _) =>
                {
                    flyout.Hide();
                    await HierarchyAction("add", className);
                };
                var favorite = new Button { Content = favoriteElementClasses.Contains(className) ? "★" : "☆", Classes = { "icon" } };
                favorite.Click += (_, _) =>
                {
                    if (!favoriteElementClasses.Add(className))
                    {
                        favoriteElementClasses.Remove(className);
                    }
                    try
                    {
                        Directory.CreateDirectory(Path.GetDirectoryName(FavoriteElementsPath)!);
                        File.WriteAllText(FavoriteElementsPath, System.Text.Json.JsonSerializer.Serialize(favoriteElementClasses.Order()));
                    }
                    catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
                    {
                        Report(exception);
                    }
                    Populate();
                };
                row.Children.Add(add);
                Grid.SetColumn(favorite, 1);
                row.Children.Add(favorite);
                items.Children.Add(row);
            }
        }
        search.TextChanged += (_, _) => Populate();
        flyout.Opened += (_, _) => { Populate(); search.Focus(); };
        Populate();
        return flyout;
    }

    private static JsonArray Segments(string[] path) => new(path.Select(segment => (JsonNode?)JsonValue.Create(segment)).ToArray());
    private async void HierarchyCommandClicked(object? sender, RoutedEventArgs args)
    {
        if (sender is MenuItem { Tag: string action })
        {
            await HierarchyAction(action);
        }
    }
    private static JsonArray Paths(string[][] paths) => new(paths.Select(path => (JsonNode?)Segments(path)).ToArray());
    private static string RowKey(HierarchyRow row) => row.ElementId.Length > 0 ? "id:" + row.ElementId : "path:" + string.Join('/', row.Path);

    private void RebuildHierarchy(JsonObject root)
    {
        var selected = hierarchySelectionOverride ?? Hierarchy.SelectedItems?.OfType<HierarchyRow>().Select(RowKey).ToHashSet() ?? [];
        hierarchySelectionOverride = null;
        if (previousHierarchyFilter.Length == 0 && Hierarchy.ItemsSource is IEnumerable<HierarchyRow> previous)
        {
            foreach (var row in Flatten(previous))
            {
                hierarchyExpansion[RowKey(row)] = row.Expanded;
            }
        }
        var rows = BuildRow(root, []).Children;
        foreach (var row in Flatten(rows))
        {
            row.Expanded = hierarchyExpansion.GetValueOrDefault(RowKey(row), true);
        }
        rows = FilterRows(rows, HierarchyFilter.Text ?? "");
        previousHierarchyFilter = HierarchyFilter.Text ?? "";
        if (!string.IsNullOrWhiteSpace(HierarchyFilter.Text))
        {
            foreach (var row in Flatten(rows))
            {
                row.Expanded = true;
            }
        }
        Hierarchy.ItemsSource = rows;
        Hierarchy.SelectedItems?.Clear();
        foreach (var row in Flatten(rows).Where(row => selected.Contains(RowKey(row))))
        {
            Hierarchy.SelectedItems!.Add(row);
        }
        if (Hierarchy.SelectedItems?.Count == 0 && selectedPath.Length > 0)
        {
            Hierarchy.SelectedItem = Flatten(rows).FirstOrDefault(row => row.Path.SequenceEqual(selectedPath));
        }
        selectedPath = Hierarchy.SelectedItems?.OfType<HierarchyRow>().LastOrDefault()?.Path ?? [];
        Hierarchy.Version = revision;
    }

    private async Task ApplyHierarchy(JsonObject request)
    {
        if (!await LeavePending())
        {
            return;
        }
        Apply(() =>
        {
            var next = CoreApi.EditSmartPropDocument(document, [], "hierarchy", request.ToJsonString());
            SelectAddedHierarchyRows(next);
            return next;
        });
    }

    private void SelectAddedHierarchyRows(string next)
    {
        var oldKeys = Flatten(BuildRow(JsonNode.Parse(document)!.AsObject(), []).Children).Select(RowKey).ToHashSet();
        var added = Flatten(BuildRow(JsonNode.Parse(next)!.AsObject(), []).Children).Where(row => !oldKeys.Contains(RowKey(row))).ToList();
        if (added.Count > 0)
        {
            hierarchySelectionOverride = added.Where(row => !added.Any(parent => parent.Path.Length < row.Path.Length && row.Path.Take(parent.Path.Length).SequenceEqual(parent.Path))).Select(RowKey).ToHashSet();
        }
    }

    private void RememberHierarchySelection() => hierarchySelectionSnapshots[document] = Hierarchy.SelectedItems?.OfType<HierarchyRow>().Select(RowKey).ToArray() ?? [];

    private async Task ImportHierarchyFiles(string[] paths, string[] target)
    {
        if (paths.Length == 0 || !await LeavePending())
        {
            return;
        }
        Apply(() =>
        {
            var next = CoreApi.ImportSmartPropHierarchyFiles(document, target, paths, GameDirectory.Text ?? "");
            SelectAddedHierarchyRows(next);
            return next;
        });
    }

    private void ToggleHierarchyIsolation()
    {
        var row = Hierarchy.SelectedItems?.OfType<HierarchyRow>().LastOrDefault();
        isolatedHierarchyKey = row is null || isolatedHierarchyKey == RowKey(row) ? null : RowKey(row);
        ShowHierarchyScene(false);
    }

    private void ShowHierarchyScene(bool frame)
    {
        var scene = hierarchyScene;
        if (isolatedHierarchyKey is not null)
        {
            var root = Flatten(BuildRow(JsonNode.Parse(document)!.AsObject(), []).Children).FirstOrDefault(row => RowKey(row) == isolatedHierarchyKey);
            if (root is not null)
            {
                var ids = Flatten([root]).Select(row => int.TryParse(row.ElementId, out var id) ? id : -1).ToHashSet();
                scene = scene.Where(instance => ids.Contains(instance.ElementId)).ToArray();
            }
        }
        Viewport.SetScene(scene, frame);
        GpuViewport.SetScene(scene, frame);
        ObjectCount.Text = $"Objects: {scene.Count}";
    }

    internal async Task HierarchyAction(string action, string? className = null)
    {
        try
        {
            if (action == "add" && className is null)
            {
                HierarchyAdd.Flyout!.ShowAt(HierarchyAdd);
                return;
            }
            if (action == "rename")
            {
                Hierarchy.BeginRename();
                return;
            }
            if (action is "expand" or "collapse")
            {
                Hierarchy.ExpandAll(action == "expand");
                return;
            }
            if (action == "isolate")
            {
                ToggleHierarchyIsolation();
                return;
            }
            if (!await LeavePending())
            {
                return;
            }
            var selected = Hierarchy.SelectedPaths;
            var clipboard = TopLevel.GetTopLevel(this)?.Clipboard;
            if (action is "copy" or "cut")
            {
                if (selected.Length == 0 || clipboard is null)
                {
                    return;
                }
                await clipboard.SetTextAsync(CoreApi.CopySmartPropHierarchy(document, selected));
                if (action == "copy")
                {
                    return;
                }
                action = "remove";
            }
            var request = new JsonObject { ["action"] = action, ["paths"] = Paths(selected), ["target"] = Segments(selectedPath) };
            if (action is "paste" or "paste-replace")
            {
                var text = clipboard is null ? null : await clipboard.TryGetTextAsync();
                if (string.IsNullOrWhiteSpace(text))
                {
                    return;
                }
                if (action == "paste-replace")
                {
                    text = await ReplaceClipboard(text);
                    if (text is null)
                    {
                        return;
                    }
                }
                request["action"] = "paste";
                request["text"] = text;
            }
            else if (action == "preset")
            {
                var files = await HostWindow.StorageProvider.OpenFilePickerAsync(new() { Title = "New from SmartProp preset", FileTypeFilter = [SmartPropFiles], AllowMultiple = false });
                if (files.Count == 0)
                {
                    return;
                }
                request["action"] = "paste";
                request["text"] = await File.ReadAllTextAsync(files[0].TryGetLocalPath()!);
            }
            else if (action == "import")
            {
                var files = await HostWindow.StorageProvider.OpenFilePickerAsync(new()
                {
                    Title = "Import models or SmartProps",
                    AllowMultiple = true,
                    FileTypeFilter = [new FilePickerFileType("Source 2 assets") { Patterns = ["*.vmdl", "*.vsmart"] }]
                });
                await ImportHierarchyFiles(files.Select(file => file.TryGetLocalPath()).OfType<string>().ToArray(), selectedPath);
                return;
            }
            if (action == "add")
            {
                request["class"] = className;
            }
            await ApplyHierarchy(request);
        }
        catch (Exception exception)
        {
            Report(exception);
        }
    }

    private async Task<string?> ReplaceClipboard(string text)
    {
        var find = new TextBox { PlaceholderText = "Find" };
        var replace = new TextBox { PlaceholderText = "Replace with" };
        var dialog = new Window { Title = "Paste with replacement", Width = 360, SizeToContent = SizeToContent.Height, WindowStartupLocation = WindowStartupLocation.CenterOwner };
        var paste = new Button { Content = "Paste" };
        var cancel = new Button { Content = "Cancel" };
        paste.Click += (_, _) => dialog.Close(true);
        cancel.Click += (_, _) => dialog.Close(false);
        dialog.Content = new StackPanel { Margin = new global::Avalonia.Thickness(12), Spacing = 8, Children = { find, replace, paste, cancel } };
        return await dialog.ShowDialog<bool>(HostWindow) ? string.IsNullOrEmpty(find.Text) ? text : text.Replace(find.Text, replace.Text ?? "", StringComparison.Ordinal) : null;
    }
}
