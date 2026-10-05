namespace Hammer5Tools.Core.IO;

internal static class ContentPathResolver
{
    internal static string? Resolve(string mapPath, string relativePath)
    {
        var normalized = relativePath.Replace('\\', '/').TrimStart('/');
        var directory = Path.GetDirectoryName(Path.GetFullPath(mapPath));
        while (directory is not null)
        {
            var candidate = Path.Combine(directory, normalized);
            if (File.Exists(candidate))
            {
                return Path.GetFullPath(candidate);
            }
            directory = Path.GetDirectoryName(directory);
        }
        return null;
    }

}
