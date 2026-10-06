namespace Hammer5Tools.Core.Workshop;

public interface IAssetToolsService
{
    Task<int> MoveAssetAndRewriteReferencesAsync(string addonContentPath, string oldRelativePath, string newRelativePath, CancellationToken cancellationToken = default);

    Task<int> FindBrokenReferencesAsync(string addonContentPath, CancellationToken cancellationToken = default);
}
