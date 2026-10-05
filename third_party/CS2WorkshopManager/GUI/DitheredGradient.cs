using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;
using Avalonia.Platform;
using Avalonia.Rendering.SceneGraph;
using Avalonia.Skia;
using SkiaSharp;

namespace GUI;

/// <summary>
/// A radial gradient from <see cref="CenterColor"/> to <see cref="EdgeColor"/>, drawn through Skia with dithering,
/// which Avalonia's own gradient brushes can not ask for and which keeps a subtle gradient from banding.
/// </summary>
public sealed class DitheredGradient : Control
{
    public static readonly StyledProperty<Color> CenterColorProperty = AvaloniaProperty.Register<DitheredGradient, Color>(nameof(CenterColor));
    public static readonly StyledProperty<Color> EdgeColorProperty = AvaloniaProperty.Register<DitheredGradient, Color>(nameof(EdgeColor));

    /// <summary>How far the gradient reaches from the center, as a fraction of the control's size.</summary>
    public static readonly StyledProperty<double> RadiusProperty = AvaloniaProperty.Register<DitheredGradient, double>(nameof(Radius), 0.75);

    /// <summary>Where <see cref="CenterColor"/> starts from, which may be off center like a gradient brush's origin.</summary>
    public static readonly StyledProperty<RelativePoint> GradientOriginProperty = AvaloniaProperty.Register<DitheredGradient, RelativePoint>(nameof(GradientOrigin), RelativePoint.Center);

    static DitheredGradient()
    {
        AffectsRender<DitheredGradient>(CenterColorProperty, EdgeColorProperty, RadiusProperty, GradientOriginProperty);
    }

    public RelativePoint GradientOrigin
    {
        get => GetValue(GradientOriginProperty);
        set => SetValue(GradientOriginProperty, value);
    }

    public Color CenterColor
    {
        get => GetValue(CenterColorProperty);
        set => SetValue(CenterColorProperty, value);
    }

    public Color EdgeColor
    {
        get => GetValue(EdgeColorProperty);
        set => SetValue(EdgeColorProperty, value);
    }

    public double Radius
    {
        get => GetValue(RadiusProperty);
        set => SetValue(RadiusProperty, value);
    }

    [System.Diagnostics.CodeAnalysis.SuppressMessage("Reliability", "CA2000:Dispose objects before losing scope", Justification = "the renderer owns and disposes custom draw operations")]
    public override void Render(DrawingContext context)
    {
        context.Custom(new DrawOperation(new Rect(Bounds.Size), CenterColor, EdgeColor, Radius, GradientOrigin.ToPixels(Bounds.Size)));
    }

    /// <summary>The renderer reuses the last operation when an equal one is submitted, which the record's value equality provides.</summary>
    private sealed record DrawOperation(Rect Bounds, Color CenterColor, Color EdgeColor, double Radius, Point Origin) : ICustomDrawOperation
    {
        public void Dispose()
        {
        }

        public bool HitTest(Point p)
        {
            return false;
        }

        public bool Equals(ICustomDrawOperation? other)
        {
            return Equals(other as DrawOperation);
        }

        public void Render(ImmediateDrawingContext context)
        {
            var skia = context.TryGetFeature<ISkiaSharpApiLeaseFeature>();

            if (skia == null)
            {
                return;
            }

            using var lease = skia.Lease();

            // a unit circle stretched to the control, so the gradient is elliptical like Avalonia's own
            var scaleX = Bounds.Width * Radius;
            var scaleY = Bounds.Height * Radius;
            var matrix = SKMatrix.CreateScale((float)scaleX, (float)scaleY)
                .PostConcat(SKMatrix.CreateTranslation((float)Bounds.Width / 2, (float)Bounds.Height / 2));

            // the origin is a focal point inside the circle, in the same unit space
            var focus = new SKPoint((float)((Origin.X - Bounds.Width / 2) / scaleX), (float)((Origin.Y - Bounds.Height / 2) / scaleY));

            using var shader = SKShader.CreateTwoPointConicalGradient(focus, 0, SKPoint.Empty, 1, [ToSKColor(CenterColor), ToSKColor(EdgeColor)], null, SKShaderTileMode.Clamp, matrix);
            using var paint = new SKPaint { Shader = shader, IsDither = true };

            lease.SkCanvas.DrawRect(SKRect.Create((float)Bounds.Width, (float)Bounds.Height), paint);
        }

        private static SKColor ToSKColor(Color color)
        {
            return new SKColor(color.R, color.G, color.B, color.A);
        }
    }
}
