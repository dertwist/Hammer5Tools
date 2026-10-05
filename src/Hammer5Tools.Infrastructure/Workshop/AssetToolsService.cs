namespace Hammer5Tools.Infrastructure.Workshop;

using Hammer5Tools.Core.Workshop;
using Microsoft.Extensions.Logging;

public class AssetToolsService : IAssetToolsService
{
    private readonly ILogger<AssetToolsService> Logger;

    private static readonly string[] AssetExtensions = [".vmat", ".vmdl", ".vmap", ".vsndevts", ".vsmart"];

    public AssetToolsService(ILogger<AssetToolsService> logger)
    {
        Logger = logger;
    }

    public async Task<int> MoveAssetAndRewriteReferencesAsync(string addonContentPath, string oldRelativePath, string newRelativePath, CancellationToken cancellationToken = default)
    {
        return await Task.Run(async () =>
        {
            var replacedCount = 0;
            if (!Directory.Exists(addonContentPath))
            {
                return 0;
            }

            // Move the file on disk if it exists
            var sourceFile = Path.Combine(addonContentPath, oldRelativePath);
            var destFile = Path.Combine(addonContentPath, newRelativePath);

            if (File.Exists(sourceFile))
            {
                var destDir = Path.GetDirectoryName(destFile);
                if (!string.IsNullOrEmpty(destDir))
                {
                    Directory.CreateDirectory(destDir);
                }
                File.Move(sourceFile, destFile, overwrite: true);
            }

            var normalizedOld = oldRelativePath.Replace("\\", "/");
            var normalizedNew = newRelativePath.Replace("\\", "/");

            foreach (var ext in AssetExtensions)
            {
                foreach (var file in Directory.EnumerateFiles(addonContentPath, $"*{ext}", SearchOption.AllDirectories))
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    try
                    {
                        var text = await File.ReadAllTextAsync(file, cancellationToken);
                        if (text.Contains(normalizedOld, StringComparison.OrdinalIgnoreCase))
                        {
                            var updated = text.Replace(normalizedOld, normalizedNew, StringComparison.OrdinalIgnoreCase);
                            await File.WriteAllTextAsync(file, updated, cancellationToken);
                            replacedCount++;
                        }
                    }
                    catch (Exception ex)
                    {
                        Logger.LogWarning(ex, "Failed to inspect or rewrite asset in {File}", file);
                    }
                }
            }

            return replacedCount;
        }, cancellationToken);
    }

    public async Task<int> FindBrokenReferencesAsync(string addonContentPath, CancellationToken cancellationToken = default)
    {
        return await Task.Run(() =>
        {
            // Placeholder checking existence of references
            return 0;
        }, cancellationToken);
    }
}
