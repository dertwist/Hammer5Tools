using System.Numerics;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Media;
using Hammer5Tools.Core.Format.Resources;

namespace Hammer5Tools.App.Features.SmartProps;

public sealed record ViewportInstance(int ElementId, string ModelName, Matrix4x4 Transform, IReadOnlyList<float> Vertices, IReadOnlyList<uint> Indices, CompiledModel? Geometry = null, Vector4? Tint = null);

public sealed class SmartPropViewport : Control
{
    private readonly record struct Edge(Vector3 Start, Vector3 End, int ElementId, bool Marker);
    private readonly List<Edge> edges = [];
    private Vector3 center;
    private float scale = 2;
    private float yaw = -0.65f;
    private float pitch = 0.65f;
    private Point? drag;
    private int? selectedElementId;
    private int placementCount;
    private bool sampled;
    private static Pen GridPen => new(Brush("H5TBorderBrush"), 1);
    private static readonly Pen MeshPen = new(global::Avalonia.Media.Brush.Parse("#95B9DF"), 1);
    private static Pen MarkerPen => new(Brush("H5TTextMutedBrush"), 1);
    private static readonly Pen SelectedPen = new(global::Avalonia.Media.Brush.Parse("#E5A00D"), 1.5);
    private static readonly Pen AxisXPen = new(global::Avalonia.Media.Brush.Parse("#CD5C5C"), 2);
    private static readonly Pen AxisYPen = new(global::Avalonia.Media.Brush.Parse("#90EE90"), 2);
    private static readonly Pen AxisZPen = new(global::Avalonia.Media.Brush.Parse("#87CEFA"), 2);

    private static IBrush Brush(string key) => (IBrush)Application.Current!.Resources[key]!;

    public int? SelectedElementId
    {
        get => selectedElementId;
        set
        {
            selectedElementId = value;
            InvalidateVisual();
        }
    }

    public void ClearScene()
    {
        edges.Clear();
        placementCount = 0;
        sampled = false;
        InvalidateVisual();
    }

    public void SetScene(IReadOnlyList<ViewportInstance> instances, bool frame = true)
    {
        edges.Clear();
        placementCount = instances.Count;
        sampled = false;
        var trianglesPerInstance = Math.Clamp(10_000 / Math.Max(instances.Count, 1), 1, 300);
        foreach (var instance in instances)
        {
            if (instance.Vertices.Count == 0)
            {
                AddMarker(instance);
                continue;
            }
            // ponytail: CPU wireframe has a 10,000 triangle scene budget; use GPU drawing for full-density meshes.
            var stride = Math.Max(1, (instance.Indices.Count / 3 + trianglesPerInstance - 1) / trianglesPerInstance);
            sampled |= stride > 1;
            for (var index = 0; index + 2 < instance.Indices.Count; index += stride * 3)
            {
                var a = Vertex(instance, instance.Indices[index]);
                var b = Vertex(instance, instance.Indices[index + 1]);
                var c = Vertex(instance, instance.Indices[index + 2]);
                edges.Add(new(a, b, instance.ElementId, false));
                edges.Add(new(b, c, instance.ElementId, false));
                edges.Add(new(c, a, instance.ElementId, false));
            }
        }
        if (frame)
        {
            FrameScene();
        }
        InvalidateVisual();
    }

    private static Vector3 Vertex(ViewportInstance instance, uint index)
    {
        var offset = checked((int)index * 3);
        return Vector3.Transform(new(instance.Vertices[offset], instance.Vertices[offset + 1], instance.Vertices[offset + 2]), instance.Transform);
    }

    private void AddMarker(ViewportInstance instance)
    {
        Vector3[] corners =
        [
            new(-8, -8, -8), new(8, -8, -8), new(8, 8, -8), new(-8, 8, -8),
            new(-8, -8, 8), new(8, -8, 8), new(8, 8, 8), new(-8, 8, 8)
        ];
        (int Start, int End)[] lines = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)];
        foreach (var (start, end) in lines)
        {
            edges.Add(new(Vector3.Transform(corners[start], instance.Transform), Vector3.Transform(corners[end], instance.Transform), instance.ElementId, true));
        }
    }

    public void FrameScene()
    {
        if (edges.Count > 0)
        {
            var minimum = new Vector3(float.PositiveInfinity);
            var maximum = new Vector3(float.NegativeInfinity);
            foreach (var edge in edges)
            {
                minimum = Vector3.Min(minimum, Vector3.Min(edge.Start, edge.End));
                maximum = Vector3.Max(maximum, Vector3.Max(edge.Start, edge.End));
            }
            center = (minimum + maximum) / 2;
            scale = (float)(Math.Min(Math.Max(Bounds.Width, 300), Math.Max(Bounds.Height, 300)) * 0.7 / Math.Max((maximum - minimum).Length(), 32));
        }
        else
        {
            center = Vector3.Zero;
            scale = 2;
        }
        InvalidateVisual();
    }

    private Point Project(Vector3 value)
    {
        value -= center;
        var x = value.X * MathF.Cos(yaw) - value.Y * MathF.Sin(yaw);
        var y = value.X * MathF.Sin(yaw) + value.Y * MathF.Cos(yaw);
        var vertical = value.Z * MathF.Cos(pitch) - y * MathF.Sin(pitch);
        return new(Bounds.Width / 2 + x * scale, Bounds.Height / 2 - vertical * scale);
    }

    public override void Render(DrawingContext context)
    {
        base.Render(context);
        context.DrawRectangle(Brush("H5TSurfaceBrush"), null, new Rect(Bounds.Size));
        for (var index = -10; index <= 10; index++)
        {
            context.DrawLine(GridPen, Project(new(index * 32, -320, 0)), Project(new(index * 32, 320, 0)));
            context.DrawLine(GridPen, Project(new(-320, index * 32, 0)), Project(new(320, index * 32, 0)));
        }
        context.DrawLine(AxisXPen, Project(Vector3.Zero), Project(new(64, 0, 0)));
        context.DrawLine(AxisYPen, Project(Vector3.Zero), Project(new(0, 64, 0)));
        context.DrawLine(AxisZPen, Project(Vector3.Zero), Project(new(0, 0, 64)));
        foreach (var edge in edges)
        {
            context.DrawLine(edge.ElementId == selectedElementId ? SelectedPen : edge.Marker ? MarkerPen : MeshPen, Project(edge.Start), Project(edge.End));
        }
        var text = placementCount == 0 ? "Open a SmartProp or add elements, then Evaluate."
            : $"{placementCount} placements{(sampled ? " · sampled wireframe" : "")}";
        context.DrawText(new FormattedText(text, CultureInfo(), FlowDirection.LeftToRight, new Typeface("Segoe UI"), 12, Brush("H5TTextBrush")), new Point(12, 12));
    }

    private static System.Globalization.CultureInfo CultureInfo() => System.Globalization.CultureInfo.InvariantCulture;

    protected override void OnPointerPressed(PointerPressedEventArgs e)
    {
        base.OnPointerPressed(e);
        if (e.GetCurrentPoint(this).Properties.IsLeftButtonPressed)
        {
            drag = e.GetPosition(this);
            e.Pointer.Capture(this);
        }
    }

    protected override void OnPointerMoved(PointerEventArgs e)
    {
        base.OnPointerMoved(e);
        if (drag is { } previous)
        {
            var current = e.GetPosition(this);
            yaw += (float)(current.X - previous.X) * 0.01f;
            pitch = Math.Clamp(pitch + (float)(current.Y - previous.Y) * 0.01f, -1.5f, 1.5f);
            drag = current;
            InvalidateVisual();
        }
    }

    protected override void OnPointerReleased(PointerReleasedEventArgs e)
    {
        base.OnPointerReleased(e);
        drag = null;
        e.Pointer.Capture(null);
    }

    protected override void OnPointerWheelChanged(PointerWheelEventArgs e)
    {
        base.OnPointerWheelChanged(e);
        scale = Math.Clamp(scale * MathF.Pow(1.15f, (float)e.Delta.Y), 0.001f, 1000);
        InvalidateVisual();
        e.Handled = true;
    }
}
