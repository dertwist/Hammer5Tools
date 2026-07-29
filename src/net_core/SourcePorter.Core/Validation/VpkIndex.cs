using SteamDatabase.ValvePak;

namespace SourcePorter.Core.Validation;

/// <summary>
/// Resolves whether a compiled resource exists, across mounted VPK archives
/// (via <c>ValvePak</c>) and loose directories. Used to check that a resource's
/// external references actually resolve to a file the game can load.
/// </summary>
public sealed class VpkIndex : IDisposable
{
    private readonly List<Package> _packages = [];
    private readonly List<string> _looseRoots = [];

    /// <summary>Mounts a <c>_dir.vpk</c> (no-op if the path doesn't exist).</summary>
    public void MountVpk(string vpkPath)
    {
        if (!File.Exists(vpkPath))
            return;

        var package = new Package();
        package.Read(vpkPath);
        _packages.Add(package);
    }

    /// <summary>Adds a loose directory root to search for files on disk.</summary>
    public void AddLooseRoot(string directory)
    {
        if (Directory.Exists(directory))
            _looseRoots.Add(directory);
    }

    public int PackageCount => _packages.Count;

    /// <summary>
    /// True if <paramref name="compiledPath"/> (forward-slash, with the <c>_c</c>
    /// suffix, e.g. <c>materials/foo.vmat_c</c>) exists in any loose root or VPK.
    /// </summary>
    public bool Exists(string compiledPath)
        => ExistsLoose(compiledPath) || ExistsInVpk(compiledPath);

    /// <summary>True if <paramref name="path"/> exists as a loose file under any added root.</summary>
    public bool ExistsLoose(string path)
    {
        var forward = path.Replace('\\', '/');
        foreach (var root in _looseRoots)
        {
            var onDisk = Path.Combine(root, forward.Replace('/', Path.DirectorySeparatorChar));
            if (File.Exists(onDisk))
                return true;
        }
        return false;
    }

    /// <summary>True if <paramref name="path"/> exists inside any mounted VPK archive.</summary>
    public bool ExistsInVpk(string path)
    {
        var forward = path.Replace('\\', '/');
        foreach (var package in _packages)
        {
            if (package.FindEntry(forward) != null)
                return true;
        }
        return false;
    }

    /// <summary>Reads <paramref name="path"/> as bytes from a loose root or a mounted VPK; null if absent.</summary>
    public byte[]? TryReadBytes(string path)
    {
        var forward = path.Replace('\\', '/');

        foreach (var root in _looseRoots)
        {
            var onDisk = Path.Combine(root, forward.Replace('/', Path.DirectorySeparatorChar));
            if (File.Exists(onDisk))
                return File.ReadAllBytes(onDisk);
        }

        foreach (var package in _packages)
        {
            var entry = package.FindEntry(forward);
            if (entry != null)
            {
                package.ReadEntry(entry, out var data);
                return data;
            }
        }

        return null;
    }

    public void Dispose()
    {
        foreach (var package in _packages)
            package.Dispose();
        _packages.Clear();
    }
}
