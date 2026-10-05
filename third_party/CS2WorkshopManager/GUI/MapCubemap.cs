using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using CS2WorkshopManager;
using SkiaSharp;
using ValvePak;
using ValveResourceFormat;
using ValveResourceFormat.ResourceTypes;
using ValveResourceFormat.Utils;

namespace GUI;

/// <summary>
/// A look at a map from one of its baked cubemaps: the compiled map an addon is about, and a view from inside one of its cubemaps that is not obviously bad.
/// </summary>
public static partial class MapCubemap
{
    /// <summary>
    /// The compiled maps to take a cubemap from for <paramref name="addon"/>, in the order to try them: the first map its addoninfo.txt lists,
    /// from the addon's own maps or the game's, then the addon's maps alphabetically.
    /// </summary>
    public static List<string> FindMaps(WorkshopManager manager, string addon)
    {
        var addonPath = Path.Combine(manager.AddonsRoot, addon);
        var mapsPath = Path.Combine(addonPath, "maps");
        var addonInfoPath = Path.Combine(addonPath, "addoninfo.txt");
        var maps = new List<string>();

        if (File.Exists(addonInfoPath))
        {
            var list = MapsList().Match(File.ReadAllText(addonInfoPath));
            var name = list.Success ? Quoted().Match(list.Groups[1].Value).Groups[1].Value : string.Empty;

            if (name.Length > 0)
            {
                var listed = new[] { Path.Combine(mapsPath, name + ".vpk"), Path.Combine(manager.GamePath, "game", "csgo", "maps", name + ".vpk") }.FirstOrDefault(File.Exists);

                if (listed != null)
                {
                    maps.Add(listed);
                }
            }
        }

        if (Directory.Exists(mapsPath))
        {
            maps.AddRange(Directory.GetFiles(mapsPath, "*.vpk").Order(StringComparer.OrdinalIgnoreCase).Where(map => !maps.Contains(map, StringComparer.OrdinalIgnoreCase)));
        }

        return maps;
    }

    /// <summary>How wide the view from inside the cubemap is, in degrees across the picture.</summary>
    private const double FieldOfView = 100;

    /// <summary>How far below level the camera looks, in degrees, so a view takes in the ground and the buildings more than open sky.</summary>
    private const double Pitch = -5;

    /// <summary>Which mip the faces of the view are taken from, a smaller one so it comes out softened, with a background's blur.</summary>
    private const uint Mip = 1;

    /// <summary>
    /// How much of the cubemap's light the view keeps, applied to the linear values before the sRGB curve like the renderer's exposure,
    /// so a sunlit map darkens with its colours intact instead of clipping to white and greying.
    /// </summary>
    private const float Exposure = 0.25f;

    /// <summary>The mip the faces are taken from to judge a direction, the one the picture is drawn from, so a lamp that glares in the picture glares when judged.</summary>
    private const uint JudgeMip = 2;

    /// <summary>The size a direction's view is drawn at to judge it.</summary>
    private const int JudgeWidth = 64;
    private const int JudgeHeight = 36;

    /// <summary>How many times smaller than the picture the view is drawn before being scaled up, which the blur of <see cref="Mip"/> hides.</summary>
    private const int DrawScale = 4;

    // what makes a view obviously bad, as shown: too dark, too bright, flat like a wall or fog up close, or any of it as bright as a lamp or the sun
    private const float DarkestMean = 0.15f;
    private const float BrightestMean = 0.7f;
    private const float LeastContrast = 0.05f;
    private const float GlareLevel = 0.85f;

    // what counts as sky, as shown: blue-leaning and not dark
    private const float SkyDarkest = 0.12f;
    private const float SkyBlueness = 0.03f;

    /// <summary>The direction each side face looks in, around the vertical axis from the map's x axis, in face order: +X, -X, +Y, -Y.</summary>
    private static readonly double[] SideYaws = [0, Math.PI, Math.PI / 2, 3 * Math.PI / 2];

    /// <summary>One face of a cube as linear colours, row by row, <see cref="Size"/> texels a side.</summary>
    private sealed record Face(int Size, Vector3[] Texels);

    /// <summary>
    /// A view from inside one of the map's cubemaps, see <see cref="PickView"/>, as a picture of <paramref name="width"/> by <paramref name="height"/>.
    /// Null when the map has no cubemaps, or none of them gives a view that is not obviously bad.
    /// </summary>
    public static SKBitmap? View(string mapPath, int width, int height)
    {
        using var package = new Package();
        package.Read(mapPath);

        var entry = (package.Entries ?? []).SelectMany(pair => pair.Value)
            .FirstOrDefault(entry => entry.GetFullPath().Contains("/cubemaps/", StringComparison.OrdinalIgnoreCase) && entry.TypeName.Equals("vtex_c", StringComparison.OrdinalIgnoreCase));

        if (entry == null)
        {
            return null;
        }

        package.ReadEntry(entry, out var data);

        using var resource = new Resource();
        resource.Read(new MemoryStream(data));

        if (resource.DataBlock is not Texture texture || (texture.Flags & VTexFlags.CUBE_TEXTURE) == 0)
        {
            return null;
        }

        if (PickView(texture) is not var (slice, yaw))
        {
            return null;
        }

        // drawn small and scaled up, since the view is blurred anyway
        var drawWidth = Math.Max(width / DrawScale, 1);
        var drawHeight = Math.Max(height / DrawScale, 1);
        var shot = Shoot(LoadFaces(texture, slice, Mip), yaw, drawWidth, drawHeight);

        using var small = new SKBitmap(drawWidth, drawHeight, SKColorType.Bgra8888, SKAlphaType.Opaque);

        for (var index = 0; index < shot.Length; index++)
        {
            small.SetPixel(index % drawWidth, index / drawWidth, new SKColor(ToByte(shot[index].X), ToByte(shot[index].Y), ToByte(shot[index].Z)));
        }

        return small.Resize(new SKImageInfo(width, height, SKColorType.Bgra8888, SKAlphaType.Opaque), new SKSamplingOptions(SKFilterMode.Linear));
    }

    /// <summary>
    /// The cubemap and direction to look in: every cubemap's four level directions, each judged by its view drawn tiny,
    /// the obviously bad ones skipped, and of the rest the one with the most sky along its top, or the first when none shows sky.
    /// Null when every direction is bad.
    /// </summary>
    private static (uint Slice, double Yaw)? PickView(Texture texture)
    {
        var slices = Math.Max((uint)texture.Depth, 1u);
        var best = (Sky: -1f, Slice: 0u, Yaw: 0.0);

        for (var slice = 0u; slice < slices; slice++)
        {
            var faces = LoadFaces(texture, slice, JudgeMip);

            foreach (var yaw in SideYaws)
            {
                var (bad, sky) = Judge(Shoot(faces, yaw, JudgeWidth, JudgeHeight));

                if (!bad && sky > best.Sky)
                {
                    best = (sky, slice, yaw);
                }
            }
        }

        return best.Sky < 0 ? null : (best.Slice, best.Yaw);
    }

    /// <summary>Whether a view drawn tiny is obviously bad, and the share of its top third that is sky.</summary>
    private static (bool Bad, float Sky) Judge(Vector3[] shot)
    {
        float sum = 0, squares = 0, brightest = 0;
        var sky = 0;

        for (var index = 0; index < shot.Length; index++)
        {
            var light = Luminance(shot[index]);

            sum += light;
            squares += light * light;
            brightest = MathF.Max(brightest, light);

            if (index < shot.Length / 3 && light >= SkyDarkest && shot[index].Z - shot[index].X >= SkyBlueness)
            {
                sky++;
            }
        }

        var mean = sum / shot.Length;
        var contrast = MathF.Sqrt(MathF.Max(0, squares / shot.Length - mean * mean));
        var bad = mean < DarkestMean || mean > BrightestMean || contrast < LeastContrast || brightest > GlareLevel;

        return (bad, sky / (shot.Length / 3f));
    }

    /// <summary>Linear light as shown: darkened by <see cref="Exposure"/> and only then brought to sRGB, as Source 2 Viewer shows HDR.</summary>
    private static Vector3 Show(Vector3 light)
    {
        return ColorSpace.SrgbLinearToGamma(Vector3.Clamp(light * Exposure, Vector3.Zero, Vector3.One));
    }

    /// <summary>The brightness of a colour, from its channels as the eye weighs them.</summary>
    private static float Luminance(Vector3 colour)
    {
        return 0.2126f * colour.X + 0.7152f * colour.Y + 0.0722f * colour.Z;
    }

    /// <summary>The six faces of one of the texture's cubemaps at a mip, as linear colours.</summary>
    private static Face[] LoadFaces(Texture texture, uint slice, uint mip)
    {
        return [.. Enumerable.Range(0, 6).Select(face => LoadFace(texture, slice, face, mip))];
    }

    /// <summary>One face of one of the texture's cubemaps at a mip, or its smallest when it has fewer, as linear colours.</summary>
    private static Face LoadFace(Texture texture, uint slice, int face, uint mip)
    {
        using var bitmap = texture.GenerateBitmap(slice, (Texture.CubemapFace)face, Math.Min(mip, (uint)texture.NumMipLevels - 1));

        var size = bitmap.Width;
        var texels = new Vector3[size * size];

        if (bitmap.ColorType == SKColorType.RgbaF32)
        {
            // HDR faces decode to linear floats
            var channels = MemoryMarshal.Cast<byte, float>(bitmap.GetPixelSpan());

            for (var index = 0; index < texels.Length; index++)
            {
                texels[index] = new Vector3(channels[index * 4], channels[index * 4 + 1], channels[index * 4 + 2]);
            }
        }
        else
        {
            for (var index = 0; index < texels.Length; index++)
            {
                var colour = bitmap.GetPixel(index % size, index / size);
                texels[index] = ColorSpace.SrgbGammaToLinear(new Vector3(colour.Red, colour.Green, colour.Blue) / 255);
            }
        }

        return new Face(size, texels);
    }

    /// <summary>
    /// What a camera of <see cref="FieldOfView"/> at the cube's centre sees, turned <paramref name="yaw"/> around the vertical axis from the map's x axis and tilted by <see cref="Pitch"/>,
    /// as colours from 0 to 1, row by row.
    /// </summary>
    private static Vector3[] Shoot(Face[] faces, double yaw, int width, int height)
    {
        var pitch = Pitch * Math.PI / 180;
        var forward = new Vector3((float)(Math.Cos(pitch) * Math.Cos(yaw)), (float)(Math.Cos(pitch) * Math.Sin(yaw)), (float)Math.Sin(pitch));
        var left = new Vector3((float)-Math.Sin(yaw), (float)Math.Cos(yaw), 0);
        var up = new Vector3((float)(-Math.Sin(pitch) * Math.Cos(yaw)), (float)(-Math.Sin(pitch) * Math.Sin(yaw)), (float)Math.Cos(pitch));

        var halfWidth = (float)Math.Tan(FieldOfView * Math.PI / 360);
        var halfHeight = halfWidth * height / width;
        var shot = new Vector3[width * height];

        for (var y = 0; y < height; y++)
        {
            var upAmount = halfHeight * (1 - 2 * (y + 0.5f) / height);

            for (var x = 0; x < width; x++)
            {
                var leftAmount = halfWidth * (1 - 2 * (x + 0.5f) / width);

                shot[y * width + x] = Show(Sample(faces, forward + left * leftAmount + up * upAmount));
            }
        }

        return shot;
    }

    /// <summary>A colour channel from 0 to 1 as a byte, anything brighter than white clamped to it.</summary>
    private static byte ToByte(float channel)
    {
        return (byte)Math.Round(Math.Clamp(channel, 0, 1) * 255);
    }

    /// <summary>
    /// The cube's light in a direction, with z up, from the face the direction points at most, the way a graphics card samples a cube,
    /// between the four texels around the spot so the small faces read smoothly at the picture's size.
    /// </summary>
    private static Vector3 Sample(Face[] faces, Vector3 direction)
    {
        var (absX, absY, absZ) = (MathF.Abs(direction.X), MathF.Abs(direction.Y), MathF.Abs(direction.Z));
        int face;
        float u, v, major;

        if (absX >= absY && absX >= absZ)
        {
            (major, face, u, v) = direction.X > 0 ? (absX, 0, -direction.Z, -direction.Y) : (absX, 1, direction.Z, -direction.Y);
        }
        else if (absY >= absZ)
        {
            (major, face, u, v) = direction.Y > 0 ? (absY, 2, direction.X, direction.Z) : (absY, 3, direction.X, -direction.Z);
        }
        else
        {
            (major, face, u, v) = direction.Z > 0 ? (absZ, 4, direction.X, -direction.Y) : (absZ, 5, -direction.X, -direction.Y);
        }

        var (size, texels) = faces[face];
        var column = Math.Clamp((u / major + 1) / 2 * size - 0.5f, 0, size - 1);
        var row = Math.Clamp((v / major + 1) / 2 * size - 0.5f, 0, size - 1);
        var leftTexel = (int)column;
        var top = (int)row;
        var right = Math.Min(leftTexel + 1, size - 1);
        var bottom = Math.Min(top + 1, size - 1);
        var across = column - leftTexel;
        var down = row - top;

        return Vector3.Lerp(
            Vector3.Lerp(texels[top * size + leftTexel], texels[top * size + right], across),
            Vector3.Lerp(texels[bottom * size + leftTexel], texels[bottom * size + right], across),
            down);
    }

    [GeneratedRegex(@"maps\s*=\s*\[([^\]]*)\]")]
    private static partial Regex MapsList();

    [GeneratedRegex("\"([^\"]+)\"")]
    private static partial Regex Quoted();
}
