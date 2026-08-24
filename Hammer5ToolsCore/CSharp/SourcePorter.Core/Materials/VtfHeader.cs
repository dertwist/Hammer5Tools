using System.Buffers.Binary;

namespace SourcePorter.Core.Materials;

/// <summary>
/// Minimal reader for the Source 1 <c>.vtf</c> (Valve Texture Format) header — enough
/// to recover a texture's pixel dimensions without decoding the image body.
///
/// This is the building block for the "custom-material scale" fix: Valve's
/// <c>source1import</c> needs a material's texture mapping dimensions to compute
/// brush-face UV scale, and when it can't open a custom <c>.vmt</c>/<c>.vtf</c> it logs
/// <c>GetMappingDimensionsForVMT: can't open …</c> and falls back to a default size — so
/// the imported brush material comes out at the wrong scale (ARCHITECTURE §4, "Custom-
/// material scale" limitation). Reading the dimensions here, with no Valve binary, lets a
/// non-binary import/repair path use the real size instead of the default.
///
/// Layout mirrors the public VTF header (all little-endian):
/// <code>
///   0   char[4]  signature  "VTF\0"
///   4   uint32   version[0]
///   8   uint32   version[1]
///   12  uint32   headerSize
///   16  uint16   width
///   18  uint16   height
///   20  uint32   flags
///   22  uint16   frames
///   ...
/// </code>
/// </summary>
public readonly record struct VtfHeader(int Width, int Height, uint Flags, int VersionMajor, int VersionMinor)
{
    private static ReadOnlySpan<byte> Signature => "VTF\0"u8;

    /// <summary>Reads just the fields needed for dimensions from a <c>.vtf</c> file. Returns null if the file is missing or not a VTF.</summary>
    public static VtfHeader? TryRead(string vtfPath)
    {
        try
        {
            if (!File.Exists(vtfPath))
                return null;

            // The dimensions live in the first 24 bytes; never read the (potentially huge) image body.
            Span<byte> head = stackalloc byte[24];
            using var stream = File.OpenRead(vtfPath);
            if (stream.Length < head.Length || !ReadExactly(stream, head))
                return null;

            return Parse(head);
        }
        catch (IOException)
        {
            return null;
        }
        catch (UnauthorizedAccessException)
        {
            return null;
        }
    }

    /// <summary>Parses the header from an in-memory buffer (at least 24 bytes). Returns null if the signature is wrong.</summary>
    public static VtfHeader? Parse(ReadOnlySpan<byte> head)
    {
        if (head.Length < 24 || !head[..4].SequenceEqual(Signature))
            return null;

        var versionMajor = (int)BinaryPrimitives.ReadUInt32LittleEndian(head[4..]);
        var versionMinor = (int)BinaryPrimitives.ReadUInt32LittleEndian(head[8..]);
        var width = BinaryPrimitives.ReadUInt16LittleEndian(head[16..]);
        var height = BinaryPrimitives.ReadUInt16LittleEndian(head[18..]);
        var flags = BinaryPrimitives.ReadUInt32LittleEndian(head[20..]);

        return new VtfHeader(width, height, flags, versionMajor, versionMinor);
    }

    /// <summary>Convenience: width/height of a <c>.vtf</c>, or null if unreadable.</summary>
    public static (int Width, int Height)? TryReadDimensions(string vtfPath)
        => TryRead(vtfPath) is { } h ? (h.Width, h.Height) : null;

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
