namespace Hammer5Tools.App.Features.SoundEvents;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Media;
using Hammer5Tools.Core.SoundEvents;

internal sealed class SoundCurveGraph : Control
{
    private readonly IReadOnlyList<decimal[]> Values;
    private readonly Action Committed;
    private int DragIndex = -1;
    private int DragSide = -1;
    private readonly List<(int Index, int Side, Point Position)> Handles = [];
    private Rect Plot;
    private double MinX;
    private double MaxX;
    private double MinY;
    private double MaxY;

    public SoundCurveGraph(IReadOnlyList<decimal[]> values, Action committed)
    {
        Values = values;
        Committed = committed;
        Height = 170;
        Focusable = true;
    }

    private static IBrush Brush(string key) => Application.Current?.Resources[key] as IBrush ?? Brushes.Gray;

    public override void Render(DrawingContext context)
    {
        base.Render(context);
        context.FillRectangle(Brush("H5TSurfaceInputBrush"), new Rect(Bounds.Size));
        if (Values.Count == 0) return;
        if (DragIndex < 0)
        {
            MinX = Math.Min(0, Values.Min(point => (double)point[0]));
            MaxX = Math.Max(MinX + 1, Values.Max(point => (double)point[0]));
            MinY = Math.Min(0, Values.Min(point => (double)point[1]));
            MaxY = Math.Max(MinY + 1, Values.Max(point => (double)point[1]));
        }
        Plot = new Rect(28, 10, Math.Max(1, Bounds.Width - 42), Math.Max(1, Bounds.Height - 32));
        var grid = new Pen(Brush("H5TBorderBrush"), 1);
        for (var i = 0; i <= 4; i++)
        {
            var x = Plot.Left + Plot.Width * i / 4;
            var y = Plot.Top + Plot.Height * i / 4;
            context.DrawLine(grid, new Point(x, Plot.Top), new Point(x, Plot.Bottom));
            context.DrawLine(grid, new Point(Plot.Left, y), new Point(Plot.Right, y));
        }
        var prepared = SoundCurve.Prepare(Values.Select(point => new SoundCurvePoint((double)point[0], (double)point[1], (double)point[2], (double)point[3], (int)point[4], (int)point[5])));
        if (prepared.Length > 1)
        {
            var pen = new Pen(Brush("H5TSoundPropertyFloatBrush"), 2);
            using (context.PushClip(Plot))
            {
                var previous = Project(MinX, SoundCurve.Sample(MinX, prepared));
                for (var i = 1; i <= 250; i++)
                {
                    var x = MinX + (MaxX - MinX) * i / 250;
                    var current = Project(x, SoundCurve.Sample(x, prepared));
                    context.DrawLine(pen, previous, current);
                    previous = current;
                }
            }
        }
        Handles.Clear();
        var tangentPen = new Pen(Brush("H5TTextMutedBrush"), 1);
        for (var i = 0; i < Values.Count; i++)
        {
            var point = Values[i];
            var anchor = Project((double)point[0], (double)point[1]);
            var evaluated = prepared.First(item => item.Input == (double)point[0]);
            var length = (MaxX - MinX) / 10;
            var leftHandle = Project((double)point[0] - length, (double)point[1] - evaluated.LeftSlope * length);
            var rightHandle = Project((double)point[0] + length, (double)point[1] + evaluated.RightSlope * length);
            context.DrawLine(tangentPen, leftHandle, rightHandle);
            context.DrawEllipse(Brush("H5TTextMutedBrush"), null, leftHandle, 3, 3);
            context.DrawEllipse(Brush("H5TTextMutedBrush"), null, rightHandle, 3, 3);
            Handles.Add((i, 0, leftHandle));
            Handles.Add((i, 1, rightHandle));
            context.DrawEllipse(Brush("H5TAccentBrush"), null, anchor, 4, 4);
        }
    }

    private Point Project(double x, double y) => new(Plot.Left + (x - MinX) / (MaxX - MinX) * Plot.Width, Plot.Bottom - (y - MinY) / (MaxY - MinY) * Plot.Height);

    protected override void OnPointerPressed(PointerPressedEventArgs e)
    {
        base.OnPointerPressed(e);
        if (!e.GetCurrentPoint(this).Properties.IsLeftButtonPressed) return;
        var position = e.GetPosition(this);
        var nearest = Values.Select((point, index) => (Index: index, Distance: ((Vector)(Project((double)point[0], (double)point[1]) - position)).Length))
            .OrderBy(point => point.Distance).FirstOrDefault((Index: -1, Distance: double.MaxValue));
        DragSide = -1;
        if (nearest.Distance <= 12) DragIndex = nearest.Index;
        else
        {
            var handle = Handles.OrderBy(item => ((Vector)(item.Position - position)).Length).FirstOrDefault();
            if (Handles.Count == 0 || ((Vector)(handle.Position - position)).Length > 10) return;
            DragIndex = handle.Index;
            DragSide = handle.Side;
        }
        e.Pointer.Capture(this);
        e.Handled = true;
    }

    protected override void OnPointerMoved(PointerEventArgs e)
    {
        base.OnPointerMoved(e);
        if (DragIndex < 0) return;
        var position = e.GetPosition(this);
        var point = Values[DragIndex];
        var x = MinX + (position.X - Plot.Left) / Plot.Width * (MaxX - MinX);
        var y = MinY + (Plot.Bottom - position.Y) / Plot.Height * (MaxY - MinY);
        if (DragSide < 0)
        {
            var lower = DragIndex == 0 ? MinX : (double)Values[DragIndex - 1][0] + 0.001;
            var upper = DragIndex == Values.Count - 1 ? MaxX : (double)Values[DragIndex + 1][0] - 0.001;
            point[0] = (decimal)Math.Clamp(x, lower, Math.Max(lower, upper));
            point[1] = (decimal)Math.Clamp(y, MinY, MaxY);
        }
        else
        {
            var side = (int)point[DragSide + 4] == 3 ? 1 - DragSide : DragSide;
            var floor = (MaxX - MinX) / 500;
            var slope = DragSide == 0 ? ((double)point[1] - y) / Math.Max((double)point[0] - x, floor)
                : (y - (double)point[1]) / Math.Max(x - (double)point[0], floor);
            point[side + 2] = (decimal)slope;
            point[side + 4] = 2;
        }
        InvalidateVisual();
    }

    protected override void OnPointerReleased(PointerReleasedEventArgs e)
    {
        base.OnPointerReleased(e);
        if (DragIndex < 0) return;
        DragIndex = -1;
        e.Pointer.Capture(null);
        Committed();
        InvalidateVisual();
    }
}
