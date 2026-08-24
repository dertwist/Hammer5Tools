namespace Hammer5Tools.Core.Tests;

public sealed class CoreApiTests
{
    [Test]
    public async Task ReportsInitialContractVersion()
    {
        await Assert.That(CoreApi.Version).IsEqualTo(new Version(1, 0));
    }
}
