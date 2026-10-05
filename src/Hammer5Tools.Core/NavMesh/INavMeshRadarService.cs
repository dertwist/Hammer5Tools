namespace Hammer5Tools.Core.NavMesh;

public interface INavMeshRadarService
{
    Task<bool> GenerateRadarAsync(NavMeshRadarConfig config, CancellationToken cancellationToken = default);

    Task<string> GenerateRadarVdataAsync(string mapName, float worldMinX, float worldMinY, float worldMaxX, float worldMaxY);
}
