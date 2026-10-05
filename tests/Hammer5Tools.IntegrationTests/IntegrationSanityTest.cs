namespace Hammer5Tools.IntegrationTests;

public class IntegrationSanityTest
{
    [Test]
    public async Task IntegrationBootstrapWorks()
    {
        var value = 1;
        await Assert.That(value).IsEqualTo(1);
    }
}
