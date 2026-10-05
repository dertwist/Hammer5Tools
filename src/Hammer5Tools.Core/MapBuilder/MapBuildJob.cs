namespace Hammer5Tools.Core.MapBuilder;

public class MapBuildJob
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");

    public string MapName { get; set; } = string.Empty;

    public string AddonName { get; set; } = string.Empty;

    public MapBuildPreset Preset { get; set; } = MapBuildPreset.Standard;

    public bool ClearVradCache { get; set; } = true;

    public bool LaunchAfterBuild { get; set; }

    public string Status { get; set; } = "Pending";

    public bool Success { get; set; }

    public DateTime StartedAt { get; set; }

    public DateTime? FinishedAt { get; set; }

    public List<string> OutputLogs { get; } = [];
}
