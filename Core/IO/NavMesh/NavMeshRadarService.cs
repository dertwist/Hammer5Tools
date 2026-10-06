namespace Hammer5Tools.Core.IO.NavMesh;

using System.Globalization;
using System.Text;
using Hammer5Tools.Core.NavMesh;
using Microsoft.Extensions.Logging;

public class NavMeshRadarService : INavMeshRadarService
{
    private readonly ILogger<NavMeshRadarService> Logger;

    public NavMeshRadarService(ILogger<NavMeshRadarService> logger)
    {
        Logger = logger;
    }

    public async Task<bool> GenerateRadarAsync(NavMeshRadarConfig config, CancellationToken cancellationToken = default)
    {
        try
        {
            Logger.LogInformation("Generating NavMesh Radar for map {Map} in addon {Addon}", config.MapName, config.AddonName);

            // Generate radar vdata KV3
            var vdata = await GenerateRadarVdataAsync(config.MapName, -2048, -2048, 2048, 2048);

            if (!string.IsNullOrEmpty(config.OutputPath))
            {
                var dir = Path.GetDirectoryName(config.OutputPath);
                if (!string.IsNullOrEmpty(dir))
                {
                    Directory.CreateDirectory(dir);
                }

                var vdataPath = Path.ChangeExtension(config.OutputPath, ".vdata");
                await File.WriteAllTextAsync(vdataPath, vdata, cancellationToken);
            }

            return true;
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Failed to generate radar for {Map}", config.MapName);
            return false;
        }
    }

    public Task<string> GenerateRadarVdataAsync(string mapName, float worldMinX, float worldMinY, float worldMaxX, float worldMaxY)
    {
        var sb = new StringBuilder();
        sb.AppendLine("<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->");
        sb.AppendLine("{");
        sb.AppendLine($"\t\"{mapName}\" =");
        sb.AppendLine("\t{");
        sb.AppendLine("\t\tm_sCompositeMaterial = \"materials/panorama/radar.vmat\"");
        sb.AppendLine(string.Format(CultureInfo.InvariantCulture, "\t\tm_flWorldMinX = {0}", worldMinX));
        sb.AppendLine(string.Format(CultureInfo.InvariantCulture, "\t\tm_flWorldMinY = {0}", worldMinY));
        sb.AppendLine(string.Format(CultureInfo.InvariantCulture, "\t\tm_flWorldMaxX = {0}", worldMaxX));
        sb.AppendLine(string.Format(CultureInfo.InvariantCulture, "\t\tm_flWorldMaxY = {0}", worldMaxY));
        sb.AppendLine("\t}");
        sb.AppendLine("}");

        return Task.FromResult(sb.ToString());
    }
}
