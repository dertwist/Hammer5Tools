namespace Hammer5Tools.Core.NavMesh;

public class NavMeshRadarConfig
{
    public string AddonName { get; set; } = string.Empty;

    public string MapName { get; set; } = string.Empty;

    public int Resolution { get; set; } = 1024;

    public float HeightMin { get; set; } = -500f;

    public float HeightMax { get; set; } = 1000f;

    public bool CollapseNgons { get; set; } = true;

    public string OutputPath { get; set; } = string.Empty;
}
