using SteamDatabase.ValvePak;

namespace Hammer5Tools.Core.Resources;

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

    /// <inheritdoc />
    public void Dispose()
    {
        foreach (var package in packages)
            package.Dispose();

        packages.Clear();
    }
}
