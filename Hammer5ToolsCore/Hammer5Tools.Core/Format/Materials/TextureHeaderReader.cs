using System.Buffers.Binary;

namespace Hammer5Tools.Core.Format.Materials;

/// <summary>
/// Lightweight reader for texture image headers (.vtf, .tga, .png) to determine
/// pixel dimensions without decoding full image payload.
/// </summary>
public static class TextureHeaderReader
{
    public static (int Width, int Height)? TryReadDimensions(string imagePath)
    {
        if (string.IsNullOrEmpty(imagePath) || !File.Exists(imagePath))
            return null;

        var ext = Path.GetExtension(imagePath).ToLowerInvariant();
        return ext switch
        {
            ".vtf" => VtfHeader.TryReadDimensions(imagePath),
            ".tga" => TryReadTgaDimensions(imagePath),
            ".png" => TryReadPngDimensions(imagePath),
            _ => null
        };
    }

    private static (int Width, int Height)? TryReadTgaDimensions(string path)
    {
        try
        {
            using var stream = File.OpenRead(path);
            if (stream.Length < 18)
                return null;

            Span<byte> head = stackalloc byte[18];
            if (!ReadExactly(stream, head))
                return null;

            ushort width = BinaryPrimitives.ReadUInt16LittleEndian(head[12..]);
            ushort height = BinaryPrimitives.ReadUInt16LittleEndian(head[14..]);
            if (width > 0 && height > 0)
                return (width, height);
        }
        catch { }
        return null;
    }

    private static (int Width, int Height)? TryReadPngDimensions(string path)
    {
        try
        {
            using var stream = File.OpenRead(path);
            if (stream.Length < 24)
                return null;

            Span<byte> head = stackalloc byte[24];
            if (!ReadExactly(stream, head))
                return null;

            if (head[0] == 0x89 && head[1] == 0x50 && head[2] == 0x4E && head[3] == 0x47)
            {
                int width = BinaryPrimitives.ReadInt32BigEndian(head[16..]);
                int height = BinaryPrimitives.ReadInt32BigEndian(head[20..]);
                if (width > 0 && height > 0)
                    return (width, height);
            }
        }
        catch { }
        return null;
    }

    private static bool ReadExactly(Stream stream, Span<byte> buffer)
    {
        var read = 0;
        while (read < buffer.Length)
        {
            var n = stream.Read(buffer[read..]);
            if (n == 0)
                return false;
            read += n;
        }
        return true;
    }
}
