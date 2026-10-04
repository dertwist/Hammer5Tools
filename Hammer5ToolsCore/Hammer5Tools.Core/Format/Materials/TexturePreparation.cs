using System.Runtime.InteropServices;
using System.Text.Json;
using System.Text.Json.Nodes;
using Hammer5Tools.Core.IO.Automation;
using SkiaSharp;

namespace Hammer5Tools.Core.Format.Materials;

internal static class TexturePreparation
{
    private sealed record Image(int Width, int Height, byte[] Pixels);
    private sealed record Output(string Path, Image Image);
    private const string ChannelNames = "rgba";

    internal static JsonObject Execute(JsonElement request, string operation)
    {
        lock (SafeAssetWrites.Sync)
        {
            var root = CompilerService.Text(request, "addon_root");
            if (operation == "inspect")
            {
                var image = Decode(AssetPathResolver.Resolve(request.GetProperty("input").GetString()!, root));
                var threshold = request.TryGetProperty("constant_threshold", out var setting) ? setting.GetInt32() : 0;
                if (threshold is < 0 or > 255)
                {
                    throw new ArgumentException("constant_threshold must be 0..255; zero means exact.");
                }

                var channels = new JsonObject();
                for (var channel = 0; channel < 4; channel++)
                {
                    var min = 255; var max = 0;
                    for (var pixel = channel; pixel < image.Pixels.Length; pixel += 4)
                    {
                        min = Math.Min(min, image.Pixels[pixel]); max = Math.Max(max, image.Pixels[pixel]);
                    }
                    channels[ChannelNames[channel].ToString()] = new JsonObject { ["minimum"] = min, ["maximum"] = max, ["constant"] = max - min <= threshold };
                }
                return new JsonObject
                {
                    ["width"] = image.Width,
                    ["height"] = image.Height,
                    ["bit_depth"] = 8,
                    ["constant_threshold"] = threshold,
                    ["semantics"] = "raw channel values; no gamma/linear conversion",
                    ["channels"] = channels
                };
            }
            var outputs = new List<Output>();
            if (operation == "split")
            {
                var image = Decode(AssetPathResolver.Resolve(request.GetProperty("input").GetString()!, root));
                foreach (var output in request.GetProperty("outputs").EnumerateArray())
                {
                    var channel = Channel(output.GetProperty("channel").GetString()!);
                    var pixels = new byte[image.Pixels.Length];
                    for (var index = 0; index < pixels.Length; index += 4)
                    {
                        pixels[index] = pixels[index + 1] = pixels[index + 2] = image.Pixels[index + channel]; pixels[index + 3] = 255;
                    }
                    outputs.Add(new Output(AssetPathResolver.Resolve(output.GetProperty("path").GetString()!, root, false), new Image(image.Width, image.Height, pixels)));
                }
            }
            else if (operation == "pack")
            {
                var mapping = request.GetProperty("channels");
                var images = new Dictionary<int, Image>();
                var constants = new Dictionary<int, byte>();
                var channels = new Dictionary<int, int>();
                for (var channel = 0; channel < 4; channel++)
                {
                    var entry = mapping.GetProperty(ChannelNames[channel].ToString());
                    if (entry.ValueKind == JsonValueKind.Number)
                    {
                        constants[channel] = entry.GetByte();
                    }
                    else
                    {
                        images[channel] = Decode(AssetPathResolver.Resolve(entry.GetProperty("path").GetString()!, root));
                        channels[channel] = Channel(entry.GetProperty("channel").GetString()!);
                    }
                }
                if (images.Count == 0)
                {
                    throw new ArgumentException("At least one source image supplies dimensions.");
                }

                var first = images.Values.First();
                if (images.Values.Any(image => image.Width != first.Width || image.Height != first.Height))
                {
                    throw new ArgumentException("Source dimensions must match.");
                }

                var pixels = new byte[first.Pixels.Length];
                for (var index = 0; index < pixels.Length; index++)
                {
                    var channel = index % 4;
                    pixels[index] = constants.TryGetValue(channel, out var constant) ? constant : images[channel].Pixels[index - channel + channels[channel]];
                }
                outputs.Add(new Output(AssetPathResolver.Resolve(request.GetProperty("path").GetString()!, root, false), new Image(first.Width, first.Height, pixels)));
            }
            else
            {
                throw new ArgumentException("Unknown texture preparation operation.");
            }

            if (outputs.Count == 0 || outputs.Select(output => output.Path).Distinct(StringComparer.OrdinalIgnoreCase).Count() != outputs.Count)
            {
                throw new ArgumentException("Outputs must be nonempty with unique destinations.");
            }

            foreach (var output in outputs)
            {
                if (!output.Path.EndsWith(".png", StringComparison.OrdinalIgnoreCase))
                {
                    throw new ArgumentException("Lossless output must be PNG.");
                }

                if (File.Exists(output.Path) && !CompilerService.Flag(request, "overwrite"))
                {
                    throw new IOException("Output exists; set overwrite explicitly.");
                }
            }
            var dry = CompilerService.Flag(request, "dry_run");
            var staged = new Dictionary<string, string>();
            var rows = new JsonArray();
            var failed = 0;
            try
            {
                if (!dry)
                {
                    foreach (var output in outputs)
                    {
                        staged[output.Path] = SafeAssetWrites.Stage(output.Path, path => Encode(path, output.Image), path =>
                        {
                            var check = Decode(path);
                            if (check.Width != output.Image.Width || check.Height != output.Image.Height || !check.Pixels.AsSpan().SequenceEqual(output.Image.Pixels))
                            {
                                throw new InvalidDataException("Staged PNG did not preserve channel values.");
                            }
                        });
                    }
                }
                foreach (var output in outputs)
                {
                    var row = new JsonObject { ["path"] = output.Path, ["width"] = output.Image.Width, ["height"] = output.Image.Height, ["bit_depth"] = 8 };
                    try
                    {
                        if (!dry)
                        {
                            row["backup"] = SafeAssetWrites.Replace(staged[output.Path], output.Path);
                        }

                        row["status"] = dry ? "would_write" : "written";
                    }
                    catch (Exception exception)
                    {
                        failed++; row["status"] = "failed"; row["error"] = exception.Message;
                    }
                    if (rows.Count < 50)
                    {
                        rows.Add(row);
                    }
                }
                return new JsonObject
                {
                    ["dry_run"] = dry,
                    ["failed"] = failed,
                    ["total"] = outputs.Count,
                    ["outputs"] = rows,
                    ["truncated"] = outputs.Count > 50,
                    ["atomicity"] = "per-file replacement; batch has no rollback",
                    ["semantics"] = "raw channels; no color-space conversion"
                };
            }
            finally
            {
                foreach (var path in staged.Values)
                {
                    File.Delete(path);
                }
            }
        }
    }

    private static int Channel(string value)
    {
        var index = value.Length == 1 ? ChannelNames.IndexOf(value, StringComparison.Ordinal) : -1;
        return index >= 0 ? index : throw new ArgumentException("Channel must be r, g, b, or a.");
    }

    private static Image Decode(string path)
    {
        var bytes = File.ReadAllBytes(path);
        // Explicitly reject higher bit depth instead of silently quantizing it through Skia.
        if (bytes.Length < 26 || !bytes.AsSpan(0, 8).SequenceEqual(new byte[] { 137, 80, 78, 71, 13, 10, 26, 10 }) || bytes[24] != 8)
        {
            throw new NotSupportedException("Texture preparation currently supports 8-bit PNG only; other formats/bit depths are rejected.");
        }

        using var stream = new SKMemoryStream(bytes);
        using var codec = SKCodec.Create(stream);
        using var bitmap = new SKBitmap(new SKImageInfo(codec.Info.Width, codec.Info.Height, SKColorType.Rgba8888, SKAlphaType.Unpremul));
        if (codec.GetPixels(bitmap.Info, bitmap.GetPixels()) != SKCodecResult.Success)
        {
            throw new InvalidDataException("PNG decode failed.");
        }

        return new Image(bitmap.Width, bitmap.Height, bitmap.Bytes);
    }

    private static void Encode(string path, Image image)
    {
        using var bitmap = new SKBitmap(new SKImageInfo(image.Width, image.Height, SKColorType.Rgba8888, SKAlphaType.Unpremul));
        Marshal.Copy(image.Pixels, 0, bitmap.GetPixels(), image.Pixels.Length);
        using var data = bitmap.Encode(SKEncodedImageFormat.Png, 100) ?? throw new InvalidDataException("PNG encode failed.");
        using var output = File.Create(path);
        data.SaveTo(output);
    }
}
