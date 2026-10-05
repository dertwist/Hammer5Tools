namespace Hammer5Tools.Infrastructure.MapBuilder;

using System.Collections.Concurrent;
using Hammer5Tools.Core.Commands;
using Hammer5Tools.Core.Compiler;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.MapBuilder;
using Hammer5Tools.Infrastructure.Cs2;
using Microsoft.Extensions.Logging;

public sealed class MapBuilderService : IMapBuilderService, IDisposable
{
    private readonly IResourceCompiler ResourceCompiler;
    private readonly Vrad3CacheService Vrad3CacheService;
    private readonly ICommandService CommandService;
    private readonly ICs2Locator Cs2Locator;
    private readonly ILogger<MapBuilderService> Logger;

    private readonly SemaphoreSlim BuildGate = new(1);
    private readonly ConcurrentDictionary<string, Task> Workers = new();

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

    public Task<MapBuildJob> EnqueueBuildAsync(string addonName, string mapName, MapBuildPreset preset, bool clearVrad = true, bool launchAfter = false)
    {
        return EnqueueBuildAsync(addonName, mapName, preset, clearVrad, launchAfter, null);
    }

    public Task<MapBuildJob> EnqueueBuildAsync(string addonName, string mapName, MapBuildOptions options)
    {
        var snapshot = options with { };
        snapshot.ToArguments(Environment.ProcessorCount);
        return EnqueueBuildAsync(addonName, mapName, MapBuildPreset.Standard, snapshot.ClearVradCache, snapshot.LaunchAfterBuild, snapshot);
    }

    private Task<MapBuildJob> EnqueueBuildAsync(string addonName, string mapName, MapBuildPreset preset, bool clearVrad, bool launchAfter, MapBuildOptions? options)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(addonName);
        ArgumentException.ThrowIfNullOrWhiteSpace(mapName);
        if (addonName.IndexOfAny(['/', '\\', '"', '\r', '\n']) >= 0 || addonName is "." or ".."
            || mapName.IndexOfAny(['"', ';', '\r', '\n']) >= 0)
        {
            throw new ArgumentException("Invalid addon or map name.");
        }

        var job = new MapBuildJob
        {
            AddonName = addonName,
            MapName = mapName,
            Preset = preset,
            ClearVradCache = clearVrad,
            LaunchAfterBuild = launchAfter,
            StartedAt = DateTime.UtcNow,
            Status = "Queued",
            Options = options,
        };

        lock (JobsList)
        {
            JobsList.Add(job);
        }

        var cts = new CancellationTokenSource();
        RunningTokens[job.Id] = cts;
        JobUpdated?.Invoke(this, job);

        var worker = Task.Run(async () =>
        {
            var acquired = false;
            try
            {
                await BuildGate.WaitAsync(cts.Token);
                acquired = true;
                job.StartedAt = DateTime.UtcNow;
                job.Status = "Building";
                JobUpdated?.Invoke(this, job);

                if (job.ClearVradCache)
                {
                    if (job.Options is null)
                    {
                        Vrad3CacheService.ClearCache(job.AddonName);
                    }
                    else
                    {
                        Vrad3CacheService.ClearAddonCache(job.AddonName);
                    }
                    job.AppendOutput("VRAD3 cache cleared.");
                }

                var cs2Root = Cs2Locator.FindCs2Path();
                if (cs2Root is null)
                {
                    job.Status = "Failed";
                    job.AppendOutput("CS2 installation not found.");
                    job.Success = false;
                    job.FinishedAt = DateTime.UtcNow;
                    JobUpdated?.Invoke(this, job);
                    return;
                }

                var mapsRoot = Path.GetFullPath(Path.Combine(Cs2Paths.GetContentAddonsPath(cs2Root), job.AddonName, "maps"));
                var input = job.MapName.EndsWith(".vmap", StringComparison.OrdinalIgnoreCase) ? job.MapName : $"{job.MapName}.vmap";
                var vmapPath = Path.GetFullPath(Path.Combine(mapsRoot, input));
                var comparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
                if (!vmapPath.StartsWith(mapsRoot + Path.DirectorySeparatorChar, comparison) || !File.Exists(vmapPath))
                {
                    throw new FileNotFoundException("Select an existing VMAP inside the addon's maps folder.", vmapPath);
                }

                var extraArgs = job.Options?.ToArguments(Environment.ProcessorCount) ?? (job.Preset switch
                {
                    MapBuildPreset.Fast => "-threads 0 -vrad -fast",
                    MapBuildPreset.Final => "-threads 0 -vrad -compress",
                    _ => "-threads 0 -vrad"
                });

                job.AppendOutput($"Starting compilation: {vmapPath}");
                job.AppendOutput($"Arguments: {extraArgs}");
                var outputCount = job.OutputLogs.Count;
                var compileResult = await ResourceCompiler.CompileAssetAsync(vmapPath, job.AddonName, extraArgs, line =>
                {
                    job.AppendOutput(line);
                    JobUpdated?.Invoke(this, job);
                }, cts.Token);
                job.Success = compileResult.Success;
                job.Status = compileResult.Success ? "Finished" : "Failed";
                if (job.OutputLogs.Count == outputCount)
                {
                    foreach (var line in (compileResult.StandardOutput + "\n" + compileResult.StandardError).Split(LineSeparators, StringSplitOptions.RemoveEmptyEntries))
                    {
                        job.AppendOutput(line);
                    }
                }

                if (job.Success && (job.LaunchAfterBuild || job.Options?.BuildCubemaps == true))
                {
                    job.Status = job.Options?.BuildCubemaps == true ? "Cubemaps" : "Running";
                    JobUpdated?.Invoke(this, job);
                    try
                    {
                        await RunMapAsync(job.AddonName, job.MapName, job.Options?.BuildCubemaps == true, cts.Token);
                        job.AppendOutput($"Dispatched: map {job.MapName}");
                    }
                    catch (InvalidOperationException ex)
                    {
                        job.AppendOutput($"Warning: compile completed, but the map could not be run: {ex.Message}");
                    }
                    job.Status = "Finished";
                }
            }
            catch (OperationCanceledException)
            {
                job.Status = "Cancelled";
                job.AppendOutput("Job cancelled by user.");
            }
            catch (Exception ex)
            {
                job.Status = "Error";
                job.AppendOutput($"Exception: {ex.Message}");
                Logger.LogError(ex, "Error building map {Map}", job.MapName);
            }
            finally
            {
                job.FinishedAt = DateTime.UtcNow;
                if (job.Options?.SaveBuildLogs == true && Cs2Locator.ResolvedCs2Path is { } root)
                {
                    try
                    {
                        var directory = Path.Combine(Cs2Paths.GetContentAddonsPath(root), job.AddonName, ".hammer5tools", "build_logs");
                        Directory.CreateDirectory(directory);
                        await File.WriteAllLinesAsync(Path.Combine(directory, $"{job.Id}.log"), job.OutputLogs);
                    }
                    catch (Exception ex)
                    {
                        job.AppendOutput($"Could not save build log: {ex.Message}");
                        Logger.LogWarning(ex, "Could not save map build log");
                    }
                }
                RunningTokens.TryRemove(job.Id, out _);
                lock (cts)
                {
                    cts.Dispose();
                }
                if (acquired) BuildGate.Release();
                JobUpdated?.Invoke(this, job);
            }
        });

        Workers[job.Id] = worker;
        _ = worker.ContinueWith(_ => Workers.TryRemove(job.Id, out var completed),
            CancellationToken.None, TaskContinuationOptions.ExecuteSynchronously, TaskScheduler.Default);
        return Task.FromResult(job);
    }

    public async Task RunMapAsync(string addonName, string mapName, bool buildCubemaps = false, CancellationToken ct = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(mapName);
        if (mapName.IndexOfAny(['"', ';', '\r', '\n']) >= 0)
        {
            throw new ArgumentException("Invalid map name.", nameof(mapName));
        }
        var root = Cs2Locator.FindCs2Path() ?? throw new InvalidOperationException("CS2 installation not found.");
        var mapsRoot = Path.GetFullPath(Path.Combine(Cs2Paths.GetContentAddonsPath(root), addonName, "maps"));
        var path = Path.GetFullPath(Path.Combine(mapsRoot, mapName.EndsWith(".vmap", StringComparison.OrdinalIgnoreCase) ? mapName : $"{mapName}.vmap"));
        var comparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
        if (!path.StartsWith(mapsRoot + Path.DirectorySeparatorChar, comparison))
        {
            throw new ArgumentException("Select a map inside the addon's maps folder.", nameof(mapName));
        }
        var relativeName = Path.GetRelativePath(mapsRoot, path)[..^5].Replace('\\', '/');
        var command = $"map_workshop \"{addonName}\" \"{relativeName}\"";
        if (buildCubemaps)
        {
            await SendAndWaitAsync(command, "Host activate: Loading", TimeSpan.FromMinutes(5), ct);
            await Task.Delay(TimeSpan.FromSeconds(5), ct);
            await SendAndWaitAsync("buildcubemaps", "Re-loading map", TimeSpan.FromMinutes(10), ct);
        }
        else if (!await CommandService.SendCommandAsync(command, ct))
        {
            throw new InvalidOperationException("CS2 command pipe is not connected. Start Workshop Tools before running a map.");
        }
    }

    private async Task SendAndWaitAsync(string command, string sentinel, TimeSpan timeout, CancellationToken ct)
    {
        var completed = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        void Observe(object? sender, string line)
        {
            if (line.Contains(sentinel, StringComparison.OrdinalIgnoreCase)) completed.TrySetResult();
        }
        CommandService.OutputLineReceived += Observe;
        try
        {
            if (!await CommandService.SendCommandAsync(command, ct))
            {
                throw new InvalidOperationException("CS2 command pipe is not connected.");
            }
            await completed.Task.WaitAsync(timeout, ct);
        }
        catch (TimeoutException ex)
        {
            throw new InvalidOperationException($"Timed out waiting for CS2 after '{command}'.", ex);
        }
        finally
        {
            CommandService.OutputLineReceived -= Observe;
        }
    }

    public void Dispose()
    {
        foreach (var id in RunningTokens.Keys)
        {
            CancelJob(id);
        }
        Task.WaitAll(Workers.Values.ToArray());
        BuildGate.Dispose();
    }

    public void CancelJob(string jobId)
    {
        if (RunningTokens.TryGetValue(jobId, out var cts))
        {
            lock (cts)
            {
                try
                {
                    cts.Cancel();
                }
                catch (ObjectDisposedException)
                {
                    // A completed worker may have removed this token after the lookup.
                }
            }
        }
    }
}
