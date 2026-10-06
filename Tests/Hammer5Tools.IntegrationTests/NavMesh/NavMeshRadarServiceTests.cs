namespace Hammer5Tools.IntegrationTests.NavMesh;

using Hammer5Tools.Core.IO.NavMesh;
using Microsoft.Extensions.Logging.Abstractions;

public class NavMeshRadarServiceTests
{
    [Test]
    public async Task GenerateRadarVdataProducesValidKv3()
    {
        var service = new NavMeshRadarService(NullLogger<NavMeshRadarService>.Instance);
        var vdata = await service.GenerateRadarVdataAsync("de_dust2", -1024, -2048, 1024, 2048);

        await Assert.That(vdata).Contains("de_dust2");
        await Assert.That(vdata).Contains("m_sCompositeMaterial = \"materials/panorama/radar.vmat\"");
        await Assert.That(vdata).Contains("m_flWorldMinX = -1024");
        await Assert.That(vdata).Contains("m_flWorldMaxY = 2048");
    }
}
