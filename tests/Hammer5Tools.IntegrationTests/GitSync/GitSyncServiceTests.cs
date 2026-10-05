namespace Hammer5Tools.IntegrationTests.GitSync;

using Hammer5Tools.Infrastructure.GitSync;
using Microsoft.Extensions.Logging.Abstractions;

public class GitSyncServiceTests
{
    [Test]
    public async Task GetStatusNonExistentDirectoryReturnsNotRepository()
    {
        var service = new GitSyncService(NullLogger<GitSyncService>.Instance);
        var result = await service.GetStatusAsync("/path/that/does/not/exist");

        await Assert.That(result.IsGitRepository).IsFalse();
        await Assert.That(result.HasUncommittedChanges).IsFalse();
    }
}
