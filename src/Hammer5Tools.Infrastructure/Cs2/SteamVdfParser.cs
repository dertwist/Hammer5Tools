namespace Hammer5Tools.Infrastructure.Cs2;

using System.Text;
using ValveKeyValue;

/// <summary>
/// Parser for Steam KeyValue 1 format files (libraryfolders.vdf and appmanifest_*.acf) using ValveKeyValue.
/// </summary>
public static class SteamVdfParser
{
    private static readonly KVSerializer Kv1Serializer = KVSerializer.Create(KVSerializationFormat.KeyValues1Text);

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

        try
        {
            using var ms = new MemoryStream(Encoding.UTF8.GetBytes(vdfContent));
            var doc = Kv1Serializer.Deserialize(ms);

            foreach (var (_, folderObj) in doc.Root.Children)
            {
                if (folderObj.TryGetValue("path", out var pathObj) && pathObj is not null)
                {
                    var rawPath = pathObj.ToString().Replace(@"\\", @"\");
                    if (!string.IsNullOrWhiteSpace(rawPath))
                    {
                        var normalized = Path.GetFullPath(rawPath);
                        if (!seen.Add(normalized))
                        {
                            continue;
                        }

                        var hasCs2 = folderObj.TryGetValue("apps", out var appsObj) &&
                                     appsObj is not null &&
                                     appsObj.ContainsKey("730");

                        if (hasCs2)
                        {
                            cs2Folders.Add(normalized);
                        }
                        else
                        {
                            otherFolders.Add(normalized);
                        }
                    }
                }
            }
        }
        catch
        {
            // Graceful handling for non-standard input
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

        try
        {
            using var ms = new MemoryStream(Encoding.UTF8.GetBytes(acfContent));
            var doc = Kv1Serializer.Deserialize(ms);
            if (doc.Root.TryGetValue("installdir", out var installDirObj) && installDirObj is not null)
            {
                return installDirObj.ToString().Replace(@"\\", @"\").Trim();
            }
        }
        catch
        {
            // Graceful handling for non-standard input
        }

        return null;
    }
}
