using System.Globalization;

namespace SourcePorter.Core.Validation;

/// <summary>
/// A size/contents summary of an imported addon, shown at the end of an import. Counts
/// the source assets in the <c>content\</c> tree (what a porter finishes in Hammer) and
/// the size of the compiled <c>game\</c> tree (what ships).
/// </summary>
/// <param name="ContentBytes">Total bytes under the content addon dir.</param>
/// <param name="GameBytes">Total bytes under the game (compiled) addon dir.</param>
/// <param name="Materials">Count of <c>.vmat</c> material sources.</param>
/// <param name="Models">Count of <c>.vmdl</c> model sources.</param>
/// <param name="Maps">Count of <c>.vmap</c> map sources.</param>
/// <param name="Textures">Count of source textures (<c>.tga</c>/<c>.png</c>/<c>.psd</c>).</param>
/// <param name="CompiledFiles">Count of compiled <c>_c</c> files in the game dir.</param>
public sealed record AddonStats(
    long ContentBytes,
    long GameBytes,
    int Materials,
    int Models,
    int Maps,
    int Textures,
    int CompiledFiles)
{
    public long TotalBytes => ContentBytes + GameBytes;

    private static readonly HashSet<string> TextureExtensions =
        new(StringComparer.OrdinalIgnoreCase) { ".tga", ".png", ".psd" };

    /// <summary>Walks the addon's content and game trees and tallies sizes/counts.</summary>
    public static AddonStats Collect(string contentAddonDir, string gameAddonDir)
    {
        long contentBytes = 0, gameBytes = 0;
        int materials = 0, models = 0, maps = 0, textures = 0, compiled = 0;

        foreach (var file in SafeFiles(contentAddonDir))
        {
            contentBytes += SafeLength(file);
            switch (Path.GetExtension(file).ToLowerInvariant())
            {
                case ".vmat": materials++; break;
                case ".vmdl": models++; break;
                case ".vmap": maps++; break;
                default:
                    if (TextureExtensions.Contains(Path.GetExtension(file)))
                        textures++;
                    break;
            }
        }

        foreach (var file in SafeFiles(gameAddonDir))
        {
            gameBytes += SafeLength(file);
            if (file.EndsWith("_c", StringComparison.OrdinalIgnoreCase))
                compiled++;
        }

        return new AddonStats(contentBytes, gameBytes, materials, models, maps, textures, compiled);
    }

    /// <summary>Renders the summary as console lines (one heading + indented rows).</summary>
    public IEnumerable<string> Format()
    {
        yield return "Addon statistics:";
        yield return $"  Size:      {Human(ContentBytes)} content · {Human(GameBytes)} compiled ({Human(TotalBytes)} total)";
        yield return $"  Materials: {Materials} .vmat";
        yield return $"  Models:    {Models} .vmdl";
        yield return $"  Maps:      {Maps} .vmap";
        yield return $"  Textures:  {Textures} source texture(s)";
        yield return $"  Compiled:  {CompiledFiles} _c file(s)";
    }

    private static IEnumerable<string> SafeFiles(string dir)
    {
        if (!Directory.Exists(dir))
            return [];
        try
        {
            return Directory.EnumerateFiles(dir, "*", SearchOption.AllDirectories);
        }
        catch
        {
            return [];
        }
    }

    private static long SafeLength(string file)
    {
        try
        {
            return new FileInfo(file).Length;
        }
        catch
        {
            return 0;
        }
    }

    /// <summary>Human-readable byte size (B/KB/MB/GB, base-1024).</summary>
    public static string Human(long bytes)
    {
        string[] units = ["B", "KB", "MB", "GB", "TB"];
        double size = bytes;
        var unit = 0;
        while (size >= 1024 && unit < units.Length - 1)
        {
            size /= 1024;
            unit++;
        }

        return unit == 0
            ? $"{bytes} B"
            : size.ToString("0.0", CultureInfo.InvariantCulture) + " " + units[unit];
    }
}
