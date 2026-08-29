namespace Hammer5Tools.Core.Tests;

public sealed class CoreApiTests
{
    [Test]
    public async Task ReportsCurrentContractVersion()
    {
        await Assert.That(CoreApi.Version).IsEqualTo(new Version(2, 0));
    }

    [Test]
    public async Task ProbesThePublicContract()
    {
        var result = CoreApi.Probe();

        await Assert.That(result.IsSuccess).IsTrue();
        await Assert.That(result.Value).IsEqualTo(new Version(2, 0));
        await Assert.That(result.Diagnostics).IsEmpty();
    }
}
