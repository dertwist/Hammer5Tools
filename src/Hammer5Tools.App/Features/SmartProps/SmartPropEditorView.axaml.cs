using System.Globalization;
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Layout;
using Avalonia.LogicalTree;
using Avalonia.Media;
using Avalonia.Platform.Storage;
using Avalonia.Threading;
using Hammer5Tools.Core;

namespace Hammer5Tools.App.Features.SmartProps;

public sealed record HierarchyRow(string Label, string Subtitle, string[] Path, List<HierarchyRow> Children, string ElementId = "")
{
    public bool Expanded { get; set; } = true;
    public bool Enabled { get; init; } = true;
    public string? Note { get; init; }
}

public sealed partial class SmartPropEditorView : UserControl, IDisposable
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };
    private readonly Stack<string> undo = new();
    private readonly Stack<string> redo = new();
    private readonly Dictionary<string, SmartPropPropertyRow> fieldEditors = [];
    private string? displayedSource;
    private string[] componentPath = [];
    private static readonly JsonObject Presentation = LoadPresentation();
    private readonly Dictionary<int, (TextBox Editor, JsonNode? Original, string? Text)> variableEditors = [];
    private string document = CoreApi.CreateSmartPropDocument();
    private string savedDocument = "";
    private string? filePath;
    private string[] selectedPath = [];
    private bool refreshing;
    private bool pending;
    private string? pendingPanel;
    private bool prompting;
    private bool fileOperation;
    private JsonObject? componentClipboard;
    private bool rendererFailed;
    private bool frameNextScene = true;
    private CancellationTokenSource? evaluation;
    private int revision;
    private string? resourceName;
    public Task InitialLoadTask { get; private set; } = Task.CompletedTask;

    public SmartPropEditorView() : this(true)
    {
    }

    public SmartPropEditorView(bool loadDefaultResource)
    {
        InitializeComponent();
        savedDocument = document;
        SetupHierarchy();
        Refresh();
        SourceKv3.TextChanged += (_, _) =>
        {
            if (SourceKv3.Text != displayedSource)
            {
                MarkPending("SourceKv3");
            }
        };
        KeyDown += OnKeyDown;
        GpuViewport.ElementClicked += element =>
        {
            if (Hierarchy.ItemsSource is IEnumerable<HierarchyRow> rows && Flatten(rows).FirstOrDefault(row => row.ElementId == element.ToString(CultureInfo.InvariantCulture)) is { } row)
            {
                Hierarchy.SelectedItem = row;
            }
        };
        GpuViewport.RendererFailed += message =>
        {
            rendererFailed = true;
            Diagnostics.Text = message;
            Status.Text = "3D renderer unavailable. Showing wireframe preview.";
            GpuViewport.IsVisible = false;
            Viewport.IsVisible = true;
        };
        if (loadDefaultResource)
        {
            AttachedToVisualTree += OnFirstAttached;
        }
    }

    public string DocumentJson => document;
    public bool IsEvaluating => evaluation is not null;
    internal Task PreviewUpdateTask { get; private set; } = Task.CompletedTask;
    internal string PreviewDiagnostics => Diagnostics.Text ?? "";

    private void MarkPending(string panel)
    {
        if (!refreshing)
        {
            pending = true;
            pendingPanel = panel;
            SetEditorsEnabled();
            Status.Text = panel == "SourceKv3" ? "Unapplied source edits — use Apply source." : "Press Enter or leave the field to commit the edit.";
            UpdateTitle();
        }
    }

    private void SetEditorsEnabled()
    {
        SourceKv3.IsEnabled = !pending || pendingPanel == "SourceKv3";
        Fields.IsEnabled = !pending || pendingPanel == "Fields";
        VariableFields.IsEnabled = !pending || pendingPanel == "VariableFields";
    }

    private void SyncPending()
    {
        if (SourceKv3.Text != displayedSource)
        {
            MarkPending("SourceKv3");
        }
        if (fieldEditors.Values.Any(row => row.IsDirty))
        {
            MarkPending("Fields");
        }
        foreach (var (editor, _, text) in variableEditors.Values)
        {
            if (editor.Text != text)
            {
                MarkPending("VariableFields");
            }
        }
    }

    private void UpdateTitle()
    {
        DocumentStateChanged?.Invoke(this, EventArgs.Empty);
        UndoButton.IsEnabled = undo.Count > 0;
        RedoButton.IsEnabled = redo.Count > 0;
    }

    private void Refresh()
    {
        refreshing = true;
        try
        {
            var root = JsonNode.Parse(document)!.AsObject();
            RebuildHierarchy(root);
            ContentVersion.Value = root["m_nContentVersion"]?.GetValue<int>() ?? 0;
            SourceKv3.Text = CoreApi.SerializeSmartPropDocument(document);
            PopulateFields();
            PopulateVariables(root["m_Variables"] as JsonArray ?? []);
            PopulateChoices(root["m_Choices"] as JsonArray ?? []);
            History.ItemsSource = undo.Reverse().Select((_, index) => $"Edit {index + 1}").Prepend("Document loaded");
            displayedSource = SourceKv3.Text;
            pending = false;
            pendingPanel = null;
            SetEditorsEnabled();
            UpdateTitle();
        }
        finally
        {
            refreshing = false;
        }
    }

    private static string Format(JsonNode? value) => value?.ToJsonString(JsonOptions) ?? "null";

    private static IEnumerable<HierarchyRow> Flatten(IEnumerable<HierarchyRow> rows)
    {
        foreach (var row in rows)
        {
            yield return row;
            foreach (var child in Flatten(row.Children))
            {
                yield return child;
            }
        }
    }

    private static HierarchyRow BuildRow(JsonObject node, string[] path)
    {
        var className = node["_class"]?.ToString() ?? "CSmartPropRoot";
        var label = node["m_sLabel"]?.ToString() ?? className.Replace("CSmartPropElement_", "", StringComparison.Ordinal);
        var id = node["m_nElementID"]?.ToString();
        List<HierarchyRow> children = [];
        if (node["m_Children"] is JsonArray array)
        {
            for (var index = 0; index < array.Count; index++)
            {
                children.Add(BuildRow(array[index]!.AsObject(), [.. path, "m_Children", index.ToString(CultureInfo.InvariantCulture)]));
            }
        }
        return new(label, className.Replace("CSmartPropElement_", "", StringComparison.Ordinal), path, children, id ?? "")
        {
            Enabled = node["m_bEnabled"] is not JsonValue enabled || !enabled.TryGetValue<bool>(out var literal) || literal,
            Note = node["m_sNote"]?.ToString()
        };
    }

    private static HierarchyRow? FindRow(HierarchyRow row, string[] path)
    {
        if (row.Path.SequenceEqual(path))
        {
            return row;
        }
        foreach (var child in row.Children)
        {
            var match = FindRow(child, path);
            if (match is not null)
            {
                return match;
            }
        }
        return null;
    }

    private JsonObject SelectedObject()
    {
        var node = JsonNode.Parse(document)!;
        foreach (var segment in selectedPath)
        {
            node = node is JsonArray array ? array[int.Parse(segment, CultureInfo.InvariantCulture)]! : node[segment]!;
        }
        return node.AsObject();
    }

    private static JsonObject LoadPresentation()
    {
        using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("Hammer5Tools.App.Features.SmartProps.SmartPropPresentation.json")!;
        using var reader = new StreamReader(stream);
        return JsonNode.Parse(reader.ReadToEnd())!.AsObject();
    }

    private static string FriendlyName(string name)
    {
        name = name.Contains('_') ? name[(name.IndexOf('_') + 1)..] : name;
        name = Regex.Replace(name, "^(?:fl|[bnsvf])(?=[A-Z])", "");
        return Regex.Replace(name, "(?<=[a-z0-9])(?=[A-Z])", " ");
    }

    private static string ScalarText(JsonNode? node) => node is JsonValue scalar && scalar.TryGetValue<string>(out var text) ? text : node?.ToJsonString() ?? "";

    private JsonObject ComponentObject()
    {
        JsonNode node = SelectedObject();
        foreach (var segment in componentPath)
        {
            node = node is JsonArray array ? array[int.Parse(segment, CultureInfo.InvariantCulture)]! : node[segment]!;
        }
        return node.AsObject();
    }

    private void PopulateFields()
    {
        var element = SelectedObject();
        Components.Children.Clear();
        if (selectedPath.Length == 0)
        {
            Fields.Children.Clear();
            fieldEditors.Clear();
            DescriptionTitle.Text = "";
            DescriptionText.Text = "";
            return;
        }
        AddComponent(element, [], true);
        foreach (var (key, label) in new[] { ("m_Modifiers", "Modifiers"), ("m_SelectionCriteria", "Selection Criteria") })
        {
            var create = new Button { Content = "Create new", Classes = { "component" }, HorizontalAlignment = HorizontalAlignment.Left };
            var flyout = new MenuFlyout();
            var prefix = key == "m_Modifiers" ? "CSmartPropOperation_" : "CSmartPropSelectionCriteria_";
            foreach (var componentClass in Presentation["componentClasses"]!.AsArray().Select(value => value!.ToString()).Where(name => name.StartsWith(prefix, StringComparison.Ordinal)))
            {
                var item = new MenuItem { Header = FriendlyName(componentClass) };
                item.Click += (_, _) => AddComponentClass(componentClass);
                flyout.Items.Add(item);
            }
            create.Flyout = flyout;
            var header = new Grid { ColumnDefinitions = new ColumnDefinitions("*,*,Auto") };
            header.Children.Add(create);
            var title = new TextBlock { Text = label, Classes = { "muted" }, FontSize = 11, VerticalAlignment = VerticalAlignment.Center };
            Grid.SetColumn(title, 1);
            header.Children.Add(title);
            var paste = new Button { Content = "Paste", Classes = { "component" } };
            paste.Click += async (_, _) =>
            {
                if (componentClipboard is not null && await LeavePending())
                {
                    if (componentClipboard["_class"]?.ToString().StartsWith(prefix, StringComparison.Ordinal) == true)
                    {
                        Apply(() => CoreApi.EditSmartPropDocument(document, selectedPath, "paste-component", Format(componentClipboard)));
                    }
                }
            };
            Grid.SetColumn(paste, 2);
            header.Children.Add(paste);
            Components.Children.Add(new Border { Classes = { "componentSection" }, Child = header });
            if (element[key] is JsonArray components)
            {
                for (var index = 0; index < components.Count; index++)
                {
                    if (components[index] is JsonObject component)
                    {
                        AddComponent(component, [key, index.ToString(CultureInfo.InvariantCulture)], false);
                    }
                }
            }
        }
        Fields.Children.Clear();
        fieldEditors.Clear();
        JsonObject node;
        try
        {
            node = ComponentObject();
        }
        catch (Exception exception) when (exception is IndexOutOfRangeException or ArgumentOutOfRangeException or NullReferenceException)
        {
            componentPath = [];
            node = element;
        }
        var name = node["_class"]?.ToString() ?? "CSmartPropRoot";
        DescriptionTitle.Text = FriendlyName(name);
        var description = Presentation["tooltips"]?[name];
        DescriptionText.Text = description is JsonObject details ? details["description"]?.ToString()
            : description?.ToString() ?? "Select a property to see its description.";
        var className = name.Contains('_') ? name[(name.IndexOf('_') + 1)..] : name;
        var keys = Presentation["propertyOrder"]?[className] is JsonArray order
            ? order.Select(value => value!.GetValue<string>()).Concat(node.Select(item => item.Key)).Distinct()
            : node.Select(item => item.Key);
        foreach (var key in keys)
        {
            if (key is "_class" or "generic_data_type" or "m_nElementID" or "m_Children" or "m_Modifiers" or "m_SelectionCriteria" or "m_Variables" or "m_Choices" or "m_nContentVersion" or "m_sLabel" or "m_sNote" or "m_sReferenceObjectID" or "m_Comment" or "_comment")
            {
                continue;
            }
            AddField(Fields, key, node[key], [key], 0);
        }
    }

    private void AddComponent(JsonObject node, string[] path, bool element)
    {
        var name = FriendlyName(node["_class"]?.ToString() ?? "Document root");
        var id = node["m_nElementID"]?.ToString();
        var button = new Button
        {
            Content = $"{(element ? "▤" : "❖")}  {name}{(id is null ? "" : $"   ID:{id}")}",
            HorizontalAlignment = HorizontalAlignment.Stretch,
            HorizontalContentAlignment = HorizontalAlignment.Left,
            Classes = { "component" }
        };
        if (componentPath.SequenceEqual(path))
        {
            button.Classes.Add("active");
        }
        button.Click += async (_, _) =>
        {
            if (await LeavePending())
            {
                componentPath = path;
                PopulateFields();
            }
        };
        if (!element)
        {
            var copy = new MenuItem { Header = "Copy" };
            copy.Click += (_, _) => componentClipboard = node.DeepClone().AsObject();
            var delete = new MenuItem { Header = "Delete" };
            delete.Click += (_, _) => Apply(() => CoreApi.EditSmartPropDocument(document, [.. selectedPath, .. path], "remove"));
            button.ContextMenu = new ContextMenu { ItemsSource = new[] { copy, delete } };
        }
        Components.Children.Add(button);
    }

    private async void AddComponentClass(string className)
    {
        if (await LeavePending())
        {
            Apply(() => CoreApi.EditSmartPropDocument(document, selectedPath, "add-component", JsonValue.Create(className)!.ToJsonString()));
        }
    }

    private void AddField(StackPanel panel, string key, JsonNode? value, string[] path, int depth)
    {
        var className = ComponentObject()["_class"]?.ToString()?.Split('_').Last() ?? "";
        var enums = Presentation["enums"]?.AsObject().FirstOrDefault(item => key.Contains(item.Key, StringComparison.Ordinal)).Value as JsonArray;
        if (className == "PlaceOnMesh" && key == "m_nPickMode")
        {
            enums = new JsonArray("FIRST_OPEN_EDGE", "FIRST_CLOSED_EDGE", "UVMAP1", "UVMAP2");
        }
        if (className is "MaterialTint" or "RandomColorTintColor" && key == "m_SelectionMode")
        {
            enums = new JsonArray("SPECIFIC_COLOR", "GRADIENT_RANDOM", "GRADIENT_RANDOM_STOP", "GRADIENT_LOCATION");
        }
        var kind = Presentation["fieldTypes"]?[key]?.ToString() ?? SmartPropPropertyRow.InferType(key, value);
        if (kind == "Float" && (key.StartsWith("m_n", StringComparison.Ordinal) || key is "m_ChoiceSelection" or "m_SpecificChildIndex" or "m_ColorSelection"))
        {
            kind = "Int";
        }
        var variables = JsonNode.Parse(document)!["m_Variables"]?.AsArray().OfType<JsonObject>().Select(variable => variable["m_VariableName"]?.ToString() ?? "").ToArray() ?? [];
        var property = new SmartPropPropertyRow(key, value, kind, enums?.Select(item => item!.ToString()).ToArray() ?? [], variables);
        property.ReferenceSelected += id =>
        {
            if (Hierarchy.ItemsSource is IEnumerable<HierarchyRow> rows && Flatten(rows).FirstOrDefault(row => row.ElementId == id.ToString(CultureInfo.InvariantCulture)) is { } target)
            {
                Hierarchy.SelectedItem = target;
            }
        };
        if (panel.Children.Count % 2 == 0)
        {
            property.Classes.Add("alternate");
        }
        var tooltip = Presentation["tooltips"]?[key]?.ToString();
        ToolTip.SetTip(property, tooltip);
        property.PointerPressed += (_, _) =>
        {
            DescriptionTitle.Text = FriendlyName(key);
            DescriptionText.Text = tooltip ?? "No description is available for this property.";
        };
        property.Changed += () =>
        {
            if (fieldEditors.GetValueOrDefault(key) == property)
            {
                MarkPending("Fields");
            }
        };
        property.CommitRequested += () => Dispatcher.UIThread.Post(() =>
        {
            if (fieldEditors.GetValueOrDefault(key) == property && pendingPanel == "Fields")
            {
                ApplyFieldsClicked(null, new RoutedEventArgs());
            }
        });
        fieldEditors[key] = property;
        panel.Children.Add(property);
    }

    private async void HierarchySelectionChanged(object? sender, SelectionChangedEventArgs args)
    {
        if (refreshing)
        {
            return;
        }
        var selection = Hierarchy.SelectedItems?.OfType<HierarchyRow>().LastOrDefault();
        if (!await LeavePending())
        {
            return;
        }
        selectedPath = selection?.Path ?? [];
        componentPath = [];
        refreshing = true;
        PopulateFields();
        refreshing = false;
        Viewport.SelectedElementId = selection is not null && int.TryParse(selection.ElementId, out var id) ? id : null;
        GpuViewport.SelectedElementId = Viewport.SelectedElementId;
    }

    private void Commit(string next)
    {
        next = CoreApi.ValidateSmartPropDocument(next);
        if (next != document)
        {
            RememberHierarchySelection();
            undo.Push(document);
            redo.Clear();
            document = next;
            revision++;
        }
        Refresh();
        PreviewUpdateTask = Evaluate();
    }

    private void ClearScene()
    {
        hierarchyScene = [];
        isolatedHierarchyKey = null;
        Viewport.ClearScene();
        GpuViewport.ClearScene();
        ObjectCount.Text = "Objects: 0";
    }

    private void Report(Exception exception)
    {
        Status.Text = exception.Message;
        Diagnostics.Text = exception.ToString();
    }

    private void Apply(Func<string> action, string? panel = null)
    {
        try
        {
            SyncPending();
            if (pending && pendingPanel != panel)
            {
                throw new InvalidOperationException("Apply the pending edits in their original panel first.");
            }
            Commit(action());
        }
        catch (Exception exception)
        {
            Report(exception);
        }
    }

    private void ApplyFieldsClicked(object? sender, RoutedEventArgs args) => Apply(() =>
    {
        var obj = ComponentObject();
        foreach (var (key, row) in fieldEditors)
        {
            if (row.IsDirty)
            {
                obj[key] = row.ReadValue();
            }
        }
        return CoreApi.EditSmartPropDocument(document, [.. selectedPath, .. componentPath], "replace", Format(obj));
    }, "Fields");

    private void ApplySourceClicked(object? sender, RoutedEventArgs args) => Apply(() => CoreApi.ParseSmartPropDocument(SourceKv3.Text ?? ""), "SourceKv3");

    private Task EditHierarchy(string operation) => HierarchyAction(operation);

    private async void AddGroupClicked(object? sender, RoutedEventArgs args) => await HierarchyAction("add", "CSmartPropElement_Group");
    private async void AddModelClicked(object? sender, RoutedEventArgs args) => await HierarchyAction("add", "CSmartPropElement_Model");
    private async void DuplicateClicked(object? sender, RoutedEventArgs args) => await HierarchyAction("duplicate");
    private async void DeleteClicked(object? sender, RoutedEventArgs args) => await HierarchyAction("remove");
    private async void MoveUpClicked(object? sender, RoutedEventArgs args) => await HierarchyAction("up");
    private async void MoveDownClicked(object? sender, RoutedEventArgs args) => await HierarchyAction("down");

    private async Task<bool> AskDiscard(string message)
    {
        if (prompting)
        {
            return false;
        }
        prompting = true;
        try
        {
            var dialog = new Window { Title = "Unsaved edits", Width = 450, SizeToContent = SizeToContent.Height, CanResize = false, WindowStartupLocation = WindowStartupLocation.CenterOwner };
            var keep = new Button { Content = "Keep editing" };
            var discard = new Button { Content = "Discard edits" };
            keep.Click += (_, _) => dialog.Close(false);
            discard.Click += (_, _) => dialog.Close(true);
            dialog.Content = new StackPanel
            {
                Margin = new global::Avalonia.Thickness(20),
                Spacing = 16,
                Children =
                {
                    new TextBlock { Text = message, TextWrapping = TextWrapping.Wrap },
                    new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8, HorizontalAlignment = HorizontalAlignment.Right, Children = { keep, discard } }
                }
            };
            return await dialog.ShowDialog<bool>(HostWindow);
        }
        finally
        {
            prompting = false;
        }
    }

    private async Task<bool> LeavePending()
    {
        SyncPending();
        if (pendingPanel == "Fields")
        {
            ApplyFieldsClicked(null, new RoutedEventArgs());
            return !pending;
        }
        if (pendingPanel == "VariableFields")
        {
            ApplyVariableFieldsClicked(null, new RoutedEventArgs());
            return !pending;
        }
        if (!pending)
        {
            return true;
        }
        if (!await AskDiscard("This panel has unapplied edits. Apply them before continuing, or discard them."))
        {
            return false;
        }
        Refresh();
        return true;
    }

    private async Task<bool> LeaveDocument()
    {
        SyncPending();
        return document == savedDocument && !pending
            || await AskDiscard("The document has unsaved edits. Save before continuing, or discard them.");
    }

    private void SetDocument(string json, string? path)
    {
        document = CoreApi.ValidateSmartPropDocument(json);
        savedDocument = document;
        filePath = path;
        resourceName = null;
        selectedPath = [];
        Hierarchy.SelectedItems?.Clear();
        hierarchySelectionSnapshots.Clear();
        hierarchyExpansion.Clear();
        hierarchySelectionOverride = BuildRow(JsonNode.Parse(document)!.AsObject(), []).Children.Take(1).Select(RowKey).ToHashSet();
        componentPath = [];
        undo.Clear();
        redo.Clear();
        revision++;
        evaluation?.Cancel();
        frameNextScene = true;
        ClearScene();
        Refresh();
        Status.Text = "Ready. Select an element to edit its properties.";
    }

    private async void NewClicked(object? sender, RoutedEventArgs args)
    {
        if (!fileOperation && await LeaveDocument())
        {
            SetDocument(CoreApi.CreateSmartPropDocument(), null);
        }
    }

    private static FilePickerFileType SmartPropFiles { get; } = new("Source SmartProp") { Patterns = ["*.vsmart", "*.vdata"] };

    private async void OpenClicked(object? sender, RoutedEventArgs args)
    {
        if (fileOperation || !await LeaveDocument())
        {
            return;
        }
        try
        {
            fileOperation = true;
            var files = await HostWindow.StorageProvider.OpenFilePickerAsync(new() { Title = "Open source SmartProp", AllowMultiple = false, FileTypeFilter = [SmartPropFiles] });
            if (files.Count == 0)
            {
                return;
            }
            var path = files[0].TryGetLocalPath() ?? throw new IOException("Select a local source file.");
            IsEnabled = false;
            var json = await Task.Run(() => CoreApi.ParseSmartPropDocument(File.ReadAllText(path)));
            SetDocument(json, path);
            await Evaluate();
        }
        catch (Exception exception)
        {
            Report(exception);
        }
        finally
        {
            fileOperation = false;
            IsEnabled = true;
        }
    }

    private async Task<bool> Save(bool saveAs)
    {
        if (fileOperation)
        {
            return false;
        }
        SyncPending();
        if (pendingPanel == "Fields")
        {
            ApplyFieldsClicked(null, new RoutedEventArgs());
        }
        else if (pendingPanel == "VariableFields")
        {
            ApplyVariableFieldsClicked(null, new RoutedEventArgs());
        }
        if (pending)
        {
            Status.Text = "Apply the pending panel edits before saving.";
            return false;
        }
        try
        {
            fileOperation = true;
            var path = filePath;
            if (saveAs || path is null)
            {
                var file = await HostWindow.StorageProvider.SaveFilePickerAsync(new() { Title = "Save source SmartProp", SuggestedFileName = path is null ? "untitled.vsmart" : Path.GetFileName(path), DefaultExtension = "vsmart", FileTypeChoices = [SmartPropFiles] });
                if (file is null)
                {
                    return false;
                }
                path = file.TryGetLocalPath() ?? throw new IOException("Select a local destination.");
            }
            var snapshot = document;
            var backup = await Task.Run(() => CoreApi.SaveSmartPropDocument(path, snapshot));
            filePath = path;
            savedDocument = snapshot;
            UpdateTitle();
            Status.Text = $"Saved {Path.GetFileName(path)}{(backup is null ? "." : $" · Backup: {Path.GetFileName(backup)}")}";
            return true;
        }
        catch (Exception exception)
        {
            Report(exception);
            return false;
        }
        finally
        {
            fileOperation = false;
        }
    }

    private async void SaveClicked(object? sender, RoutedEventArgs args) => await Save(false);
    private async void SaveAsClicked(object? sender, RoutedEventArgs args) => await Save(true);

    private async Task UndoRedo(bool isUndo)
    {
        if (!await LeavePending())
        {
            return;
        }
        var source = isUndo ? undo : redo;
        var destination = isUndo ? redo : undo;
        if (source.TryPop(out var snapshot))
        {
            RememberHierarchySelection();
            destination.Push(document);
            document = snapshot;
            hierarchySelectionOverride = hierarchySelectionSnapshots.GetValueOrDefault(snapshot)?.ToHashSet();
            revision++;
            evaluation?.Cancel();
            Refresh();
            PreviewUpdateTask = Evaluate();
        }
    }

    private async void UndoClicked(object? sender, RoutedEventArgs args) => await UndoRedo(true);
    private async void RedoClicked(object? sender, RoutedEventArgs args) => await UndoRedo(false);
    private void FrameClicked(object? sender, RoutedEventArgs args)
    {
        Viewport.FrameScene();
        GpuViewport.FrameScene();
    }

    internal async Task Evaluate()
    {
        SyncPending();
        if (pending)
        {
            Status.Text = "Apply pending edits before evaluating.";
            return;
        }
        evaluation?.Cancel();
        var cancellation = new CancellationTokenSource();
        evaluation = cancellation;
        var snapshot = document;
        var generation = revision;
        var game = GameDirectory.Text?.Trim() ?? "";
        var addon = AddonName.Text?.Trim() ?? "";
        Status.Text = "Evaluating SmartProp and loading geometry…";
        try
        {
            var scene = await Task.Run(() => CoreApi.BuildSmartPropPreview(snapshot, game, addon, filePath, cancellation.Token), cancellation.Token);
            if (generation != revision || evaluation != cancellation)
            {
                return;
            }
            var instances = scene.Instances.Select(item => new ViewportInstance(item.Placement.ElementId, item.Placement.ModelName, item.Placement.Transform,
                item.Geometry?.Vertices.ToArray() ?? [], item.Geometry?.Indices.ToArray() ?? [], item.Geometry, item.Placement.TintColor)).ToList();
            hierarchyScene = instances;
            ShowHierarchyScene(frameNextScene);
            frameNextScene = false;
            Diagnostics.Text = scene.Diagnostics.Count == 0 ? "No evaluation diagnostics." : string.Join(Environment.NewLine, scene.Diagnostics);
            var loadedCount = scene.Instances.Count(instance => instance.Geometry is not null);
            GpuViewport.IsVisible = !rendererFailed && loadedCount > 0;
            Viewport.IsVisible = !GpuViewport.IsVisible;
            Status.Text = $"{scene.Instances.Count} placements · {loadedCount} with geometry · {scene.Instances.Count - loadedCount} without geometry · {scene.Diagnostics.Count} diagnostics";
        }
        catch (OperationCanceledException)
        {
            if (evaluation == cancellation)
            {
                Status.Text = "Evaluation cancelled.";
            }
        }
        catch (Exception exception)
        {
            if (generation == revision && evaluation == cancellation)
            {
                Report(exception);
            }
        }
        finally
        {
            if (evaluation == cancellation)
            {
                evaluation = null;
            }
            cancellation.Dispose();
        }
    }

    private async void OnKeyDown(object? sender, KeyEventArgs args)
    {
        if (!args.KeyModifiers.HasFlag(KeyModifiers.Control))
        {
            return;
        }
        if (args.Key == Key.S)
        {
            args.Handled = true;
            await Save(args.KeyModifiers.HasFlag(KeyModifiers.Shift));
        }
        else if (args.Key == Key.Z && args.Source is not TextBox)
        {
            args.Handled = true;
            await UndoRedo(!args.KeyModifiers.HasFlag(KeyModifiers.Shift));
        }
    }

    private async void ExampleClicked(object? sender, RoutedEventArgs args)
    {
        if (fileOperation || !await LeaveDocument())
        {
            return;
        }
        try
        {
            SetDocument(CoreApi.ParseSmartPropDocument(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "Example.vsmart"))), null);
            savedDocument = CoreApi.CreateSmartPropDocument();
            UpdateTitle();
            await Evaluate();
        }
        catch (Exception exception)
        {
            Report(exception);
        }
    }

    private async Task LoadDefaultResource()
    {
        try
        {
            Status.Text = "Finding Counter-Strike 2…";
            if (string.IsNullOrWhiteSpace(GameDirectory.Text))
            {
                GameDirectory.Text = await Task.Run(CoreApi.FindCs2GameDirectory) ?? "";
            }
            if (GameDirectory.Text.Length == 0)
            {
                Status.Text = "CS2 not found. The default cargo van requires an installed copy of CS2.";
                return;
            }
            await LoadResource("models/vehicles/cargovan_01/cargovan_01.vsmart");
        }
        catch (Exception exception)
        {
            Report(exception);
        }
    }

    private async Task LoadResource(string resource)
    {
        if (fileOperation || !await LeaveDocument())
        {
            return;
        }
        fileOperation = true;
        IsEnabled = false;
        try
        {
            Status.Text = $"Loading {resource}…";
            var game = GameDirectory.Text?.Trim() ?? "";
            var addon = AddonName.Text?.Trim() ?? "";
            var json = await Task.Run(() => CoreApi.LoadSmartPropResource(resource, game, addon));
            SetDocument(json, null);
            resourceName = resource;
            UpdateTitle();
            await Evaluate();
        }
        catch (Exception exception)
        {
            Report(exception);
        }
        finally
        {
            fileOperation = false;
            IsEnabled = true;
        }
    }

    private async void DefaultResourceClicked(object? sender, RoutedEventArgs args) => await LoadResource("models/vehicles/cargovan_01/cargovan_01.vsmart");
    private readonly TextBox GameDirectory = new() { PlaceholderText = "Folder containing csgo and csgo_addons" };
    private readonly TextBox AddonName = new() { PlaceholderText = "Optional" };
    private readonly TextBox Diagnostics = new() { IsReadOnly = true, AcceptsReturn = true, MinHeight = 180, Classes = { "code" } };

    private void ShadingModeChanged(object? sender, SelectionChangedEventArgs args)
    {
        if (GpuViewport is not null && ShadingMode.SelectedItem is ComboBoxItem item)
        {
            GpuViewport.ShadingMode = item.Content?.ToString() ?? "Textured";
        }
    }

    private void ShowGridChanged(object? sender, RoutedEventArgs args)
    {
        if (GpuViewport is not null)
        {
            GpuViewport.ShowGrid = ShowGrid.IsChecked == true;
        }
    }

    private void GridStepChanged(object? sender, SelectionChangedEventArgs args)
    {
        if (GpuViewport is not null && GridStep.SelectedItem is ComboBoxItem item && float.TryParse(item.Content?.ToString(), out var step))
        {
            GpuViewport.GridStep = step;
        }
    }

    private void PopulateVariables(JsonArray variables)
    {
        variableEditors.Clear();
        VariableFields.Children.Clear();
        for (var index = 0; index < variables.Count; index++)
        {
            if (variables[index] is not JsonObject variable)
            {
                continue;
            }
            var name = variable["m_VariableName"]?.ToString() ?? $"Variable {index}";
            var type = variable["_class"]?.ToString().Replace("CSmartPropVariable_", "", StringComparison.Ordinal) ?? "";
            var original = variable["m_DefaultValue"];
            var value = original is JsonValue scalar && scalar.TryGetValue<string>(out var text) ? text : Format(original);

            var editor = new TextBox { Text = value, AcceptsReturn = original is JsonObject or JsonArray, TextWrapping = TextWrapping.Wrap };
            var variableIndex = index;
            editor.TextChanged += (_, _) =>
            {
                if (variableEditors.GetValueOrDefault(variableIndex).Editor == editor && editor.Text != value)
                {
                    MarkPending("VariableFields");
                }
            };
            editor.LostFocus += (_, _) => Dispatcher.UIThread.Post(() =>
            {
                if (variableEditors.GetValueOrDefault(variableIndex).Editor == editor && pendingPanel == "VariableFields")
                {
                    ApplyVariableFieldsClicked(null, new RoutedEventArgs());
                }
            });
            editor.KeyDown += (_, args) =>
            {
                if (args.Key == Key.Enter)
                {
                    ApplyVariableFieldsClicked(null, new RoutedEventArgs());
                    args.Handled = true;
                }
            };
            variableEditors[index] = (editor, original, value);
            var header = new Grid { ColumnDefinitions = new ColumnDefinitions("*,80"), MinWidth = 140 };
            header.Children.Add(new TextBlock { Text = name, FontSize = 11, VerticalAlignment = VerticalAlignment.Center });
            var typeLabel = new TextBlock { Text = type, FontSize = 10, Classes = { "muted" }, HorizontalAlignment = HorizontalAlignment.Right };
            Grid.SetColumn(typeLabel, 1);
            header.Children.Add(typeLabel);
            var content = new Grid { ColumnDefinitions = new ColumnDefinitions("90,*"), Margin = new global::Avalonia.Thickness(6, 2) };
            content.Children.Add(new TextBlock { Text = "Default value", FontSize = 11, VerticalAlignment = VerticalAlignment.Center });
            Grid.SetColumn(editor, 1);
            content.Children.Add(editor);
            var row = new Expander { Header = header, Content = content, Tag = name, Classes = { "variableRow" }, HorizontalAlignment = HorizontalAlignment.Stretch };
            row.IsVisible = name.Contains(VariableFilter.Text ?? "", StringComparison.OrdinalIgnoreCase);
            VariableFields.Children.Add(row);
        }
    }

    private void ApplyVariableFieldsClicked(object? sender, RoutedEventArgs args) => Apply(() =>
    {
        var root = JsonNode.Parse(document)!;
        foreach (var (index, (editor, original, _)) in variableEditors)
        {
            root["m_Variables"]![index]!["m_DefaultValue"] = original is JsonValue scalar && scalar.TryGetValue<string>(out _)
                ? JsonValue.Create(editor.Text ?? "") : JsonNode.Parse(editor.Text ?? "null");
        }
        return CoreApi.EditSmartPropDocument(document, [], "replace", Format(root));
    }, "VariableFields");

    private void PopulateChoices(JsonArray choices)
    {
        ChoiceFields.Children.Clear();
        foreach (var choice in choices.OfType<JsonObject>())
        {
            var label = choice["m_Name"]?.ToString() ?? choice["m_ChoiceName"]?.ToString() ?? choice["m_VariableName"]?.ToString() ?? "Choice";
            var row = new Grid { ColumnDefinitions = new ColumnDefinitions("*,*"), Classes = { "propertyRow" }, MinHeight = 24 };
            row.Children.Add(new TextBlock { Text = label, Margin = new global::Avalonia.Thickness(4), FontSize = 11 });
            var value = new TextBlock { Text = ScalarText(choice["m_DefaultValue"] ?? choice["m_Value"]), Margin = new global::Avalonia.Thickness(4), FontSize = 11 };
            Grid.SetColumn(value, 1);
            row.Children.Add(value);
            ChoiceFields.Children.Add(row);
        }
    }

    private static List<HierarchyRow> FilterRows(IEnumerable<HierarchyRow> rows, string filter)
    {
        if (string.IsNullOrWhiteSpace(filter))
        {
            return rows.ToList();
        }
        return rows.Select(row => row with { Children = FilterRows(row.Children, filter) })
            .Where(row => row.Children.Count > 0 || row.Label.Contains(filter, StringComparison.OrdinalIgnoreCase) || row.Subtitle.Contains(filter, StringComparison.OrdinalIgnoreCase)).ToList();
    }

    private void HierarchyFilterChanged(object? sender, TextChangedEventArgs args)
    {
        if (Hierarchy is null || refreshing)
        {
            return;
        }
        refreshing = true;
        RebuildHierarchy(JsonNode.Parse(document)!.AsObject());
        refreshing = false;
    }

    private void VariableFilterChanged(object? sender, TextChangedEventArgs args)
    {
        if (VariableFields is null)
        {
            return;
        }
        foreach (var row in VariableFields.Children)
        {
            row.IsVisible = row.Tag?.ToString()?.Contains(VariableFilter.Text ?? "", StringComparison.OrdinalIgnoreCase) ?? true;
        }
    }

    private void ContentVersionChanged(object? sender, NumericUpDownValueChangedEventArgs args)
    {
        if (!refreshing && ContentVersion is not null && args.NewValue is { } value)
        {
            Apply(() =>
            {
                var root = JsonNode.Parse(document)!;
                root["m_nContentVersion"] = (int)value;
                return CoreApi.EditSmartPropDocument(document, [], "replace", Format(root));
            });
        }
    }

    private Window HostWindow => TopLevel.GetTopLevel(this) as Window
        ?? throw new InvalidOperationException("The SmartProp editor is not attached to a window.");

    public event EventHandler? DocumentStateChanged;
    public string DocumentTitle => Path.GetFileName(filePath ?? resourceName ?? "Untitled.vsmart");
    public string? DocumentPath => filePath;
    public bool HasUnsavedChanges => document != savedDocument || pending;
    public bool CanUndo => undo.Count > 0;
    public bool CanRedo => redo.Count > 0;

    private void OnFirstAttached(object? sender, global::Avalonia.VisualTreeAttachmentEventArgs args)
    {
        AttachedToVisualTree -= OnFirstAttached;
        InitialLoadTask = LoadDefaultResource();
    }

    public void ConfigureResources(string? gameDirectory, string addon)
    {
        GameDirectory.Text = gameDirectory ?? "";
        AddonName.Text = addon;
    }

    public async Task OpenDocumentAsync(string path)
    {
        fileOperation = true;
        IsEnabled = false;
        try
        {
            var json = await Task.Run(() => CoreApi.ParseSmartPropDocument(File.ReadAllText(path)));
            SetDocument(json, Path.GetFullPath(path));
            await Evaluate();
        }
        finally
        {
            fileOperation = false;
            IsEnabled = true;
        }
    }

    public async Task<bool> SaveDocumentAsync()
    {
        return await Save(false);
    }

    public Task UndoDocumentAsync() => UndoRedo(true);
    public Task RedoDocumentAsync() => UndoRedo(false);
    public Task<bool> ConfirmCloseAsync() => LeaveDocument();

    public void Dispose()
    {
        evaluation?.Cancel();
        GC.SuppressFinalize(this);
    }
}
