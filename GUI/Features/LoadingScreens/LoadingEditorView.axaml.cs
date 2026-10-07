namespace Hammer5Tools.App.Features.LoadingScreens;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Media;
using Avalonia.Platform.Storage;

public partial class LoadingEditorView : UserControl
{
    public LoadingEditorView()
    {
        InitializeComponent();
        PreviewViewport.PointerWheelChanged += (_, e) =>
        {
            if (DataContext is not LoadingEditorViewModel { ImagePreview: not null }) return;
            ZoomAt(e.GetPosition(PreviewViewport), e.Delta.Y > 0 ? 1.2 : 1 / 1.2);
            e.Handled = true;
        };
        PreviewViewport.PointerPressed += (_, e) =>
        {
            if (e.ClickCount == 2 && e.GetCurrentPoint(PreviewViewport).Properties.IsLeftButtonPressed)
            {
                ResetViewport();
                e.Handled = true;
                return;
            }
            if (!e.GetCurrentPoint(PreviewViewport).Properties.IsRightButtonPressed) return;
            PanStart = e.GetPosition(PreviewViewport);
            e.Pointer.Capture(PreviewViewport);
            PreviewViewport.Cursor = new Cursor(StandardCursorType.SizeAll);
            e.Handled = true;
        };
        PreviewViewport.PointerMoved += (_, e) =>
        {
            if (PanStart is not { } start) return;
            var position = e.GetPosition(PreviewViewport);
            Pan += position - start;
            PanStart = position;
            UpdateViewportTransform();
            e.Handled = true;
        };
        PreviewViewport.PointerReleased += (_, e) =>
        {
            if (PanStart is null) return;
            e.Pointer.Capture(null);
            EndPan();
            e.Handled = true;
        };
        PreviewViewport.PointerCaptureLost += (_, _) => EndPan();
        IconDropArea.DoubleTapped += (_, _) => (DataContext as LoadingEditorViewModel)?.BrowseIconCommand.Execute(null);
        IconDropArea.AddHandler(DragDrop.DragOverEvent, OnDragOver);
        IconDropArea.AddHandler(DragDrop.DropEvent, OnDrop);
        LoadingShotsTree.AddHandler(DragDrop.DragOverEvent, OnScreenshotDragOver);
        LoadingShotsTree.AddHandler(DragDrop.DropEvent, OnScreenshotDrop);
        HistoryTree.AddHandler(DragDrop.DragOverEvent, OnScreenshotDragOver);
        HistoryTree.AddHandler(DragDrop.DropEvent, OnScreenshotDrop);
    }

    internal double ViewportZoom { get; private set; } = 1;
    internal Vector Pan { get; private set; }
    private Point? PanStart;

    internal void ZoomAt(Point position, double factor)
    {
        var zoom = Math.Clamp(ViewportZoom * factor, 0.03, 10);
        var ratio = zoom / ViewportZoom;
        // The scene starts at its layout margin; keep the image under the pointer stationary.
        var anchor = position - PreviewScene.Bounds.Position;
        Pan = new Vector(anchor.X, anchor.Y) - (new Vector(anchor.X, anchor.Y) - Pan) * ratio;
        ViewportZoom = zoom;
        UpdateViewportTransform();
    }

    internal void ResetViewport()
    {
        ViewportZoom = 1;
        Pan = default;
        UpdateViewportTransform();
    }

    private void UpdateViewportTransform() => PreviewScene.RenderTransform = new MatrixTransform(new Matrix(ViewportZoom, 0, 0, ViewportZoom, Pan.X, Pan.Y));

    private void EndPan()
    {
        PanStart = null;
        PreviewViewport.Cursor = Cursor.Default;
    }

    private static void OnDragOver(object? sender, DragEventArgs e)
    {
        e.DragEffects = e.DataTransfer.TryGetFile()?.TryGetLocalPath()?.EndsWith(".svg", StringComparison.OrdinalIgnoreCase) == true
            ? DragDropEffects.Copy : DragDropEffects.None;
    }

    private void OnDrop(object? sender, DragEventArgs e)
    {
        if (e.DataTransfer.TryGetFile()?.TryGetLocalPath() is { } path && DataContext is LoadingEditorViewModel viewModel)
        {
            viewModel.SetDroppedIcon(path);
        }
    }

    private static void OnScreenshotDragOver(object? sender, DragEventArgs e)
    {
        e.DragEffects = e.DataTransfer.Contains(DataFormat.File) ? DragDropEffects.Copy : DragDropEffects.None;
    }

    private async void OnScreenshotDrop(object? sender, DragEventArgs e)
    {
        if (DataContext is not LoadingEditorViewModel viewModel || sender is not Control { Name: var name }) return;
        var paths = e.DataTransfer.TryGetFiles()?.Select(file => file.TryGetLocalPath()).Where(path => path is not null).Cast<string>().ToArray() ?? [];
        await viewModel.ImportDroppedScreenshotsAsync(name == "HistoryTree", paths);
    }
}
