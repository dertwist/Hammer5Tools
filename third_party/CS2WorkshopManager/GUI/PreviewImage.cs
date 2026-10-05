using System.IO;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Labs.Gif;
using Avalonia.Media;
using Avalonia.Media.Imaging;

namespace GUI;

/// <summary>
/// Shows a workshop preview image, which plays when it is a gif, from what <see cref="Decode"/> made of the image file.
/// </summary>
public sealed class PreviewImage : Panel
{
    /// <summary>A <see cref="Bitmap"/> or an <see cref="IGifSource"/> from <see cref="Decode"/>.</summary>
    public static readonly StyledProperty<object?> SourceProperty = AvaloniaProperty.Register<PreviewImage, object?>(nameof(Source));

    // pictures shrink to fit but are never blown up past their own size
    private readonly Image image = new() { Stretch = Stretch.Uniform, StretchDirection = StretchDirection.DownOnly };
    private readonly GifImage gif = new() { Stretch = Stretch.Uniform, StretchDirection = StretchDirection.DownOnly, IsVisible = false };

    public PreviewImage()
    {
        // previews are drawn far from their own size in both directions
        RenderOptions.SetBitmapInterpolationMode(image, BitmapInterpolationMode.HighQuality);

        Children.Add(image);
        Children.Add(gif);
    }

    public object? Source
    {
        get => GetValue(SourceProperty);
        set => SetValue(SourceProperty, value);
    }

    /// <summary>
    /// Decodes an image file, scaled down to <paramref name="width"/> unless that is 0. Gifs are kept whole so they can play.
    /// </summary>
    public static object Decode(byte[] file, int width = 0)
    {
        if (file.AsSpan().StartsWith("GIF8"u8))
        {
            // the gif control decodes and plays the stream itself, so it keeps the stream
            return GifStreamSource.FromStream(new MemoryStream(file));
        }

        using var stream = new MemoryStream(file);

        return width > 0 ? Bitmap.DecodeToWidth(stream, width) : new Bitmap(stream);
    }

    protected override void OnPropertyChanged(AvaloniaPropertyChangedEventArgs change)
    {
        base.OnPropertyChanged(change);

        if (change.Property == SourceProperty)
        {
            image.Source = Source as Bitmap;
            gif.Source = Source as IGifSource;
            gif.IsVisible = gif.Source != null;
        }
    }
}
