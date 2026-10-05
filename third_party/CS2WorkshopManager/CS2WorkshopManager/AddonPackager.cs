using System.Globalization;
using System.IO;
using System.Linq;
using ValveKeyValue;
using ValvePak;

namespace CS2WorkshopManager;

/// <summary>
/// Handles packing an addon the same way the CS2 workshop manager does, creating chunked vpks and publish_data.txt
/// </summary>
public static class AddonPackager
{
    private const int Mib = 1024 * 1024;

    /// <summary>Split addon vpks every n mib</summary>
    public const int ChunkSize = 100 * Mib;

    /// <summary>VPK entries store their length as a signed 32 bit value.</summary>
    public const long MaxFileSize = int.MaxValue;

    /// <summary>Limit addon upload size to 3 Gib, same limitation CS2 workshop manager has.</summary>
    public const long MaxTotalSize = 3L * 1024 * Mib;

    public const string PublishDataFileName = "publish_data.txt";

    private const string PublishTimeFormat = "MM/dd/yyyy hh:mm:ss tt";

    // hard coded folders, files and file names that are skipped when uploading
    private static readonly string[] SkippedFileNames =
    [
        "readonly_tools_asset_info.bin",
        "tools_asset_info.bin",
    ];
    private static readonly string[] SkippedDirectoryNames =
    [
        "_bakeresourcecache",
        "_vrad3",
    ];
    private static readonly string[] BlockedExtensions =
    [
        ".bat",
        ".cmd",
        ".com",
        ".dll",
        ".exe",
        ".msi",
        ".rar",
        ".reg",
        ".los",
        ".zip",
    ];

    private readonly record struct VpkDirectoryRule(bool Exclude, string Prefix);

    public static string GetStagingPath(string addonsRoot, ulong publishedFileId)
    {
        return Path.Combine(addonsRoot, "vpks", publishedFileId.ToString(CultureInfo.InvariantCulture));
    }

    /// <summary>
    /// Creates a staging folder where the packed addon is assembled, "vpks/{publishedFileId}" with "{publishedFileId}_dir.vpk", its chunks and publish_data.txt.
    /// </summary>
    /// <returns>The staging folder to hand to SetItemContent.</returns>
    public static string Stage(string addonsRoot, string addonName, string gameInfoPath, ulong publishedFileId, string title, DateTimeOffset publishTime, AddonRules? rules = null)
    {
        var addonPath = Path.Combine(addonsRoot, addonName);

        if (!Directory.Exists(addonPath))
        {
            throw new DirectoryNotFoundException($"Addon folder '{addonPath}' does not exist.");
        }

        var stagingPath = GetStagingPath(addonsRoot, publishedFileId);

        // delete past contents and recreate the staging folder
        if (Directory.Exists(stagingPath))
        {
            Directory.Delete(stagingPath, recursive: true);
        }
        Directory.CreateDirectory(stagingPath);

        Pack(addonPath, gameInfoPath, Path.Combine(stagingPath, $"{publishedFileId}_dir.vpk"), rules);

        var publishData = KVObject.Collection();
        publishData.Add("title", title);
        publishData.Add("source_folder", addonName);
        publishData.Add("publish_time", publishTime.ToUnixTimeSeconds());
        publishData.Add("publish_time_readable", publishTime.ToLocalTime().ToString(PublishTimeFormat, CultureInfo.InvariantCulture));

        // create publish_data.txt
        using var stream = File.Create(Path.Combine(stagingPath, PublishDataFileName));
        KVSerializer.Create(KVSerializationFormat.KeyValues1Text).Serialize(stream, publishData, "publish_data");

        return stagingPath;
    }

    /// <summary>
    /// The "source_folder" recorded in a folder's publish_data.txt, or null when there is none.
    /// </summary>
    public static string? ReadPublishedSourceFolder(string directory)
    {
        var path = Path.Combine(directory, PublishDataFileName);

        if (!File.Exists(path))
        {
            return null;
        }

        using var stream = File.OpenRead(path);
        var publishData = KVSerializer.Create(KVSerializationFormat.KeyValues1Text).Deserialize(stream, KVSerializerOptions.DefaultOptions);

        return publishData["source_folder"] is KVObject sourceFolder ? (string)sourceFolder : null;
    }

    /// <summary>
    /// All the files to pack into the addon: what the user's <paramref name="rules"/> and then gameinfo's VpkDirectories allow, without the files the workshop manager skips.
    /// </summary>
    public static List<FileInfo> CollectFiles(string addonPath, string gameInfoPath, AddonRules? rules = null)
    {
        addonPath = Path.TrimEndingDirectorySeparator(Path.GetFullPath(addonPath));

        var directoryRules = LoadVpkDirectories(gameInfoPath);

        if (rules != null)
        {
            // the user's rules go first, so they win over gameinfo's
            directoryRules.InsertRange(0, rules.Rules.Select(rule => new VpkDirectoryRule(rule.Exclude, rule.Pattern)));
        }

        var files = new List<string>();
        CollectFiles(addonPath, addonPath, directoryRules, files);

        return [.. files.Select(file => new FileInfo(file))];
    }

    /// <summary>
    /// Every file under the addon that a rule could pack: all of them but those the workshop manager always leaves out, whatever gameinfo or the user say.
    /// </summary>
    public static List<FileInfo> ListFiles(string addonPath)
    {
        addonPath = Path.TrimEndingDirectorySeparator(Path.GetFullPath(addonPath));

        // no directory rules at all accepts everything, leaving only the hard coded skips
        var files = new List<string>();
        CollectFiles(addonPath, addonPath, [], files);

        return [.. files.Select(file => new FileInfo(file))];
    }

    /// <summary>
    /// Get the addon contents, using <see cref="CollectFiles(string, string, AddonRules)"/> just like <see cref="Pack"/> but without doing any packing.
    /// </summary>
    public static AddonContents GetContents(string addonPath, string gameInfoPath, AddonRules? rules = null)
    {
        return AddonContents.FromFiles(CollectFiles(addonPath, gameInfoPath, rules));
    }

    /// <summary>
    /// Writes <paramref name="outputDirectoryFile"/> (ending in "_dir.vpk") and its numbered vok chunks.
    /// </summary>
    /// <returns>The packed files, relative to the addon root.</returns>
    public static List<string> Pack(string addonPath, string gameInfoPath, string outputDirectoryFile, AddonRules? rules = null)
    {
        addonPath = Path.TrimEndingDirectorySeparator(Path.GetFullPath(addonPath));

        var files = CollectFiles(addonPath, gameInfoPath, rules);

        using var package = new Package();
        package.WriteChunkSize = ChunkSize;

        var totalSize = 0L;

        foreach (var file in files)
        {
            var size = file.Length;

            if (totalSize >= MaxTotalSize || totalSize + size >= MaxTotalSize)
            {
                throw new InvalidOperationException($"VPK: Exceeded CS2 Workshop upload limit of 3.0 GB! Error adding '{file.FullName}'.");
            }

            if (size >= MaxFileSize)
            {
                throw new InvalidOperationException($"VPK: Exceeded single VPK 2.0 GB limit! Error adding '{file.FullName}'.");
            }

            package.AddFile(GetRelativePath(addonPath, file.FullName), File.ReadAllBytes(file.FullName), multiChunk: true);

            totalSize += size;
        }

        package.Write(outputDirectoryFile);

        return [.. files.Select(file => GetRelativePath(addonPath, file.FullName))];
    }

    private static List<VpkDirectoryRule> LoadVpkDirectories(string gameInfoPath)
    {
        using var stream = File.OpenRead(gameInfoPath);
        var gameInfo = KVSerializer.Create(KVSerializationFormat.KeyValues1Text).Deserialize(stream, KVSerializerOptions.DefaultOptions);

        var rules = new List<VpkDirectoryRule>();

        if (gameInfo["AddonConfig"] is not KVObject addonConfig || addonConfig["VpkDirectories"] is not KVObject vpkDirectories)
        {
            return rules;
        }

        foreach (var child in vpkDirectories.Children)
        {
            rules.Add(new VpkDirectoryRule(child.Key.Equals("exclude", StringComparison.OrdinalIgnoreCase), (string)child.Value));
        }

        return rules;
    }

    private static bool IsInVpkDirectories(List<VpkDirectoryRule> rules, string relativePath, bool isDirectory)
    {
        if (rules.Count == 0)
        {
            return true;
        }

        foreach (var rule in rules)
        {
            if (rule.Exclude && relativePath.StartsWith(rule.Prefix, StringComparison.OrdinalIgnoreCase))
            {
                return false;
            }

            if (isDirectory && rule.Prefix.StartsWith(relativePath, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }

            if (relativePath.StartsWith(rule.Prefix, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        return false;
    }

    private static void CollectFiles(string addonPath, string directory, List<VpkDirectoryRule> rules, List<string> files)
    {
        foreach (var path in Directory.EnumerateFileSystemEntries(directory))
        {
            var name = Path.GetFileName(path);

            if (name.StartsWith('.'))
            {
                continue;
            }

            if (SkippedFileNames.Contains(name, StringComparer.OrdinalIgnoreCase))
            {
                continue;
            }

            if (name.StartsWith("tools_thumbnail_cache.", StringComparison.Ordinal))
            {
                continue;
            }

            if (HasBlockedExtension(name))
            {
                continue;
            }

            var isDirectory = Directory.Exists(path);

            if (!IsInVpkDirectories(rules, GetRelativePath(addonPath, path), isDirectory))
            {
                continue;
            }

            if (HasBlockedExtension(path))
            {
                continue;
            }

            if (isDirectory)
            {
                if (!SkippedDirectoryNames.Contains(name, StringComparer.OrdinalIgnoreCase))
                {
                    CollectFiles(addonPath, path, rules, files);
                }

                continue;
            }

            files.Add(path);
        }
    }

    /// <summary>A path under the addon the way the vpk and the rules name it, forward slashes and all.</summary>
    public static string GetRelativePath(string addonPath, string path)
    {
        return Path.GetRelativePath(addonPath, path).Replace('\\', '/');
    }

    private static bool HasBlockedExtension(string path)
    {
        foreach (var extension in BlockedExtensions)
        {
            if (path.Contains(extension, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        return false;
    }
}
