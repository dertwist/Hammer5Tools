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

    private readonly Lock OutputLock = new();
    private readonly List<MapBuildOutput> Logs = [];

    /// <summary>The compiler options captured when this job was queued.</summary>
    public MapBuildOptions? Options { get; set; }

    /// <summary>A thread-safe snapshot of the job output.</summary>
    public IReadOnlyList<string> OutputLogs
    {
        get
        {
            lock (OutputLock)
            {
                return Logs.Select(line => line.Text).ToArray();
            }
        }
    }

    /// <summary>A timestamped snapshot for live output and history presentation.</summary>
    public IReadOnlyList<MapBuildOutput> Output
    {
        get
        {
            lock (OutputLock)
            {
                return Logs.ToArray();
            }
        }
    }

    /// <summary>Appends output from a compiler worker.</summary>
    public void AppendOutput(string line)
    {
        lock (OutputLock)
        {
            Logs.Add(new MapBuildOutput(DateTimeOffset.UtcNow, line));
        }
    }
}

/// <summary>A compiler or build-service output line with its original recording time.</summary>
public sealed record MapBuildOutput(DateTimeOffset RecordedAt, string Text);
