namespace SourcePorter.Core.Toolchain;

/// <summary>
/// Removes the intermediate <c>importfilelist</c> scratch files the importer
/// writes into an addon's <c>content\</c> tree — <c>*_refs.txt</c>,
/// <c>*_mdl_lst.txt</c>/<c>*_mtl_lst.txt</c>, <c>*_new_refs.txt</c>,
/// <c>*_compile_new_refs.txt</c>, the <c>repair_*.txt</c> lists, and the
/// per-model <c>*_refs\</c> mesh-info directories — left behind by
/// <see cref="MapImportService"/> and <see cref="MissingAssetImporter"/>.
///
/// These are throwaway list files regenerated on every import; deleting them
/// only declutters the addon and never touches the actual ported assets
/// (<c>.vmap</c>/<c>.vmdl</c>/<c>.vmat</c>/textures). Tools → Clean refs files.
/// </summary>
public static class RefsCleanup
{
    /// <summary>File globs the importer uses for its scratch list files.</summary>
    private static readonly string[] FilePatterns = ["*_refs.txt", "*_lst.txt"];

    /// <summary>The result of a cleanup sweep: how many entries were removed and the bytes freed.</summary>
    public readonly record struct Result(int FileCount, int DirCount, long BytesFreed);

    /// <summary>
    /// Recursively deletes the importer's scratch refs files (and <c>*_refs\</c>
    /// directories) under <paramref name="contentRoot"/>. Returns a no-op result
    /// when the root doesn't exist.
    /// </summary>
    public static Result Clean(string contentRoot)
    {
        if (!Directory.Exists(contentRoot))
            return default;

        var files = 0;
        var dirs = 0;
        long bytes = 0;

        foreach (var pattern in FilePatterns)
        {
            foreach (var file in Directory.EnumerateFiles(contentRoot, pattern, SearchOption.AllDirectories))
            {
                try
                {
                    bytes += new FileInfo(file).Length;
                    File.Delete(file);
                    files++;
                }
                catch (IOException) { }
                catch (UnauthorizedAccessException) { }
            }
        }

        // Per-model "<model>_refs\" dirs hold mesh/meshinfo.txt the model pass emits. Only ever
        // delete one whose contents are entirely .txt — never recurse-delete real ported assets
        // (.vmdl/.vmat/textures) just because a directory happens to match the "*_refs" glob.
        foreach (var dir in Directory.EnumerateDirectories(contentRoot, "*_refs", SearchOption.AllDirectories))
        {
            var entries = Directory.EnumerateFiles(dir, "*", SearchOption.AllDirectories).ToList();
            if (entries.Any(f => !f.EndsWith(".txt", StringComparison.OrdinalIgnoreCase)))
                continue;

            try
            {
                bytes += DirectorySize(dir);
                Directory.Delete(dir, recursive: true);
                dirs++;
            }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
        }

        return new Result(files, dirs, bytes);
    }

    private static long DirectorySize(string dir)
    {
        long total = 0;
        foreach (var file in Directory.EnumerateFiles(dir, "*", SearchOption.AllDirectories))
        {
            try { total += new FileInfo(file).Length; }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
        }
        return total;
    }
}
