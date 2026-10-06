namespace Hammer5Tools.Core.GitSync;

public interface IGitSyncService
{
    Task<GitStatusResult> GetStatusAsync(string repositoryPath, CancellationToken cancellationToken = default);

    Task<bool> PullAsync(string repositoryPath, CancellationToken cancellationToken = default);

    Task<bool> PushAsync(string repositoryPath, CancellationToken cancellationToken = default);

    Task<bool> CommitAsync(string repositoryPath, string message, CancellationToken cancellationToken = default);
}
