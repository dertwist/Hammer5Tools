using System.IO;
using System.Linq;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;
using Avalonia.Platform;
using Avalonia.Rendering.SceneGraph;
using Avalonia.Skia;
using Avalonia.Styling;
using SkiaSharp;
using Svg.Skia;

namespace GUI;

// icons yoinked from source2 viewer :ujel:
public sealed class SvgIcon : Control
{
    /// <summary>The icon for a folder.</summary>
    public const string Folder = "Folder";

    /// <summary>The icon for a file of no particular kind.</summary>
    public const string File = "File";

    private const string LightSuffix = "_light";

    public static readonly StyledProperty<string?> SourceProperty = AvaloniaProperty.Register<SvgIcon, string?>(nameof(Source));

    private static readonly Uri Root = new("avares://CS2WorkshopManager-GUI/assets/filetypes/");

    /// <summary>The names of every icon, light variants included.</summary>
    private static readonly HashSet<string> Names = AssetLoader.GetAssets(Root, null)
        .Select(uri => uri.AbsolutePath)
        .Where(path => path.EndsWith(".svg", StringComparison.OrdinalIgnoreCase))
        .Select(Path.GetFileNameWithoutExtension)
        .ToHashSet(StringComparer.OrdinalIgnoreCase)!;

    private static readonly Dictionary<string, string> Aliases = LoadAliases();

    private static readonly Dictionary<string, SKSvg> Cache = new(StringComparer.OrdinalIgnoreCase);

    static SvgIcon()
    {
        AffectsRender<SvgIcon>(SourceProperty);
    }

    /// <summary>The name of the icon, as <see cref="ForFile"/> gives it.</summary>
    public string? Source
    {
        get => GetValue(SourceProperty);
        set => SetValue(SourceProperty, value);
    }

    public static string ForFile(string fileName)
    {
        var extension = Path.GetExtension(fileName).TrimStart('.');

        if (extension.EndsWith("_c", StringComparison.OrdinalIgnoreCase))
        {
            extension = extension[..^2];
        }

        if (Known(extension, out var name))
        {
            return name;
        }

        if (extension.StartsWith('v') && Known(extension[1..], out name))
        {
            return name;
        }

        return File;

        static bool Known(string extension, out string name)
        {
            name = Aliases.TryGetValue(extension, out var alias) ? alias : extension;

            return name.Length > 0 && !name.EndsWith(LightSuffix, StringComparison.OrdinalIgnoreCase) && Names.Contains(name);
        }
    }

    protected override void OnPropertyChanged(AvaloniaPropertyChangedEventArgs change)
    {
        base.OnPropertyChanged(change);

        if (change.Property.Name == nameof(ActualThemeVariant))
        {
            InvalidateVisual();
        }
    }

    [System.Diagnostics.CodeAnalysis.SuppressMessage("Reliability", "CA2000:Dispose objects before losing scope", Justification = "the renderer owns and disposes custom draw operations")]
    public override void Render(DrawingContext context)
    {
        if (Source == null)
        {
            return;
        }

        var name = ActualThemeVariant == ThemeVariant.Light && Names.Contains(Source + LightSuffix) ? Source + LightSuffix : Source;

        if (Load(name).Picture is { } picture)
        {
            context.Custom(new DrawOperation(new Rect(Bounds.Size), picture));
        }
    }

    private static SKSvg Load(string name)
    {
        if (!Cache.TryGetValue(name, out var svg))
        {
            svg = new SKSvg();

            using var stream = AssetLoader.Open(new Uri(Root, name + ".svg"));
            svg.Load(stream);

            Cache[name] = svg;
        }

        return svg;
    }

    private static Dictionary<string, string> LoadAliases()
    {
        var aliases = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        using var stream = AssetLoader.Open(new Uri(Root, "aliases.txt"));
        using var reader = new StreamReader(stream);

        // one "alias icon" pair per line
        while (reader.ReadLine() is { } line)
        {
            var parts = line.Split(' ', 2, StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

            if (parts.Length == 2)
            {
                aliases[parts[0]] = parts[1];
            }
        }

        return aliases;
    }

    /// <summary>
    /// Draws the picture with its live area fitted inside the bounds: the icons are drawn on a 24 unit grid whose outer 2 units are kept clear,
    /// so a 16 pixel control shows 16 pixels of icon rather than of grid.
    /// </summary>
    private sealed record DrawOperation(Rect Bounds, SKPicture Picture) : ICustomDrawOperation
    {
        private const float LiveArea = 20f / 24f;

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

            var canvas = lease.SkCanvas;
            var scale = (float)Math.Min(Bounds.Width / Picture.CullRect.Width, Bounds.Height / Picture.CullRect.Height) / LiveArea;

            canvas.Save();
            canvas.Translate((float)(Bounds.Width - Picture.CullRect.Width * scale) / 2, (float)(Bounds.Height - Picture.CullRect.Height * scale) / 2);
            canvas.Scale(scale);
            canvas.DrawPicture(Picture);
            canvas.Restore();
        }
    }
}
