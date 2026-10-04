namespace Hammer5Tools.Core.IO.Automation;

/// <summary>Resolves loose source/output files independently of archive resource names.</summary>
public static class AssetPathResolver
{
    /// <summary>Resolves a source path, confining relative inputs to the supplied addon.</summary>
    public static string Resolve(string path, string? addonRoot = null, bool mustExist = true)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        path = path.Replace('\\', Path.DirectorySeparatorChar).Replace('/', Path.DirectorySeparatorChar);
        if (path.Length >= 2 && path[1] == ':' && !Path.IsPathFullyQualified(path))
        {
            throw new ArgumentException("Drive-relative paths are unsupported; use C:/path or an addon-relative path.");
        }
        if (Path.IsPathRooted(path) && !Path.IsPathFullyQualified(path))
        {
            throw new ArgumentException("Root-relative paths require a full drive or UNC path.");
        }

        string resolved;
        if (Path.IsPathFullyQualified(path))
        {
            resolved = Path.GetFullPath(path);
        }
        else
        {
            if (string.IsNullOrWhiteSpace(addonRoot))
            {
                throw new ArgumentException("Relative paths require addon_root or an active configured addon.");
            }
            if (!Path.IsPathFullyQualified(addonRoot))
            {
                throw new ArgumentException("addon_root must be an absolute directory.");
            }
            var root = Path.GetFullPath(addonRoot);
            if (!Directory.Exists(root))
            {
                throw new DirectoryNotFoundException($"Addon root not found: '{root}'");
            }
            resolved = Path.GetFullPath(Path.Combine(root, path));
            RequireContained(root, resolved);
            RequireContained(ResolveLinks(root), ResolveLinks(resolved));
        }
        if (mustExist && !File.Exists(resolved))
        {
            throw new FileNotFoundException($"Asset file not found: '{resolved}'", resolved);
        }
        return resolved;
    }

    private static void RequireContained(string root, string candidate)
    {
        var comparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
        if (!candidate.StartsWith(Path.TrimEndingDirectorySeparator(root) + Path.DirectorySeparatorChar, comparison))
        {
            throw new ArgumentException("Relative path escapes the selected addon root.");
        }
    }

    private static string ResolveLinks(string path)
    {
        var current = Path.GetPathRoot(path)!;
        foreach (var part in path[current.Length..].Split(Path.DirectorySeparatorChar, StringSplitOptions.RemoveEmptyEntries))
        {
            current = Path.Combine(current, part);
            FileSystemInfo info = Directory.Exists(current) ? new DirectoryInfo(current) : new FileInfo(current);
            if (info.LinkTarget is not null)
            {
                current = info.ResolveLinkTarget(true)?.FullName
                    ?? throw new IOException($"Unable to resolve link '{current}'.");
            }
        }
        return current;
    }
}
