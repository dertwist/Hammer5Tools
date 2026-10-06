using SteamDatabase.ValvePak;

namespace Hammer5Tools.Core.IO.Vpk;

/// <summary>
/// Resolves paths across mounted VPK archives and loose directories.
/// </summary>
public sealed class VpkIndex : IDisposable
{
    private readonly List<Package> packages = [];
    private readonly List<string> looseRoots = [];

    /// <summary>
    /// Gets the number of mounted VPK archives.
    /// </summary>
    public int PackageCount => packages.Count;

    /// <summary>
    /// Mounts a <c>_dir.vpk</c>. Missing paths are ignored.
    /// </summary>
    public void MountVpk(string vpkPath)
    {
        if (!File.Exists(vpkPath))
            return;

        var package = new Package();
        package.Read(vpkPath);
        packages.Add(package);
    }

    /// <summary>
    /// Adds a loose directory root to search. Missing directories are ignored.
    /// </summary>
    public void AddLooseRoot(string directory)
    {
        if (Directory.Exists(directory))
            looseRoots.Add(directory);
    }

    /// <summary>
    /// Gets whether a path exists in a loose root or a mounted VPK archive.
    /// </summary>
    public bool Exists(string path) => ExistsLoose(path) || ExistsInVpk(path);

    /// <summary>
    /// Gets whether a path exists in a loose root.
    /// </summary>
    public bool ExistsLoose(string path) => TryGetLooseRoot(path) is not null;

    /// <summary>
    /// Gets the first loose root that contains a path, or <c>null</c> when none does.
    /// </summary>
    public string? TryGetLooseRoot(string path)
    {
        ArgumentNullException.ThrowIfNull(path);

        var forward = path.Replace('\\', '/');
        foreach (var root in looseRoots)
        {
            var onDisk = Path.Combine(root, forward.Replace('/', Path.DirectorySeparatorChar));
            if (File.Exists(onDisk))
                return root;
        }

        return null;
    }

    /// <summary>
    /// Gets whether a path exists in a mounted VPK archive.
    /// </summary>
    public bool ExistsInVpk(string path)
    {
        ArgumentNullException.ThrowIfNull(path);

        var forward = path.Replace('\\', '/');
        foreach (var package in packages)
            if (package.FindEntry(forward) is not null)
                return true;

        return false;
    }

    /// <summary>
    /// Reads bytes from a loose root or mounted VPK archive, or returns <c>null</c> when absent.
    /// </summary>
    public byte[]? TryReadBytes(string path)
    {
        ArgumentNullException.ThrowIfNull(path);

        var forward = path.Replace('\\', '/');

        foreach (var root in looseRoots)
        {
            var onDisk = Path.Combine(root, forward.Replace('/', Path.DirectorySeparatorChar));
            if (File.Exists(onDisk))
                return File.ReadAllBytes(onDisk);
        }

        foreach (var package in packages)
        {
            var entry = package.FindEntry(forward);
            if (entry is null)
                continue;

            package.ReadEntry(entry, out var data);
            return data;
        }

        return null;
    }

    /// <summary>
    /// Enumerates mounted VPK entries whose paths end with one of the supplied suffixes.
    /// </summary>
    public IReadOnlyList<VpkEntry> EnumerateEntries(IReadOnlyCollection<string> suffixes)
    {
        ArgumentNullException.ThrowIfNull(suffixes);

        var normalizedSuffixes = suffixes
            .Select(suffix => suffix.StartsWith('.') ? suffix : $".{suffix}")
            .ToArray();
        var results = new List<VpkEntry>();
        foreach (var package in packages)
        {
            if (package.Entries is null)
            {
                continue;
            }
            foreach (var entries in package.Entries.Values)
            {
                foreach (var entry in entries)
                {
                    var directory = entry.DirectoryName?.Replace('\\', '/').Trim('/') ?? string.Empty;
                    var path = string.IsNullOrEmpty(directory)
                        ? $"{entry.FileName}.{entry.TypeName}"
                        : $"{directory}/{entry.FileName}.{entry.TypeName}";
                    var sourcePath = path.EndsWith("_c", StringComparison.OrdinalIgnoreCase)
                        ? path[..^2]
                        : path;
                    if (normalizedSuffixes.Length > 0
                        && !normalizedSuffixes.Any(suffix =>
                            sourcePath.EndsWith(suffix, StringComparison.OrdinalIgnoreCase)))
                    {
                        continue;
                    }
                    results.Add(new VpkEntry(sourcePath, entry.TotalLength));
                }
            }
        }
        return results;
    }

    /// <inheritdoc />
    public void Dispose()
    {
        foreach (var package in packages)
            package.Dispose();

        packages.Clear();
    }
}
