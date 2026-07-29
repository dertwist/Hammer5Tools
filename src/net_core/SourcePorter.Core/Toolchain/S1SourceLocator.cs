using SourcePorter.Core.Validation;

namespace SourcePorter.Core.Toolchain;

/// <summary>Where a Source 1 source file was found.</summary>
public enum S1Source
{
    /// <summary>Not found in any CS:GO VPK or custom-content root.</summary>
    NotFound,

    /// <summary>Found loose in a custom-content root (e.g. a decompiled BSP's unpacked assets).</summary>
    CustomContent,

    /// <summary>Found inside a stock CS:GO <c>*_dir.vpk</c> (or loose in the csgo game dir).</summary>
    CsgoVpk,
}

/// <summary>
/// Locates the Source 1 source files (<c>.mdl</c>, <c>.vmt</c>, <c>.vtf</c>) that the importer
/// consumes, searching <b>both</b> the stock CS:GO VPK archives and the map's custom content —
/// so the "Import missing assets" repair only attempts assets it can actually source, and reports
/// the genuinely-sourceless ones honestly instead of firing the toolchain at files that don't exist.
///
/// Custom content wins over stock (a map that ships its own <c>de_coastal/…</c> overrides the base
/// game), matching how Valve's search paths resolve. Built on the same <see cref="VpkIndex"/> the
/// asset validator uses.
/// </summary>
public sealed class S1SourceLocator : IDisposable
{
    private readonly VpkIndex _csgo = new();
    private readonly VpkIndex _custom = new();
    private readonly BspPakfile _bspPak;

    /// <summary>Number of stock CS:GO VPK archives mounted.</summary>
    public int CsgoVpkCount => _csgo.PackageCount;

    /// <summary>Number of files in the original BSP's embedded pakfile (0 if none).</summary>
    public int BspEmbeddedCount => _bspPak.EntryCount;

    /// <summary>
    /// Mounts every <c>*_dir.vpk</c> under <paramref name="csgoGameInfoDir"/> (the CS:GO <c>csgo\</c>
    /// dir) plus that dir as a loose root for stock sources, and treats as <b>custom content</b>:
    /// <paramref name="customContentDir"/> (the staged unpack dir), any <paramref name="extraContentRoots"/>
    /// (e.g. the original <c>.bsp</c>'s own folder), and the original <c>.bsp</c>'s embedded pakfile
    /// (<paramref name="bspPath"/>) read directly — so a file BSPSource didn't unpack is still found.
    /// </summary>
    public S1SourceLocator(
        string csgoGameInfoDir,
        string? customContentDir,
        IEnumerable<string>? extraContentRoots = null,
        string? bspPath = null)
    {
        if (Directory.Exists(csgoGameInfoDir))
        {
            foreach (var vpk in Directory.EnumerateFiles(csgoGameInfoDir, "*_dir.vpk"))
                _csgo.MountVpk(vpk);
            _csgo.AddLooseRoot(csgoGameInfoDir);
        }

        // Only treat the custom dir as custom content when it's a *different* tree than the csgo
        // install — a loose-.vmf project can point S1ContentDir at the csgo dir itself.
        if (!string.IsNullOrWhiteSpace(customContentDir)
            && !PathsEqual(customContentDir, csgoGameInfoDir))
        {
            _custom.AddLooseRoot(customContentDir);
        }

        foreach (var root in extraContentRoots ?? [])
            if (!string.IsNullOrWhiteSpace(root) && !PathsEqual(root, csgoGameInfoDir))
                _custom.AddLooseRoot(root);

        _bspPak = BspPakfile.Open(bspPath);
    }

    /// <summary>
    /// Where a forward-slash source path (e.g. <c>materials/de_coastal/sand.vmt</c>,
    /// <c>models/props/crate.mdl</c>) can be sourced from, searching custom content first.
    /// </summary>
    public S1Source Locate(string sourcePath)
    {
        var forward = sourcePath.Replace('\\', '/');
        if (_custom.ExistsLoose(forward) || _bspPak.Exists(forward))
            return S1Source.CustomContent;
        if (_csgo.Exists(forward))
            return S1Source.CsgoVpk;
        return S1Source.NotFound;
    }

    /// <summary>True if the source exists in either CS:GO VPKs or custom content.</summary>
    public bool Has(string sourcePath) => Locate(sourcePath) != S1Source.NotFound;

    /// <summary>
    /// Reads a source file's text (custom content first, then CS:GO VPKs), or null if absent.
    /// Lets the non-binary <c>MaterialConverter</c> fallback convert a <c>.vmt</c> straight from the
    /// VPK — used for tool materials that <c>source1import</c> blacklists and refuses to import.
    /// </summary>
    public string? TryReadText(string sourcePath)
    {
        var bytes = TryReadBytes(sourcePath);
        return bytes is null ? null : System.Text.Encoding.UTF8.GetString(bytes);
    }

    /// <summary>Reads a source file's bytes (custom content → BSP pakfile → CS:GO VPKs), or null.</summary>
    public byte[]? TryReadBytes(string sourcePath)
    {
        var forward = sourcePath.Replace('\\', '/');
        return _custom.TryReadBytes(forward) ?? _bspPak.TryReadBytes(forward) ?? _csgo.TryReadBytes(forward);
    }

    /// <summary>True if a forward-slash path is only in the BSP's embedded pakfile (not loose on disk).</summary>
    public bool IsOnlyInBspPak(string sourcePath)
    {
        var forward = sourcePath.Replace('\\', '/');
        return !_custom.ExistsLoose(forward) && _bspPak.Exists(forward);
    }

    private static bool PathsEqual(string a, string b)
    {
        static string Norm(string p) => Path.TrimEndingDirectorySeparator(
            Path.GetFullPath(p)).Replace('/', '\\');
        try
        {
            return string.Equals(Norm(a), Norm(b), StringComparison.OrdinalIgnoreCase);
        }
        catch
        {
            return string.Equals(a, b, StringComparison.OrdinalIgnoreCase);
        }
    }

    public void Dispose()
    {
        _csgo.Dispose();
        _custom.Dispose();
        _bspPak.Dispose();
    }
}
