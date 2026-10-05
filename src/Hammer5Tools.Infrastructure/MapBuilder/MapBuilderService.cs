namespace Hammer5Tools.Infrastructure.MapBuilder;

using System.Collections.Concurrent;
using Hammer5Tools.Core.Commands;
using Hammer5Tools.Core.Compiler;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.MapBuilder;
using Hammer5Tools.Infrastructure.Cs2;
using Microsoft.Extensions.Logging;

public class MapBuilderService : IMapBuilderService
{
    private readonly IResourceCompiler ResourceCompiler;
    private readonly Vrad3CacheService Vrad3CacheService;
    private readonly ICommandService CommandService;
    private readonly ICs2Locator Cs2Locator;
    private readonly ILogger<MapBuilderService> Logger;

    private static readonly char[] LineSeparators = ['\r', '\n'];

    private readonly List<MapBuildJob> JobsList = [];
    private readonly ConcurrentDictionary<string, CancellationTokenSource> RunningTokens = new();

    public IReadOnlyList<MapBuildJob> Jobs
    {
        get
        {
            lock (JobsList)
            {
                return [.. JobsList];
            }
        }
    }

    public event EventHandler<MapBuildJob>? JobUpdated;

    public MapBuilderService(
        IResourceCompiler resourceCompiler,
        Vrad3CacheService vrad3CacheService,
        ICommandService commandService,
        ICs2Locator cs2Locator,
        ILogger<MapBuilderService> logger)
    {
        ResourceCompiler = resourceCompiler;
        Vrad3CacheService = vrad3CacheService;
        CommandService = commandService;
        Cs2Locator = cs2Locator;
        Logger = logger;
    }

    public async Task<MapBuildJob> EnqueueBuildAsync(string addonName, string mapName, MapBuildPreset preset, bool clearVrad = true, bool launchAfter = false)
    {
        var job = new MapBuildJob
        {
            AddonName = addonName,
            MapName = mapName,
            Preset = preset,
            ClearVradCache = clearVrad,
            LaunchAfterBuild = launchAfter,
            StartedAt = DateTime.UtcNow,
            Status = "Queued",
        };

        lock (JobsList)
        {
            JobsList.Add(job);
        }

        JobUpdated?.Invoke(this, job);

        var cts = new CancellationTokenSource();
        RunningTokens[job.Id] = cts;

        _ = Task.Run(async () =>
        {
            try
            {
                job.Status = "Building";
                JobUpdated?.Invoke(this, job);

                if (job.ClearVradCache)
                {
                    Vrad3CacheService.ClearCache(job.AddonName);
                    job.OutputLogs.Add("VRAD3 cache cleared.");
                }

                var cs2Root = Cs2Locator.FindCs2Path();
                if (cs2Root is null)
                {
                    job.Status = "Failed";
                    job.OutputLogs.Add("CS2 installation not found.");
                    job.Success = false;
                    job.FinishedAt = DateTime.UtcNow;
                    JobUpdated?.Invoke(this, job);
                    return;
                }

                var vmapPath = Path.Combine(Cs2Paths.GetContentAddonsPath(cs2Root), job.AddonName, "maps", $"{job.MapName}.vmap");
                var extraArgs = job.Preset switch
                {
                    MapBuildPreset.Fast => "-threads 0 -vrad -fast",
                    MapBuildPreset.Final => "-threads 0 -vrad -compress",
                    _ => "-threads 0 -vrad"
                };

                var compileResult = await ResourceCompiler.CompileAssetAsync(vmapPath, addonName: job.AddonName, additionalArguments: extraArgs, ct: cts.Token);
                job.Success = compileResult.Success;
                job.Status = compileResult.Success ? "Finished" : "Failed";
                var lines = compileResult.StandardOutput.Split(LineSeparators, StringSplitOptions.RemoveEmptyEntries);
                job.OutputLogs.AddRange(lines);
                job.OutputLogs.AddRange(compileResult.StandardError.Split(LineSeparators, StringSplitOptions.RemoveEmptyEntries));

                if (job.Success && job.LaunchAfterBuild)
                {
                    await CommandService.SendCommandAsync($"map {job.MapName}", cts.Token);
                    job.OutputLogs.Add($"Dispatched: map {job.MapName}");
                }
            }
            catch (OperationCanceledException)
            {
                job.Status = "Cancelled";
                job.OutputLogs.Add("Job cancelled by user.");
            }
            catch (Exception ex)
            {
                job.Status = "Error";
                job.OutputLogs.Add($"Exception: {ex.Message}");
                Logger.LogError(ex, "Error building map {Map}", job.MapName);
            }
            finally
            {
                job.FinishedAt = DateTime.UtcNow;
                RunningTokens.TryRemove(job.Id, out _);
                JobUpdated?.Invoke(this, job);
            }
        });

        return await Task.FromResult(job);
    }

    public void CancelJob(string jobId)
    {
        if (RunningTokens.TryGetValue(jobId, out var cts))
        {
            cts.Cancel();
        }
    }
}
