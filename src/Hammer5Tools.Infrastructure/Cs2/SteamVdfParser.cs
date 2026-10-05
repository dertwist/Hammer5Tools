namespace Hammer5Tools.Infrastructure.Cs2;

using System.IO;
using System.Text.RegularExpressions;

/// <summary>
/// Parser for Steam KeyValue 1 format files (libraryfolders.vdf and appmanifest_*.acf).
/// </summary>
public static partial class SteamVdfParser
{
    [GeneratedRegex(@"""path""\s+""([^""]+)""", RegexOptions.IgnoreCase)]
    private static partial Regex PathRegex();

    [GeneratedRegex(@"""installdir""\s+""([^""]+)""", RegexOptions.IgnoreCase)]
    private static partial Regex InstallDirRegex();

    [GeneratedRegex(@"""(\d+)""\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}", RegexOptions.Singleline)]
    private static partial Regex LibraryBlockRegex();

    /// <summary>
    /// Parses libraryfolders.vdf content and returns ordered library folders (those with CS2 730 first).
    /// </summary>
    public static List<string> ParseLibraryFolders(string vdfContent)
    {
        if (string.IsNullOrWhiteSpace(vdfContent))
        {
            return [];
        }

        var cs2Folders = new List<string>();
        var otherFolders = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        var blocks = LibraryBlockRegex().Matches(vdfContent);
        foreach (Match block in blocks)
        {
            var text = block.Groups[2].Value;
            var pathMatch = PathRegex().Match(text);
            if (!pathMatch.Success)
            {
                continue;
            }

            var rawPath = pathMatch.Groups[1].Value.Replace(@"\\", @"\");
            var normalized = Path.GetFullPath(rawPath);

            if (!seen.Add(normalized))
            {
                continue;
            }

            var hasCs2 = text.Contains(@"""730""", StringComparison.OrdinalIgnoreCase);
            if (hasCs2)
            {
                cs2Folders.Add(normalized);
            }
            else
            {
                otherFolders.Add(normalized);
            }
        }

        // Fallback for simple "path" "..." without block nesting
        if (cs2Folders.Count == 0 && otherFolders.Count == 0)
        {
            var allPaths = PathRegex().Matches(vdfContent);
            foreach (Match m in allPaths)
            {
                var raw = m.Groups[1].Value.Replace(@"\\", @"\");
                var norm = Path.GetFullPath(raw);
                if (seen.Add(norm))
                {
                    otherFolders.Add(norm);
                }
            }
        }

        var result = new List<string>(cs2Folders.Count + otherFolders.Count);
        result.AddRange(cs2Folders);
        result.AddRange(otherFolders);
        return result;
    }

    /// <summary>
    /// Extracts the installation directory from an appmanifest_*.acf file.
    /// </summary>
    public static string? ParseInstallDir(string acfContent)
    {
        if (string.IsNullOrWhiteSpace(acfContent))
        {
            return null;
        }

        var match = InstallDirRegex().Match(acfContent);
        return match.Success ? match.Groups[1].Value.Replace(@"\\", @"\").Trim() : null;
    }
}
