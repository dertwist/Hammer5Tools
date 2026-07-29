using SourcePorter.Core.Domain;

namespace SourcePorter.Core.Toolchain;

/// <summary>
/// Stages a source map into a clean temp content root that satisfies
/// <c>source1import</c>'s required <c>&lt;contentdir&gt;\maps\&lt;name&gt;.vmf</c>
/// layout. This lets users point at a loose <c>.vmf</c> (or a <c>.bsp</c> sitting
/// anywhere) without us writing into their own folders, and gives a self-contained
/// content root for a decompiled <c>.bsp</c>'s unpacked materials/models.
/// <para>
/// The returned <c>.vmf</c> path always lives under a <c>maps\</c> folder, so
/// <see cref="Cs2Install.TryParseSourceMap"/> can split it into the content dir and
/// map name the importer needs.
/// </para>
/// </summary>
public static class MapStaging
{
    /// <summary>Parent of every per-map staging dir: <c>%TEMP%\SourcePorter</c>.</summary>
    public static string StagingRoot => Path.Combine(Path.GetTempPath(), "SourcePorter");

    /// <summary>
    /// Deletes the whole staging root (every per-map BSP decompile / unpacked-embedded
    /// content cache) and reports how many bytes were reclaimed. These dirs are throwaway
    /// scratch space — each import re-creates its own via <see cref="FreshRoot"/> — so
    /// clearing them is always safe. Returns the number of bytes freed (0 if nothing was
    /// cached). Never throws if the root is absent.
    /// </summary>
    public static long CleanCache()
    {
        if (!Directory.Exists(StagingRoot))
            return 0;
        var bytes = DirSize(StagingRoot);
        SafeDeleteTree(StagingRoot);
        return bytes;
    }

    /// <summary>
    /// Recursively deletes <paramref name="dir"/>, removing any directory <b>junction</b>/symlink
    /// as a link rather than following it into — and deleting — its target. A plain
    /// <c>Directory.Delete(recursive)</c> can throw on a tree that contains a reparse point.
    /// </summary>
    internal static void SafeDeleteTree(string dir)
    {
        foreach (var sub in Directory.EnumerateDirectories(dir))
        {
            if ((File.GetAttributes(sub) & FileAttributes.ReparsePoint) != 0)
                Directory.Delete(sub); // a junction/symlink: drop the link only
            else
                SafeDeleteTree(sub);
        }
        foreach (var file in Directory.EnumerateFiles(dir))
            File.Delete(file);
        Directory.Delete(dir);
    }

    /// <summary>Total size of real files under <paramref name="dir"/>, NOT following directory
    /// junctions (so a <c>csgo</c> junction doesn't make us count the whole CS:GO install).</summary>
    private static long DirSize(string dir)
    {
        long bytes = 0;
        foreach (var sub in Directory.EnumerateDirectories(dir))
        {
            if ((File.GetAttributes(sub) & FileAttributes.ReparsePoint) != 0)
                continue;
            bytes += DirSize(sub);
        }
        foreach (var file in Directory.EnumerateFiles(dir))
        {
            try { bytes += new FileInfo(file).Length; }
            catch { /* a file vanishing mid-walk shouldn't abort the cleanup */ }
        }
        return bytes;
    }

    /// <summary>
    /// Ensures <paramref name="vmfPath"/> is usable as a source map. A correctly
    /// structured map that <c>source1import</c> already accepts (under a <c>maps\</c>
    /// folder, with the required header) is used in place — preserving its sibling
    /// materials/models content root. Anything else (a loose <c>.vmf</c>, or a
    /// decompiled one missing the <c>versioninfo</c> preamble) is copied into a fresh
    /// temp content root and fixed up there, so the user's own file is never mutated.
    /// Returns the path to feed <see cref="Cs2Install.BuildProject"/>.
    /// </summary>
    public static string StageVmf(string vmfPath, Action<string>? log = null)
    {
        var needsHeader = !VmfNormalizer.HasImportableHeader(vmfPath);
        if (!needsHeader && Cs2Install.TryParseSourceMap(vmfPath, out _, out _))
            return vmfPath;

        var mapName = Path.GetFileNameWithoutExtension(vmfPath);
        var maps = Path.Combine(FreshRoot(mapName), "maps");
        Directory.CreateDirectory(maps);
        var dest = Path.Combine(maps, mapName + ".vmf");
        File.Copy(vmfPath, dest, overwrite: true);
        if (needsHeader)
        {
            // Only a decompiled .vmf lacks the header; the same source can be missing
            // the displacement offset subkeys, so repair them on this temp copy too
            // (idempotent — a normal Hammer .vmf already has them).
            VmfNormalizer.EnsureImportableHeader(dest, log);
            VmfNormalizer.EnsureDisplacementOffsets(dest, log);
        }
        return dest;
    }

    /// <summary>
    /// Decompiles <paramref name="bspPath"/> into a fresh temp content root and,
    /// when <paramref name="unpackEmbedded"/> is set, extracts its embedded
    /// materials/models/etc. alongside, then places the decompiled <c>.vmf</c> under
    /// <c>maps\</c> in that same root. Returns the staged <c>.vmf</c> path.
    /// </summary>
    public static async Task<string> StageBspAsync(
        BspDecompiler decompiler, string bspPath, bool unpackEmbedded, CancellationToken ct = default)
    {
        var mapName = Path.GetFileNameWithoutExtension(bspPath);
        var root = FreshRoot(mapName);

        // Decompile the .vmf at the root level. When unpacking, BSPSource extracts the
        // embedded files into "<root>\<mapName>\" (a content root of its own), so we
        // adopt that as the content root and drop the .vmf into its maps\ folder.
        var rawVmf = Path.Combine(root, mapName + ".vmf");
        var result = await decompiler.DecompileAsync(bspPath, rawVmf, unpackEmbedded, ct);

        var contentRoot = result.UnpackDir ?? root;
        var maps = Path.Combine(contentRoot, "maps");
        Directory.CreateDirectory(maps);
        var stagedVmf = Path.Combine(maps, mapName + ".vmf");
        File.Move(result.VmfPath, stagedVmf, overwrite: true);
        return stagedVmf;
    }

    // A clean, predictable per-map dir under the staging root (cleared if it already
    // exists, so a re-run never inherits stale content from a previous attempt).
    private static string FreshRoot(string mapName)
    {
        var root = Path.Combine(StagingRoot, mapName);
        if (Directory.Exists(root))
            SafeDeleteTree(root); // may contain a csgo junction from a previous run
        Directory.CreateDirectory(root);
        return root;
    }
}
