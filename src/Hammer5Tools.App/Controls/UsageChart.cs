namespace Hammer5Tools.App.Controls;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;

/// <summary>Draws the recent measured percentage history without chart-library dependencies.</summary>
public sealed class UsageChart : Control
{
    public static readonly StyledProperty<double[]> ValuesProperty =
        AvaloniaProperty.Register<UsageChart, double[]>(nameof(Values), []);
    public static readonly StyledProperty<IBrush?> StrokeProperty =
        AvaloniaProperty.Register<UsageChart, IBrush?>(nameof(Stroke));

    public double[] Values
    {
        get => GetValue(ValuesProperty);
        set => SetValue(ValuesProperty, value);
    }

    public IBrush? Stroke
    {
        get => GetValue(StrokeProperty);
        set => SetValue(StrokeProperty, value);
    }

    static UsageChart()
    {
        AffectsRender<UsageChart>(ValuesProperty, StrokeProperty);
    }

    public override void Render(DrawingContext context)
    {
        base.Render(context);
        if (Stroke is null || Values.Length < 2) return;
        var area = new StreamGeometry();
        using (var geometry = area.Open())
        {
            geometry.BeginFigure(new Point(0, Bounds.Height), true);
            for (var index = 0; index < Values.Length; index++)
            {
                geometry.LineTo(new Point(index * Bounds.Width / 59, Bounds.Height * (1 - Math.Clamp(Values[index], 0, 100) / 100)));
            }
            geometry.LineTo(new Point((Values.Length - 1) * Bounds.Width / 59, Bounds.Height));
            geometry.EndFigure(true);
        }
        using (context.PushOpacity(0.2))
        {
            context.DrawGeometry(Stroke, null, area);
        }
        var pen = new Pen(Stroke, 2);
        for (var index = 1; index < Values.Length; index++)
        {
            var first = new Point((index - 1) * Bounds.Width / 59, Bounds.Height * (1 - Math.Clamp(Values[index - 1], 0, 100) / 100));
            var second = new Point(index * Bounds.Width / 59, Bounds.Height * (1 - Math.Clamp(Values[index], 0, 100) / 100));
            context.DrawLine(pen, first, second);
        }
    }
}
