using System.Linq;
using ValveKeyValue;

namespace SourcePorter.Core.Validation;

/// <summary>
/// Reads <c>gameinfo.gi</c> (a KeyValues1 file) with <c>ValveKeyValue</c> to learn
/// which game directories are on the search path, so the validator knows which
/// base VPK archives to mount. Best-effort: falls back to the defaults
/// (<c>csgo</c>, <c>core</c>) if the file is missing or can't be parsed.
/// </summary>
public static class GameInfo
{
    private static readonly string[] Defaults = ["csgo", "core"];

    /// <summary>Returns the distinct game search-path directory names from gameinfo.gi.</summary>
    public static IReadOnlyList<string> ReadSearchDirs(string gameInfoPath)
    {
        var dirs = new List<string>(Defaults);

        try
        {
            if (!File.Exists(gameInfoPath))
                return dirs;

            using var stream = File.OpenRead(gameInfoPath);
            var serializer = KVSerializer.Create(KVSerializationFormat.KeyValues1Text);
            var root = serializer.Deserialize(stream);

            var fileSystem = FindChild(root, "FileSystem");
            var searchPaths = fileSystem is null ? null : FindChild(fileSystem, "SearchPaths");
            if (searchPaths is null)
                return dirs;

            foreach (var entry in searchPaths)
            {
                var dir = NormalizeSearchDir(entry.Value?.ToString());
                if (dir is not null && !dirs.Contains(dir, StringComparer.OrdinalIgnoreCase))
                    dirs.Add(dir);
            }
        }
        catch
        {
            // Unparseable gameinfo → defaults are still usable.
        }

        return dirs;
    }

    /// <summary>
    /// Reduces a SearchPaths value (e.g. <c>csgo</c>, <c>|all_source_engine_paths|csgo</c>,
    /// <c>|gameinfo_path|.</c>) to its leading directory name, or null if not a plain dir.
    /// </summary>
    private static string? NormalizeSearchDir(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return null;

        var v = value;
        var bar = v.LastIndexOf('|');
        if (bar >= 0)
            v = v[(bar + 1)..];

        v = v.Replace('\\', '/').Trim('/');
        var segment = v.Split('/', StringSplitOptions.RemoveEmptyEntries) is { Length: > 0 } parts ? parts[0] : "";
        return segment is "" or "." ? null : segment;
    }

    private static KVObject? FindChild(KVObject obj, string name) =>
        obj.FirstOrDefault(child => string.Equals(child.Name, name, StringComparison.OrdinalIgnoreCase));
}
