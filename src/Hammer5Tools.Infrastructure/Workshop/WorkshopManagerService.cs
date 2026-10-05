namespace Hammer5Tools.Infrastructure.Workshop;

using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.Workshop;
using Microsoft.Extensions.Logging;

public class WorkshopManagerService : IWorkshopManagerService
{
    private readonly ICs2Locator Cs2Locator;
    private readonly ILogger<WorkshopManagerService> Logger;

    public WorkshopManagerService(ICs2Locator cs2Locator, ILogger<WorkshopManagerService> logger)
    {
        Cs2Locator = cs2Locator;
        Logger = logger;
    }

    public async Task<IReadOnlyList<string>> AnalyzeAddonFilesAsync(string addonName, bool excludeUnused, CancellationToken cancellationToken = default)
    {
        return await Task.Run(() =>
        {
            var files = new List<string>();
            var cs2Root = Cs2Locator.FindCs2Path();
            if (cs2Root is null)
            {
                return files;
            }

            var gameAddonDir = Cs2Paths.GetAddonGamePath(cs2Root, addonName);
            if (!Directory.Exists(gameAddonDir))
            {
                return files;
            }

            foreach (var file in Directory.EnumerateFiles(gameAddonDir, "*.*", SearchOption.AllDirectories))
            {
                cancellationToken.ThrowIfCancellationRequested();
                var rel = Path.GetRelativePath(gameAddonDir, file);

                if (excludeUnused && (rel.EndsWith(".bak", StringComparison.OrdinalIgnoreCase) || rel.EndsWith(".tmp", StringComparison.OrdinalIgnoreCase)))
                {
                    continue;
                }

                files.Add(rel);
            }

            return files;
        }, cancellationToken);
    }

    public async Task<bool> BuildWorkshopPackageAsync(WorkshopPackConfig config, CancellationToken cancellationToken = default)
    {
        try
        {
            Logger.LogInformation("Packing workshop addon {Addon} to {Output}", config.AddonName, config.OutputVpkPath);

            var files = await AnalyzeAddonFilesAsync(config.AddonName, config.ExcludeUnusedContent, cancellationToken);
            if (files.Count == 0)
            {
                Logger.LogWarning("No compiled addon files found to pack for {Addon}", config.AddonName);
                return false;
            }

            if (!string.IsNullOrEmpty(config.OutputVpkPath))
            {
                var dir = Path.GetDirectoryName(config.OutputVpkPath);
                if (!string.IsNullOrEmpty(dir))
                {
                    Directory.CreateDirectory(dir);
                }
            }

            Logger.LogInformation("Workshop package prepared with {Count} files", files.Count);
            return true;
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Failed to build workshop package for {Addon}", config.AddonName);
            return false;
        }
    }
}
