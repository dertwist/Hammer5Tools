using System.Text;

namespace SourcePorter.Core.Validation;

/// <summary>
/// Minimal reader for the Source 2 resource container (the <c>_c</c> files:
/// <c>.vmap_c</c>, <c>.vmdl_c</c>, <c>.vmat_c</c>, …). It reads only the **RERL**
/// block — the authoritative list of external files a compiled resource depends
/// on — which is what we need to detect missing files.
///
/// The binary layout mirrors ValveResourceFormat's <c>Resource</c> header and
/// <c>ResourceExtRefList.Read</c> (studied under <c>reference/</c>); ValveKeyValue
/// cannot parse this container, so this small reader fills that gap.
/// </summary>
public static class Source2Resource
{
    private const ushort KnownHeaderVersion = 12;

    /// <summary>
    /// Returns the external resource references (RERL) of a compiled resource.
    /// Names use the uncompiled extension (e.g. <c>materials/foo.vmat</c>,
    /// <c>models/bar.vmesh</c>) — append <c>_c</c> to find them on disk.
    /// </summary>
    /// <exception cref="InvalidDataException">The stream is not a Source 2 resource.</exception>
    public static IReadOnlyList<string> ReadExternalReferences(Stream stream)
    {
        using var reader = new BinaryReader(stream, Encoding.UTF8, leaveOpen: true);

        _ = reader.ReadUInt32(); // FileSize (not verified here)
        var headerVersion = reader.ReadUInt16();
        if (headerVersion != KnownHeaderVersion)
            throw new InvalidDataException(
                $"Not a Source 2 resource (header version {headerVersion}, expected {KnownHeaderVersion}).");

        _ = reader.ReadUInt16(); // Version
        var blockOffset = reader.ReadUInt32();
        var blockCount = reader.ReadUInt32();
        reader.BaseStream.Position += blockOffset - 8; // 8 = the two uint32s just read

        long rerlOffset = -1;
        for (var i = 0; i < blockCount; i++)
        {
            var type = Encoding.ASCII.GetString(reader.ReadBytes(4));
            var position = reader.BaseStream.Position;
            var offset = (uint)position + reader.ReadUInt32();
            _ = reader.ReadUInt32(); // block size
            if (type == "RERL")
                rerlOffset = offset;
            reader.BaseStream.Position = position + 8; // advance to next block entry
        }

        return rerlOffset < 0 ? [] : ReadRerlBody(reader, rerlOffset);
    }

    /// <summary>Reads the RERL block body at <paramref name="blockOffset"/>.</summary>
    internal static IReadOnlyList<string> ReadRerlBody(BinaryReader reader, long blockOffset)
    {
        reader.BaseStream.Position = blockOffset;

        var offset = reader.ReadUInt32();
        var size = reader.ReadUInt32();
        if (size == 0)
            return [];

        reader.BaseStream.Position += offset - 8; // 8 = the two uint32s just read

        var names = new List<string>((int)size);
        for (var i = 0; i < size; i++)
        {
            _ = reader.ReadUInt64(); // resource id (unused for existence checks)
            var previous = reader.BaseStream.Position;

            // The string offset is relative to the current position.
            reader.BaseStream.Position += reader.ReadInt64();
            names.Add(ReadNullTerminatedString(reader));

            reader.BaseStream.Position = previous + 8; // account for the int64 we read
        }

        return names;
    }

    private static string ReadNullTerminatedString(BinaryReader reader)
    {
        var bytes = new List<byte>(64);
        byte b;
        while ((b = reader.ReadByte()) != 0)
            bytes.Add(b);
        return Encoding.UTF8.GetString(bytes.ToArray());
    }
}
