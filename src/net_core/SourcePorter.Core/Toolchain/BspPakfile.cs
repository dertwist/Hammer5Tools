using System.Buffers.Binary;
using System.IO.Compression;

namespace SourcePorter.Core.Toolchain;

/// <summary>
/// Reads a Source 1 <c>.bsp</c>'s embedded <b>pakfile</b> lump (LUMP_PAKFILE, a standard ZIP) directly
/// — so the missing-asset repair can search the BSP's embedded files even when BSPSource's
/// <c>--unpack_embedded</c> didn't write a given file to disk. The map's custom <c>.vmt</c>/<c>.vtf</c>
/// /<c>.mdl</c> are packed here, so this is the authoritative "BSP embedded files" source.
///
/// BSP header layout (little-endian): <c>int ident ("VBSP"), int version, lump_t[64], int revision</c>,
/// where <c>lump_t = { int fileofs; int filelen; int version; char fourCC[4]; }</c>. Lump index 40 is
/// the pakfile. Best-effort and non-throwing on a malformed/absent file.
/// </summary>
public sealed class BspPakfile : IDisposable
{
    private const int LumpPakfile = 40;
    private const int HeaderLumpsOffset = 8;   // after ident + version
    private const int LumpEntrySize = 16;      // fileofs + filelen + version + fourCC
    private static ReadOnlySpan<byte> Ident => "VBSP"u8;

    private readonly ZipArchive? _zip;
    // entry name (forward-slash, lower-case) -> entry
    private readonly Dictionary<string, ZipArchiveEntry> _entries = new(StringComparer.OrdinalIgnoreCase);

    private BspPakfile(ZipArchive? zip)
    {
        _zip = zip;
        if (_zip is null)
            return;
        foreach (var entry in _zip.Entries)
            _entries[entry.FullName.Replace('\\', '/')] = entry;
    }

    /// <summary>Number of files in the embedded pakfile (0 if none / unreadable).</summary>
    public int EntryCount => _entries.Count;

    /// <summary>All packed file paths (forward-slash).</summary>
    public IEnumerable<string> EntryPaths => _entries.Keys;

    /// <summary>Opens <paramref name="bspPath"/>'s embedded pakfile. Returns an empty (but usable)
    /// instance if the file is missing, not a BSP, or has no pakfile lump.</summary>
    public static BspPakfile Open(string? bspPath)
    {
        if (string.IsNullOrEmpty(bspPath) || !File.Exists(bspPath))
            return new BspPakfile(null);

        try
        {
            using var stream = File.OpenRead(bspPath);
            Span<byte> header = stackalloc byte[HeaderLumpsOffset + LumpEntrySize * 64];
            if (stream.Length < header.Length || !ReadExactly(stream, header) || !header[..4].SequenceEqual(Ident))
                return new BspPakfile(null);

            var entry = header.Slice(HeaderLumpsOffset + LumpPakfile * LumpEntrySize, LumpEntrySize);
            var fileofs = BinaryPrimitives.ReadInt32LittleEndian(entry);
            var filelen = BinaryPrimitives.ReadInt32LittleEndian(entry[4..]);
            if (fileofs <= 0 || filelen <= 0 || fileofs + (long)filelen > stream.Length)
                return new BspPakfile(null);

            var data = new byte[filelen];
            stream.Seek(fileofs, SeekOrigin.Begin);
            if (!ReadExactly(stream, data))
                return new BspPakfile(null);

            // ZipArchive needs a seekable stream that stays open for the archive's lifetime.
            var zip = new ZipArchive(new MemoryStream(data), ZipArchiveMode.Read);
            return new BspPakfile(zip);
        }
        catch (Exception ex) when (ex is IOException or InvalidDataException or UnauthorizedAccessException)
        {
            return new BspPakfile(null);
        }
    }

    /// <summary>True if a forward-slash path (e.g. <c>materials/foo/bar.vmt</c>) is in the pakfile.</summary>
    public bool Exists(string path) => _entries.ContainsKey(path.Replace('\\', '/'));

    /// <summary>
    /// Extracts <b>every</b> packed file into <paramref name="destRoot"/>, preserving its relative
    /// path — the full, unfiltered unpack (unlike BSPSource's "smart" unpack, which drops
    /// vbsp-generated materials such as the <c>maps/&lt;map&gt;/…_wvt_patch.vmt</c> the map needs).
    /// Existing files are overwritten. Returns the number of files written.
    /// </summary>
    public int ExtractAll(string destRoot, Action<string>? log = null)
    {
        if (_zip is null)
            return 0;

        var written = 0;
        foreach (var entry in _zip.Entries)
        {
            // Skip directory entries (zip dirs end in '/').
            if (entry.FullName.EndsWith('/') || entry.FullName.EndsWith('\\'))
                continue;

            var rel = entry.FullName.Replace('\\', '/').TrimStart('/');
            if (rel.Length == 0)
                continue;

            try
            {
                var outPath = Path.Combine(destRoot, rel.Replace('/', Path.DirectorySeparatorChar));
                Directory.CreateDirectory(Path.GetDirectoryName(outPath)!);
                using (var es = entry.Open())
                using (var fs = File.Create(outPath))
                    es.CopyTo(fs);
                written++;
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or InvalidDataException)
            {
                log?.Invoke($"Could not extract {rel}: {ex.Message}");
            }
        }
        return written;
    }

    /// <summary>Reads a packed file's bytes, or null if absent.</summary>
    public byte[]? TryReadBytes(string path)
    {
        if (!_entries.TryGetValue(path.Replace('\\', '/'), out var entry))
            return null;
        using var es = entry.Open();
        using var ms = new MemoryStream();
        es.CopyTo(ms);
        return ms.ToArray();
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

    public void Dispose() => _zip?.Dispose();
}
