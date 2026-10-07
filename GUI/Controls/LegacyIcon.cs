namespace Hammer5Tools.App.Controls;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Media.Imaging;
using Avalonia.Platform;

/// <summary>Displays the original Python resource artwork, including SVG icons.</summary>
public sealed class LegacyIcon : Image
{
    public static readonly StyledProperty<string> PathProperty = AvaloniaProperty.Register<LegacyIcon, string>(nameof(Path), string.Empty);

    public string Path
    {
        get => GetValue(PathProperty);
        set => SetValue(PathProperty, value);
    }

    public LegacyIcon()
    {
        Width = Height = 16;
    }

    protected override void OnPropertyChanged(AvaloniaPropertyChangedEventArgs change)
    {
        base.OnPropertyChanged(change);
        if (change.Property != PathProperty || string.IsNullOrEmpty(Path)) return;
        var resourcePath = Path.Contains('/', StringComparison.Ordinal) ? Path : $"ui/{Path}";
        using var stream = AssetLoader.Open(new Uri($"avares://Hammer5Tools/Assets/LegacyIcons/{resourcePath}"));
        Bitmap bitmap;
        if (Path.EndsWith(".svg", StringComparison.OrdinalIgnoreCase))
        {
            using var svg = new Svg.Skia.SKSvg();
            var picture = svg.Load(stream)!;
            using var raster = new SkiaSharp.SKBitmap(32, 32);
            using var canvas = new SkiaSharp.SKCanvas(raster);
            canvas.Clear(SkiaSharp.SKColors.Transparent);
            var bounds = picture.CullRect;
            canvas.Scale(32 / Math.Max(bounds.Width, bounds.Height));
            canvas.Translate(-bounds.Left, -bounds.Top);
            canvas.DrawPicture(picture);
            using var data = raster.Encode(SkiaSharp.SKEncodedImageFormat.Png, 100);
            using var png = data.AsStream();
            bitmap = new Bitmap(png);
        }
        else
        {
            bitmap = new Bitmap(stream);
        }
        var previous = Source as Bitmap;
        Source = bitmap;
        previous?.Dispose();
    }
}
