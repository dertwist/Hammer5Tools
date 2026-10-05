namespace Hammer5Tools.Core.MapBuilder;

public interface IMapBuilderService
{
    IReadOnlyList<MapBuildJob> Jobs { get; }

    event EventHandler<MapBuildJob>? JobUpdated;

    Task<MapBuildJob> EnqueueBuildAsync(string addonName, string mapName, MapBuildPreset preset, bool clearVrad = true, bool launchAfter = false);

    void CancelJob(string jobId);
}
