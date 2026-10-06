using System.Numerics;
using System.Text.Json.Nodes;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Headless;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.LogicalTree;
using Avalonia.Threading;
using Avalonia.VisualTree;
using Hammer5Tools.App.Features.SmartProps;
using Hammer5Tools.Core;
using Hammer5Tools.SmartProp.Tests;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

if (args.Length > 0 && args[0] is "--gpu" or "--main-gpu")
{
    var nativeApp = args[0] == "--main-gpu" ? AppBuilder.Configure<IntegratedGpuApp>() : AppBuilder.Configure<App>();
    nativeApp.UsePlatformDetect().AfterSetup(_ => Dispatcher.UIThread.Post(async () =>
    {
        var lifetime = (IClassicDesktopStyleApplicationLifetime)Application.Current!.ApplicationLifetime!;
        try
        {
            await Task.Delay(200);
            var desktopWindow = lifetime.MainWindow!;
            var editor = desktopWindow is MainWindow preview ? preview.Editor
                : ((Hammer5Tools.App.Features.Shell.ShellViewModel)desktopWindow.DataContext!).Documents.OfType<SmartPropEditorViewModel>().Single().View;
            await editor.InitialLoadTask;
            var gpu = editor.FindControl<SmartPropGlViewport>("GpuViewport")!;
            var deadline = System.Diagnostics.Stopwatch.StartNew();
            while ((!gpu.IsRendererReady || gpu.MeshCount != 10 || !editor.InitialLoadTask.IsCompleted)
                && deadline.Elapsed < TimeSpan.FromSeconds(10))
            {
                await Task.Delay(50);
            }
            if (!gpu.IsRendererReady || gpu.MeshCount != 10)
            {
                throw new InvalidOperationException($"{editor.FindControl<TextBlock>("Status")!.Text}\n{editor.PreviewDiagnostics}");
            }
            var capturePath = args.Length > 1 ? args[1] : Path.Combine(Path.GetTempPath(), "h5t-cargovan-textured.png");
            var viewportPoint = gpu.TranslatePoint(new Point(gpu.Bounds.Width / 2, gpu.Bounds.Height / 2), desktopWindow)!.Value;
            if (desktopWindow.InputHitTest(viewportPoint) != gpu)
            {
                throw new InvalidOperationException("Camera input must hit the textured GPU viewport, not the wireframe fallback.");
            }
            await gpu.CaptureFrame(capturePath).WaitAsync(TimeSpan.FromSeconds(10));
            var initialCameraPosition = gpu.CameraPosition;
            var pointer = new Pointer(1, PointerType.Mouse, true);
            var middlePressed = new PointerPointProperties(RawInputModifiers.MiddleMouseButton, PointerUpdateKind.MiddleButtonPressed);
            var hit = (InputElement)desktopWindow.InputHitTest(viewportPoint)!;
            hit.RaiseEvent(new PointerPressedEventArgs(hit, pointer, desktopWindow, viewportPoint, 1, middlePressed, KeyModifiers.None));
            var movedPoint = viewportPoint + new global::Avalonia.Vector(70, 25);
            hit.RaiseEvent(new PointerEventArgs(InputElement.PointerMovedEvent, hit, pointer, desktopWindow, movedPoint, 2,
                new PointerPointProperties(RawInputModifiers.MiddleMouseButton, PointerUpdateKind.Other), KeyModifiers.None));
            hit.RaiseEvent(new PointerReleasedEventArgs(hit, pointer, desktopWindow, movedPoint, 3,
                new PointerPointProperties(RawInputModifiers.None, PointerUpdateKind.MiddleButtonReleased), KeyModifiers.None, MouseButton.Middle));
            if (Vector3.Distance(initialCameraPosition, gpu.CameraPosition) < 1 || gpu.ShadingMode != "Textured"
                || editor.FindControl<SmartPropViewport>("Viewport")!.IsVisible)
            {
                throw new InvalidOperationException("Orbit input must rotate the textured scene without displaying the wireframe fallback.");
            }
            await gpu.CaptureFrame(Path.ChangeExtension(capturePath, ".orbit.png")).WaitAsync(TimeSpan.FromSeconds(10));
            var cameraPosition = gpu.CameraPosition;
            var contentVersion = editor.FindControl<NumericUpDown>("ContentVersion")!;
            contentVersion.Value = (contentVersion.Value ?? 0) + 1;
            if (gpu.MeshCount != 10)
            {
                throw new InvalidOperationException("Editing must keep the current scene visible while evaluating.");
            }
            await editor.PreviewUpdateTask;
            if (gpu.MeshCount != 10 || Vector3.Distance(cameraPosition, gpu.CameraPosition) > 0.001f)
            {
                throw new InvalidOperationException("Property updates must preserve the camera and loaded model.");
            }
            gpu.ShadingMode = "Solid";
            await gpu.CaptureFrame(Path.ChangeExtension(capturePath, ".solid.png")).WaitAsync(TimeSpan.FromSeconds(10));
            gpu.ShadingMode = "Wireframe";
            await gpu.CaptureFrame(Path.ChangeExtension(capturePath, ".wireframe.png")).WaitAsync(TimeSpan.FromSeconds(10));
            Console.WriteLine("Native GPU check passed: camera input rotates the textured cargo van, fallback hidden, 10 meshes, textured/orbit/solid/wireframe frames captured.");
            lifetime.Shutdown();
        }
        catch (Exception exception)
        {
            Console.Error.WriteLine(exception);
            lifetime.Shutdown(1);
        }
    })).StartWithClassicDesktopLifetime(args);
    return;
}

if (args.Contains("--game-assets", StringComparer.Ordinal))
{
    var game = CoreApi.FindCs2GameDirectory() ?? throw new InvalidOperationException("CS2 not found.");
    var addon = args.Length > 1 ? args[1] : "";
    var loaded = CoreApi.LoadSmartPropResource("models/vehicles/cargovan_01/cargovan_01.vsmart", game, addon);
    var scene = CoreApi.BuildSmartPropPreview(loaded, game, addon);
    Console.WriteLine($"Cargo van: {scene.Instances.Count} placements, {scene.Instances.Count(instance => instance.Geometry is not null)} meshes, {scene.Instances.Sum(instance => instance.Geometry?.SubMeshes.Count(mesh => mesh.Material.BaseColor is not null) ?? 0)} textured submeshes.");
    if (scene.Instances.Count == 0 || scene.Instances.Any(instance => instance.Geometry is null))
    {
        throw new InvalidOperationException(string.Join(Environment.NewLine, scene.Diagnostics));
    }
    return;
}

AppBuilder.Configure<App>().UseHeadless(new AvaloniaHeadlessPlatformOptions { UseHeadlessDrawing = false }).UseSkia().SetupWithoutStarting();
var window = new MainWindow(false);
window.Show();
Dispatcher.UIThread.RunJobs();

static void Require(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}

var camera = new ViewportCamera();
var eye = camera.Position;
camera.Look(new global::Avalonia.Vector(50, 20));
Require(Vector3.Distance(eye, camera.Position) < 0.001f, "RMB look must rotate around the camera eye.");
var target = camera.Center;
camera.Orbit(new global::Avalonia.Vector(50, 20));
Require(camera.Center == target && Vector3.Distance(eye, camera.Position) > 1, "MMB orbit must preserve the target and move the eye.");

var dynamicRow = new SmartPropPropertyRow("m_flValue", JsonNode.Parse("{\"m_Expression\":\"1\",\"custom\":42}"), "Float", [], []);
dynamicRow.GetLogicalDescendants().OfType<TextBox>().Single(input => input.Tag?.ToString() == "m_flValue/expression").Text = "2";
var dynamicValue = dynamicRow.ReadValue()!;
Require(dynamicValue["custom"]!.GetValue<int>() == 42 && dynamicValue["m_Expression"]!.GetValue<string>() == "2", "Expression edits must preserve unknown metadata.");

static void Click(MainWindow window, string content)
{
    static IEnumerable<MenuItem> MenuItems(IEnumerable<MenuItem> items)
    {
        foreach (var item in items)
        {
            yield return item;
            foreach (var child in MenuItems(item.Items.OfType<MenuItem>()))
            {
                yield return child;
            }
        }
    }
    if (content == "Evaluate")
    {
        _ = ((MainWindow)window).Evaluate();
        Dispatcher.UIThread.RunJobs();
        return;
    }
    if (content is "Apply fields" or "Apply variables")
    {
        var field = window.GetLogicalDescendants().OfType<TextBox>().LastOrDefault(input => input.Tag is not null && input.Text is "models/test.vmdl" or "-128")
            ?? window.FindControl<StackPanel>("VariableFields")!.GetLogicalDescendants().OfType<TextBox>().Single();
        field.RaiseEvent(new KeyEventArgs { RoutedEvent = global::Avalonia.Input.InputElement.KeyDownEvent, Key = global::Avalonia.Input.Key.Enter });
        Dispatcher.UIThread.RunJobs();
        return;
    }
    var text = content switch { "+ Group" => "Add group", "+ Model" => "Add model", _ => content };
    var button = window.GetLogicalDescendants().OfType<Button>().FirstOrDefault(item => item.Content?.ToString() == text);
    if (button is not null)
    {
        button.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    }
    else
    {
        var menu = MenuItems(window.GetLogicalDescendants().OfType<Menu>().SelectMany(menu => menu.Items.OfType<MenuItem>())).First(item => item.Header?.ToString() == text);
        menu.RaiseEvent(new RoutedEventArgs(MenuItem.ClickEvent));
    }
    Dispatcher.UIThread.RunJobs();
}

Click(window, "+ Group");
var tree = window.FindControl<TreeView>("Hierarchy")!;
var root = ((IEnumerable<HierarchyRow>)tree.ItemsSource!).Single();
tree.SelectedItem = root;
Dispatcher.UIThread.RunJobs();
Click(window, "+ Model");
root = ((IEnumerable<HierarchyRow>)tree.ItemsSource!).Single();
tree.SelectedItem = root.Children.Single();
Dispatcher.UIThread.RunJobs();
Require(window.GetLogicalDescendants().OfType<TabItem>().All(tab => tab.Header?.ToString()?.Contains("JSON", StringComparison.OrdinalIgnoreCase) != true), "The production layout must not include JSON tabs.");
var jsonEditor = window.FindControl<TextBox>("SourceKv3")!;
var node = JsonNode.Parse(window.DocumentJson)!;
node["m_Children"]![0]!["m_Children"]![0]!["m_sLabel"] = "Test model";
jsonEditor.Text = CoreApi.SerializeSmartPropDocument(node.ToJsonString());
Dispatcher.UIThread.RunJobs();
Require(!window.FindControl<StackPanel>("Fields")!.IsEnabled, "Unapplied element edits must protect other drafts.");
Click(window, "Apply source");
Require(window.DocumentJson.Contains("Test model", StringComparison.Ordinal), "Applying source must update the model.");
Click(window, "Undo");
Require(!window.DocumentJson.Contains("Test model", StringComparison.Ordinal), "Undo must restore the original label.");
Click(window, "Redo");
Require(window.DocumentJson.Contains("Test model", StringComparison.Ordinal), "Redo must restore the edit.");
var before = window.DocumentJson;
jsonEditor.Text = "not json";
Dispatcher.UIThread.RunJobs();
Click(window, "Apply source");
Require(window.DocumentJson == before, "Invalid input must not mutate the document.");
jsonEditor.Text = CoreApi.SerializeSmartPropDocument(before);
Dispatcher.UIThread.RunJobs();
Click(window, "Apply source");
Require(window.FindControl<StackPanel>("Fields")!.IsEnabled, "Applying an edit must unlock other panels.");

var viewport = window.FindControl<SmartPropViewport>("Viewport")!;
var modelInput = window.FindControl<StackPanel>("Fields")!.GetLogicalDescendants().OfType<TextBox>().Single(input => input.Tag?.ToString() == "m_sModelName");
modelInput.Text = "models/test.vmdl";
Click(window, "Apply fields");
Require(window.DocumentJson.Contains("models/test.vmdl", StringComparison.Ordinal), "Field editing must update the document even before deferred change notifications.");
Click(window, "Evaluate");
var status = window.FindControl<TextBlock>("Status")!;
var timeout = System.Diagnostics.Stopwatch.StartNew();
while (window.IsEvaluating && timeout.Elapsed < TimeSpan.FromSeconds(10))
{
    Thread.Sleep(10);
    Dispatcher.UIThread.RunJobs();
}
Require(status.Text?.Contains("1 placements", StringComparison.Ordinal) == true, "Core evaluation must return a placement to the viewport.");
Click(window, "Evaluate");
timeout.Restart();
while (window.IsEvaluating && timeout.Elapsed < TimeSpan.FromSeconds(10))
{
    Thread.Sleep(10);
    Dispatcher.UIThread.RunJobs();
}
Require(status.Text?.Contains("1 placements", StringComparison.Ordinal) == true, "Repeated evaluation must not reuse a disposed cancellation source.");
viewport.SetScene([new(1, "test.vmdl", Matrix4x4.Identity, new float[] { -16, 0, 0, 16, 0, 0, 0, 0, 32 }, new uint[] { 0, 1, 2 })]);
Dispatcher.UIThread.RunJobs();
var example = new MainWindow(false);
example.Show();
Dispatcher.UIThread.RunJobs();
Click(example, "Example");
timeout.Restart();
while (example.IsEvaluating && timeout.Elapsed < TimeSpan.FromSeconds(10))
{
    Thread.Sleep(10);
    Dispatcher.UIThread.RunJobs();
}
Require(example.FindControl<TextBlock>("Status")!.Text?.Contains("3 placements", StringComparison.Ordinal) == true, "The bundled example must evaluate through Core.");
var exampleTree = example.FindControl<TreeView>("Hierarchy")!;
var exampleRoot = ((IEnumerable<HierarchyRow>)exampleTree.ItemsSource!).Single();
exampleTree.SelectedItem = exampleRoot.Children[0];
Dispatcher.UIThread.RunJobs();
var translate = example.FindControl<StackPanel>("Components")!.Children.OfType<Button>().Single(button => button.Content?.ToString()?.Contains("Translate", StringComparison.Ordinal) == true);
translate.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
Dispatcher.UIThread.RunJobs();
var positionX = example.FindControl<StackPanel>("Fields")!.GetLogicalDescendants().OfType<TextBox>().Single(input => input.Tag?.ToString() == "m_vPosition/m_Components/0");
positionX.Text = "-128";
Click(example, "Apply fields");
var editedExample = JsonNode.Parse(example.DocumentJson)!;
Require(editedExample["m_Children"]![0]!["m_Children"]![0]!["m_Modifiers"]![0]!["m_vPosition"]!["m_Components"]![0]!.GetValue<double>() == -128, "Component selection must edit the selected modifier through typed fields.");
Require(editedExample["m_Children"]![0]!["m_Children"]![0]!["m_nElementID"]!.GetValue<int>() == 1, "Modifier edits must preserve the parent element identity.");
Click(example, "Undo");
var filter = example.FindControl<TextBox>("HierarchyFilter")!;
filter.Text = "Right";
Dispatcher.UIThread.RunJobs();
Require(((IEnumerable<HierarchyRow>)exampleTree.ItemsSource!).Single().Children.Single().Label == "Right barrel", "Hierarchy filtering must preserve ancestors and hide unmatched leaves.");
filter.Text = "";
Dispatcher.UIThread.RunJobs();
example.FindControl<NumericUpDown>("ContentVersion")!.Value = 2;
Dispatcher.UIThread.RunJobs();
Require(JsonNode.Parse(example.DocumentJson)!["m_nContentVersion"]!.GetValue<int>() == 2, "Content version must be editable when the source omitted it.");
Click(example, "Undo");
exampleRoot = ((IEnumerable<HierarchyRow>)exampleTree.ItemsSource!).Single();
exampleTree.SelectedItem = exampleRoot.Children[1];
Dispatcher.UIThread.RunJobs();
var variableInput = example.FindControl<StackPanel>("VariableFields")!.GetLogicalDescendants().OfType<TextBox>().Single();
variableInput.Text = "128";
Click(example, "Apply variables");
Require(JsonNode.Parse(example.DocumentJson)!["m_Variables"]![0]!["m_DefaultValue"]!.GetValue<double>() == 128, "Structured variable editing must preserve numeric values.");
Click(example, "Undo");
Require(JsonNode.Parse(example.DocumentJson)!["m_Variables"]![0]!["m_DefaultValue"]!.GetValue<double>() == 96, "Undo must restore a structured variable edit.");
Click(example, "Evaluate");
timeout.Restart();
while (example.IsEvaluating && timeout.Elapsed < TimeSpan.FromSeconds(10))
{
    Thread.Sleep(10);
    Dispatcher.UIThread.RunJobs();
}
Require(example.FindControl<TextBlock>("Status")!.Text?.Contains("3 placements", StringComparison.Ordinal) == true, "Evaluation after undo must restore the scene.");
if (args.Length > 0)
{
    using var frame = example.CaptureRenderedFrame() ?? throw new InvalidOperationException("No rendered frame.");
    var imagePath = Path.GetFullPath(args[0]);
    Directory.CreateDirectory(Path.GetDirectoryName(imagePath)!);
    frame.Save(imagePath, global::Avalonia.Media.Imaging.PngBitmapEncoderOptions.Default);
}
var hierarchy = example.FindControl<SmartPropHierarchy>("Hierarchy")!;
static HierarchyLabel LabelFor(Window window, string id) => window.GetVisualDescendants().OfType<HierarchyLabel>().Single(label => (label.DataContext as HierarchyRow)?.ElementId == id);
static void SelectLabel(Window window, string id, RawInputModifiers modifiers = RawInputModifiers.None)
{
    var label = LabelFor(window, id);
    var point = label.TranslatePoint(new Point(24, 10), window)!.Value;
    window.MouseDown(point, MouseButton.Left, modifiers);
    window.MouseUp(point, MouseButton.Left, modifiers);
    Dispatcher.UIThread.RunJobs();
}
SelectLabel(example, "1");
SelectLabel(example, "3", RawInputModifiers.Control);
Require(hierarchy.SelectedItems!.Count == 2, "Ctrl-click must retain multiple selected hierarchy rows.");
SelectLabel(example, "1");
SelectLabel(example, "3", RawInputModifiers.Shift);
Require(hierarchy.SelectedItems!.Count == 3, "Shift-click must select the visible range.");
var oldHierarchyDocument = example.DocumentJson;
_ = example.HierarchyAction("duplicate");
Dispatcher.UIThread.RunJobs();
Require(JsonNode.Parse(example.DocumentJson)!["m_Children"]![0]!["m_Children"]!.AsArray().Count == 6, "Duplicate must apply to every selected subtree in one edit.");
Click(example, "Undo");
Require(example.DocumentJson == oldHierarchyDocument && hierarchy.SelectedItems!.Count == 3, "Undo must restore the hierarchy document and its selection.");

SelectLabel(example, "1");
var data = hierarchy.CreateDragData();
var leafLabel = LabelFor(example, "2");
var denied = new DragEventArgs(DragDrop.DragOverEvent, data, leafLabel, new Point(20, 11), KeyModifiers.None);
leafLabel.RaiseEvent(denied);
Require(denied.DragEffects == DragDropEffects.None, "Dropping inside a Model must be rejected by the widget.");
var dropLabel = LabelFor(example, "3");
var allowed = new DragEventArgs(DragDrop.DragOverEvent, data, dropLabel, new Point(20, 21), KeyModifiers.None);
dropLabel.RaiseEvent(allowed);
Require(allowed.DragEffects == DragDropEffects.Move, "The lower edge of a leaf must accept a sibling move.");
dropLabel.RaiseEvent(new DragEventArgs(DragDrop.DropEvent, data, dropLabel, new Point(20, 21), KeyModifiers.None));
Dispatcher.UIThread.RunJobs();
Require(JsonNode.Parse(example.DocumentJson)!["m_Children"]![0]!["m_Children"]![2]!["m_nElementID"]!.GetValue<int>() == 1, "A routed drop must reorder the document through Core.");
Click(example, "Undo");
SelectLabel(example, "2");
hierarchy.BeginRename();
var renameInput = LabelFor(example, "2").GetVisualDescendants().OfType<TextBox>().Single();
renameInput.Text = "Renamed barrel";
renameInput.RaiseEvent(new KeyEventArgs { RoutedEvent = InputElement.KeyDownEvent, Key = Key.Enter });
Dispatcher.UIThread.RunJobs();
Require(example.DocumentJson.Contains("Renamed barrel", StringComparison.Ordinal), "Inline rename must commit through Core.");
Click(example, "Undo");
Console.WriteLine("Avalonia interaction, hierarchy selection, routed drop, rename and rendering checks passed.");

public sealed class IntegratedGpuApp : Hammer5Tools.App.App
{
    public override void OnFrameworkInitializationCompleted()
    {
        base.OnFrameworkInitializationCompleted();
        var builder = Host.CreateApplicationBuilder();
        builder.Services.AddHammer5ToolsCore();
        builder.Services.AddSingleton<Hammer5Tools.App.Services.IDialogService, Hammer5Tools.App.Services.DialogService>();
        builder.Services.AddSingleton<Hammer5Tools.App.Features.Shell.ShellViewModel>();
        var host = builder.Build();
        var shell = host.Services.GetRequiredService<Hammer5Tools.App.Features.Shell.ShellViewModel>();
        shell.OpenSmartPropEditor();
        var window = new Hammer5Tools.App.MainWindow(shell);
        window.Closed += (_, _) => host.Dispose();
        ((IClassicDesktopStyleApplicationLifetime)ApplicationLifetime!).MainWindow = window;
    }
}
