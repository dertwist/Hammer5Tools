using System.Globalization;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Documents;
using Avalonia.Input;
using Avalonia.Media;
using Avalonia.Media.Immutable;
using CS2WorkshopManager;

namespace GUI;

/// <summary>
/// The workshop manager's bar of the asset types an addon upload is made of, drawn the way it draws it: one span per asset type across the top half,
/// smallest first, as wide as its share of the total size, and the totals or the asset type under the pointer written underneath.
/// </summary>
public sealed class ContentsBar : Control
{
    public static readonly StyledProperty<AddonContents?> ContentsProperty = AvaloniaProperty.Register<ContentsBar, AddonContents?>(nameof(Contents));

    public static readonly StyledProperty<IBrush?> ForegroundProperty = TextElement.ForegroundProperty.AddOwner<ContentsBar>();

    private const double MinSpanWidth = 10;
    private const double LabelFontSize = 12;

    // the workshop manager's hues, from orange for the biggest asset type to purple for the smallest, and its HSV saturation and value out of 255
    private const double FirstHue = 30;
    private const double HueRange = 240;
    private const double Saturation = 120 / 255.0;
    private const double Value = 200 / 255.0;

    /// <summary>How much the workshop manager lightens the span under the pointer and darkens the others, as Qt's percentage.</summary>
    private const double HoverFactor = 125;

    private static readonly Color WarningColor = Color.FromRgb(255, 40, 40);

    private Point? pointer;

    static ContentsBar()
    {
        AffectsRender<ContentsBar>(ContentsProperty, ForegroundProperty);
    }

    public AddonContents? Contents
    {
        get => GetValue(ContentsProperty);
        set => SetValue(ContentsProperty, value);
    }

    public IBrush? Foreground
    {
        get => GetValue(ForegroundProperty);
        set => SetValue(ForegroundProperty, value);
    }

    public override void Render(DrawingContext context)
    {
        var contents = Contents;
        var bounds = new Rect(Bounds.Size);

        if (contents == null || bounds.Width <= 0 || bounds.Height <= 0)
        {
            return;
        }

        var spans = LayoutSpans(contents, bounds);
        var hovered = pointer is Point point ? spans.Find(span => span.Rect.Contains(point)) : null;

        foreach (var span in spans)
        {
            var color = hovered == null ? span.Color : span == hovered ? Contrast.Lighter(span.Color, HoverFactor) : Contrast.Darker(span.Color, HoverFactor);

            context.FillRectangle(new ImmutableSolidColorBrush(color), span.Rect);
        }

        // the bottom half says what the bar shows, or what the span under the pointer is, in the span's colour or the warning's pushed to where it reads on the window
        var textArea = new Rect(0, Math.Floor(bounds.Height / 2), bounds.Width, 2 * Math.Floor(bounds.Height / 2) - 1);
        var background = this.TryFindResource("AppColor", ActualThemeVariant, out var found) && found is Color window ? window : Colors.Black;
        string text;
        IBrush? brush;

        if (hovered != null)
        {
            text = contents.Describe(hovered.AssetType);
            brush = new ImmutableSolidColorBrush(Contrast.Readable(Contrast.Lighter(hovered.Color, HoverFactor), background));
        }
        else if (contents.ExceedsUploadLimit)
        {
            text = $"{contents.Summary} WARNING: Exceeds {AddonContents.FormatSize(AddonPackager.MaxTotalSize)} upload limit!";
            brush = new ImmutableSolidColorBrush(Contrast.Readable(WarningColor, background));
        }
        else
        {
            text = contents.Summary;
            brush = Foreground;
        }

        var label = new FormattedText(text, CultureInfo.InvariantCulture, FlowDirection.LeftToRight, Typeface.Default, LabelFontSize, brush);

        context.DrawText(label, new Point(textArea.X, textArea.Y + (textArea.Height - label.Height) / 2));
    }

    protected override void OnPointerMoved(PointerEventArgs e)
    {
        base.OnPointerMoved(e);

        pointer = e.GetPosition(this);
        InvalidateVisual();
    }

    protected override void OnPointerExited(PointerEventArgs e)
    {
        base.OnPointerExited(e);

        pointer = null;
        InvalidateVisual();
    }

    /// <summary>
    /// Lays the asset types out from the last, the smallest, to the first, each at least a sliver wide, until the width is used up.
    /// </summary>
    private static List<Span> LayoutSpans(AddonContents contents, Rect bounds)
    {
        var spans = new List<Span>();
        var assetTypes = contents.AssetTypes;
        var height = Math.Floor(bounds.Height / 2) - 1;
        var remaining = bounds.Width;
        var x = 0.0;

        for (var index = assetTypes.Count - 1; index >= 0 && remaining > 0; index--)
        {
            var assetType = assetTypes[index];
            var width = Math.Min(remaining, Math.Max(MinSpanWidth, Math.Floor(bounds.Width * contents.Share(assetType))));
            var hue = FirstHue + HueRange * (assetTypes.Count > 1 ? (double)index / (assetTypes.Count - 1) : 0);

            spans.Add(new Span(assetType, new Rect(x, 0, width, height), HsvColor.ToRgb(hue, Saturation, Value)));

            x += width;
            remaining -= width;
        }

        return spans;
    }

    private sealed record Span(AddonContents.AssetType AssetType, Rect Rect, Color Color);
}
