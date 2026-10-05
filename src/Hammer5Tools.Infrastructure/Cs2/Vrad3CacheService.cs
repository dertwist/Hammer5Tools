namespace Hammer5Tools.Infrastructure.Cs2;

using System.IO;
using Hammer5Tools.Core.Cs2;
using Microsoft.Extensions.Logging;

/// <summary>
/// Service for finding and clearing VRAD3 light bake cache files.
/// </summary>
public class Vrad3CacheService
{
    private readonly ICs2Locator Cs2Locator;
    private readonly ILogger<Vrad3CacheService>? Logger;

    public Vrad3CacheService(ICs2Locator cs2Locator, ILogger<Vrad3CacheService>? logger = null)
    {
        Cs2Locator = cs2Locator;
        Logger = logger;
    }

    /// <summary>
    /// Discovers all .vrad3 cache files in the active addon or game directories.
    /// </summary>
    public IReadOnlyList<string> FindCacheFiles(string? addonName = null)
    {
        var cs2Path = Cs2Locator.ResolvedCs2Path;
        if (string.IsNullOrWhiteSpace(cs2Path) || !Directory.Exists(cs2Path))
        {
            return [];
        }

        var results = new List<string>();

        if (!string.IsNullOrWhiteSpace(addonName))
        {
            var addonGameDir = Cs2Paths.GetAddonGamePath(cs2Path, addonName);
            if (Directory.Exists(addonGameDir))
            {
                results.AddRange(Directory.EnumerateFiles(addonGameDir, "*.vrad3", SearchOption.AllDirectories));
            }
        }

        var mapsDir = Path.Combine(cs2Path, "game", "csgo", "maps");
        if (Directory.Exists(mapsDir))
        {
            results.AddRange(Directory.EnumerateFiles(mapsDir, "*.vrad3", SearchOption.TopDirectoryOnly));
        }

        return results;
    }

    /// <summary>Removes the named addon's generated _vrad3 cache directory.</summary>
    public void ClearAddonCache(string addonName)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(addonName);
        if (addonName.IndexOfAny(['/', '\\', '"']) >= 0 || addonName is "." or "..")
        {
            throw new ArgumentException("Invalid addon name.", nameof(addonName));
        }
        var root = Cs2Locator.ResolvedCs2Path ?? throw new InvalidOperationException("CS2 path is not resolved.");
        var directory = Path.Combine(Cs2Paths.GetAddonGamePath(root, addonName), "_vrad3");
        if (Directory.Exists(directory)) Directory.Delete(directory, recursive: true);
    }

    /// <summary>
    /// Clears the discovered VRAD3 cache files.
    /// </summary>
    public int ClearCache(string? addonName = null)
    {
        var files = FindCacheFiles(addonName);
        var cleared = 0;

        foreach (var file in files)
        {
            try
            {
                if (File.Exists(file))
                {
                    File.Delete(file);
                    cleared++;
                }
            }
            catch (Exception ex)
            {
                Logger?.LogWarning(ex, "Failed to delete VRAD3 cache file {File}", file);
            }
        }

        Logger?.LogInformation("Cleared {Count} VRAD3 cache files.", cleared);
        return cleared;
    }
}
