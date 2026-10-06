namespace Hammer5Tools.Core.Tests;

public class CoreSanityTest
{
    [Test]
    public async Task CoreBootstrapWorks()
    {
        var value = 1;
        await Assert.That(value).IsEqualTo(1);
    }
}
