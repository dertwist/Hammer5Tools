using System.IO;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Layout;
using Avalonia.Media;
using Avalonia.Media.Imaging;
using Avalonia.Platform;
using Avalonia.Styling;
using SkiaSharp;

namespace GUI;

/// <summary>
/// The thumbnail a new submission starts with: the app's icon and name over a look at the addon's map, or over the gradient the dark theme paints its windows with, drawn to a picture file.
/// </summary>
public static class DefaultThumbnail
{
    public const int Width = 1280;
    public const int Height = 720;

    /// <summary>How much the map behind the icon and name is shaded on top of the darker exposure it is drawn with, so they read over it whatever it shows.</summary>
    private const double MapShade = 0.3;

    /// <summary>Where the picture is written, under the temp folder like the thumbnails the upload converts.</summary>
    public static string FilePath { get; } = Path.Combine(Path.GetTempPath(), "CS2WorkshopManager", "default_thumbnail.png");

    /// <summary>Draws the thumbnail to <see cref="FilePath"/>, over <paramref name="map"/> when there is one, and returns that path.</summary>
    public static string Render(SKBitmap? map)
    {
        var application = Application.Current!;
        var main = ThemeColor(application, "AppColor");
        var contrast = ThemeColor(application, "ContrastColor");
        var accent = App.ThemeAccent(ThemeVariant.Dark);

        var picture = new Panel { Width = Width, Height = Height };

        if (map != null)
        {
            // the look at the map, shaded so the icon and the name read over it
            picture.Children.Add(new Image { Source = ToBitmap(map), Stretch = Stretch.UniformToFill });
            picture.Children.Add(new Border { Background = new SolidColorBrush(Colors.Black, MapShade) });
        }
        else
        {
            // the same gradient as a window's, from the same corner
            picture.Children.Add(new DitheredGradient
            {
                CenterColor = WindowAccent.GradientCenter(main, accent),
                EdgeColor = main,
                GradientOrigin = new RelativePoint(0.9, 0, RelativeUnit.Relative),
            });
        }

        var content = new StackPanel { HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Bottom, Spacing = 24, Margin = new Thickness(0, 0, 0, 48) };

        content.Children.Add(new Image
        {
            Source = new Bitmap(AssetLoader.Open(new Uri("avares://CS2WorkshopManager-GUI/assets/icon.png"))),
            Width = 200,
            Height = 200,
        });

        content.Children.Add(new TextBlock
        {
            Text = "Default Thumbnail",
            FontSize = 64,
            FontWeight = FontWeight.SemiBold,
            Foreground = new SolidColorBrush(contrast),
            HorizontalAlignment = HorizontalAlignment.Center,
        });

        content.Children.Add(new TextBlock
        {
            Text = "CS2 Workshop Manager",
            FontSize = 32,
            Foreground = new SolidColorBrush(contrast),
            HorizontalAlignment = HorizontalAlignment.Center,
            Margin = new Thickness(0, -12, 0, 0),
        });

        picture.Children.Add(content);

        picture.Measure(new Size(Width, Height));
        picture.Arrange(new Rect(0, 0, Width, Height));

        using var bitmap = new RenderTargetBitmap(new PixelSize(Width, Height));
        bitmap.Render(picture);

        Directory.CreateDirectory(Path.GetDirectoryName(FilePath)!);

        using (var stream = File.Create(FilePath))
        {
            bitmap.Save(stream, new PngBitmapEncoderOptions());
        }

        return FilePath;
    }

    /// <summary>A colour of the dark theme by its key.</summary>
    private static Color ThemeColor(Application application, string key)
    {
        return application.TryFindResource(key, ThemeVariant.Dark, out var found) && found is Color color ? color : Colors.Black;
    }

    /// <summary>A Skia bitmap as one Avalonia can draw, by way of a picture in memory.</summary>
    private static Bitmap ToBitmap(SKBitmap bitmap)
    {
        using var stream = new MemoryStream();
        bitmap.Encode(stream, SKEncodedImageFormat.Png, 100);
        stream.Position = 0;

        return new Bitmap(stream);
    }
}
