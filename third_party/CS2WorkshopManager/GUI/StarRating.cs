using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;

namespace GUI;

/// <summary>
/// Five stars filled from the left by a value out of five, a star partly filled for any fraction.
/// </summary>
public sealed class StarRating : Control
{
    public static readonly StyledProperty<double> ValueProperty = AvaloniaProperty.Register<StarRating, double>(nameof(Value));

    public static readonly StyledProperty<IBrush?> FillProperty = AvaloniaProperty.Register<StarRating, IBrush?>(nameof(Fill));

    public static readonly StyledProperty<IBrush?> OutlineProperty = AvaloniaProperty.Register<StarRating, IBrush?>(nameof(Outline));

    public static readonly StyledProperty<double> StarSizeProperty = AvaloniaProperty.Register<StarRating, double>(nameof(StarSize), 14);

    private const int Count = 5;

    /// <summary>The space between stars, in pixels.</summary>
    private const double Gap = 2;

    /// <summary>A five pointed star in a unit square.</summary>
    private static readonly Geometry Star = MakeStar();

    static StarRating()
    {
        AffectsRender<StarRating>(ValueProperty, FillProperty, OutlineProperty, StarSizeProperty);
        AffectsMeasure<StarRating>(StarSizeProperty);
    }

    /// <summary>How many stars are filled, out of five, fractions included.</summary>
    public double Value
    {
        get => GetValue(ValueProperty);
        set => SetValue(ValueProperty, value);
    }

    public IBrush? Fill
    {
        get => GetValue(FillProperty);
        set => SetValue(FillProperty, value);
    }

    /// <summary>What every star is drawn with, whether filled or not.</summary>
    public IBrush? Outline
    {
        get => GetValue(OutlineProperty);
        set => SetValue(OutlineProperty, value);
    }

    public double StarSize
    {
        get => GetValue(StarSizeProperty);
        set => SetValue(StarSizeProperty, value);
    }

    protected override Size MeasureOverride(Size availableSize)
    {
        return new Size(Count * StarSize + (Count - 1) * Gap, StarSize);
    }

    public override void Render(DrawingContext context)
    {
        var size = StarSize;
        var value = Math.Clamp(Value, 0, Count);
        var full = Math.Floor(value);

        // the fill reaches through the full stars and the fraction of the next, then the outlines go over every star
        var width = full * (size + Gap) + (value - full) * size;

        using (context.PushClip(new Rect(0, 0, width, size)))
        {
            DrawStars(context, Fill, null);
        }

        if (Outline != null)
        {
            DrawStars(context, null, new Pen(Outline, 1 / size));
        }
    }

    private void DrawStars(DrawingContext context, IBrush? fill, IPen? pen)
    {
        for (var index = 0; index < Count; index++)
        {
            using (context.PushTransform(Matrix.CreateScale(StarSize, StarSize) * Matrix.CreateTranslation(index * (StarSize + Gap), 0)))
            {
                context.DrawGeometry(fill, pen, Star);
            }
        }
    }

    private static StreamGeometry MakeStar()
    {
        var geometry = new StreamGeometry();

        using var shape = geometry.Open();

        // ten points around the centre, the outer ones on the square's edge and the inner ones at two fifths of that, starting from the top
        for (var point = 0; point < 10; point++)
        {
            var angle = (-90 + point * 36) * Math.PI / 180;
            var radius = point % 2 == 0 ? 0.5 : 0.2;
            var position = new Point(0.5 + radius * Math.Cos(angle), 0.5 + radius * Math.Sin(angle));

            if (point == 0)
            {
                shape.BeginFigure(position, isFilled: true);
            }
            else
            {
                shape.LineTo(position);
            }
        }

        shape.EndFigure(isClosed: true);

        return geometry;
    }
}
