using System.Globalization;
using System.IO;
using System.Linq;

namespace CS2WorkshopManager;

/// <summary>
/// The asset types an addon upload is made of and how much space each takes, the way the original workshop manager content bar shows them.
/// </summary>
public sealed class AddonContents
{
    /// <summary>The workshop manager keeps this many asset types and folds the smaller ones into <see cref="VariousLabel"/>.</summary>
    public const int MaxAssetTypes = 10;

    public const string VariousLabel = "Various";

    public readonly record struct AssetType(string Label, int FileCount, long Size);

    private AddonContents(IReadOnlyList<AssetType> assetTypes, int fileCount, long totalSize)
    {
        AssetTypes = assetTypes;
        FileCount = fileCount;
        TotalSize = totalSize;
    }

    /// <summary>Biggest first, the order the workshop manager keeps them in.</summary>
    public IReadOnlyList<AssetType> AssetTypes { get; }

    public int FileCount { get; }

    public long TotalSize { get; }

    /// <summary>Whether the workshop manager would refuse to upload this much.</summary>
    public bool ExceedsUploadLimit => TotalSize >= AddonPackager.MaxTotalSize;

    /// <summary>The line the workshop manager shows under the bar, "717 Files. 189.14 MB Total."</summary>
    public string Summary => string.Create(CultureInfo.InvariantCulture, $"{FileCount} Files. {FormatSize(TotalSize)} Total.");

    public static AddonContents FromFiles(IEnumerable<FileInfo> files)
    {
        ArgumentNullException.ThrowIfNull(files);

        var assetTypes = new Dictionary<string, AssetType>(StringComparer.OrdinalIgnoreCase);
        var fileCount = 0;
        var totalSize = 0L;

        foreach (var file in files)
        {
            var extension = file.Extension.TrimStart('.');
            var assetType = assetTypes.TryGetValue(extension, out var existing) ? existing : new AssetType(extension, 0, 0);

            assetTypes[extension] = assetType with { FileCount = assetType.FileCount + 1, Size = assetType.Size + file.Length };
            fileCount++;
            totalSize += file.Length;
        }

        var sorted = assetTypes.Values.OrderByDescending(assetType => assetType.Size).ToList();

        if (sorted.Count > MaxAssetTypes)
        {
            var various = new AssetType(VariousLabel, sorted.Skip(MaxAssetTypes - 1).Sum(assetType => assetType.FileCount), sorted.Skip(MaxAssetTypes - 1).Sum(assetType => assetType.Size));

            sorted.RemoveRange(MaxAssetTypes - 1, sorted.Count - (MaxAssetTypes - 1));
            sorted.Add(various);
        }

        sorted.RemoveAll(assetType => assetType.FileCount == 0 || assetType.Size == 0);

        return new AddonContents(sorted, fileCount, totalSize);
    }

    /// <summary>The asset type's share of the total size, 0 to 1.</summary>
    public double Share(AssetType assetType)
    {
        return TotalSize <= 0 ? 0 : Math.Clamp((double)assetType.Size / TotalSize, 0, 1);
    }

    /// <summary>What the workshop manager says about an asset type under the pointer, "[vtex_c]: 12 Files. 30.00 MB Total. 15.23%."</summary>
    public string Describe(AssetType assetType)
    {
        return string.Create(CultureInfo.InvariantCulture, $"[{assetType.Label}]: {assetType.FileCount} Files. {FormatSize(assetType.Size)} Total. {Share(assetType) * 100:F2}%.");
    }

    /// <summary>Formats a size the way the workshop manager does, "189.14 MB", in units of 1024.</summary>
    public static string FormatSize(long bytes)
    {
        const double Kilo = 1024;

        double value = bytes;
        string unit;

        if (value > Kilo * Kilo * Kilo)
        {
            value /= Kilo * Kilo * Kilo;
            unit = "GB";
        }
        else if (value > Kilo * Kilo)
        {
            value /= Kilo * Kilo;
            unit = "MB";
        }
        else if (value > Kilo)
        {
            value /= Kilo;
            unit = "KB";
        }
        else
        {
            unit = "bytes";
        }

        return string.Create(CultureInfo.InvariantCulture, $"{value:N2} {unit}");
    }
}
