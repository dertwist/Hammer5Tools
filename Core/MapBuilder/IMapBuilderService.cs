namespace Hammer5Tools.Core.MapBuilder;

public interface IMapBuilderService
{
    IReadOnlyList<MapBuildJob> Jobs { get; }

    event EventHandler<MapBuildJob>? JobUpdated;

    Task<MapBuildJob> EnqueueBuildAsync(string addonName, string mapName, MapBuildPreset preset, bool clearVrad = true, bool launchAfter = false);

    /// <summary>Queues a map build using a snapshot of editable compiler settings.</summary>
    Task<MapBuildJob> EnqueueBuildAsync(string addonName, string mapName, MapBuildOptions options);

    /// <summary>Runs a compiled map without compiling it again.</summary>
    Task RunMapAsync(string addonName, string mapName, bool buildCubemaps = false, CancellationToken ct = default);

    void CancelJob(string jobId);
}
