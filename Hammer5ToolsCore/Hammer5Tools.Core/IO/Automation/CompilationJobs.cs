using System.Collections.Concurrent;
using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Hammer5Tools.Core.IO.Automation;

internal static class CompilationJobs
{
    private sealed class Job : IDisposable
    {
        internal readonly object Sync = new();
        internal readonly CancellationTokenSource Cancellation = new();
        internal readonly JsonObject Data;
        internal Job(JsonObject data) => Data = data;
        public void Dispose() => Cancellation.Dispose();
    }

    private static readonly ConcurrentDictionary<string, Job> Jobs = new();
    private static readonly object Initialization = new();
    private static bool Initialized;

    internal static JsonObject Start(JsonElement request, Func<JsonElement, CancellationToken, JsonObject>? compile = null)
    {
        Initialize();
        CleanupExpired();
        var paths = CompilerService.ResolveInputs(request);
        _ = CompilerService.Flag(request, "force");
        if (request.TryGetProperty("timeout_seconds", out var timeout) && timeout.GetInt32() <= 0)
            throw new ArgumentException("timeout_seconds must be positive.");
        var cs2 = request.GetProperty("cs2_path").GetString()!;
        var executable = new Toolchain.ValveToolLocator(Path.Combine(cs2, "game")).ResourceCompiler;
        if (!File.Exists(executable)) throw new FileNotFoundException("resourcecompiler.exe not found", executable);
        var id = Guid.NewGuid().ToString("N");
        using var host = Process.GetCurrentProcess();
        var job = new Job(new JsonObject
        {
            ["job_id"] = id,
            ["state"] = "queued",
            ["total"] = paths.Count,
            ["host_process_id"] = Environment.ProcessId,
            ["host_process_start_utc"] = host.StartTime.ToUniversalTime().ToString("O"),
            ["created_utc"] = DateTimeOffset.UtcNow.ToString("O")
        });
        Jobs[id] = job;
        Persist(job);
        var snapshot = JsonNode.Parse(request.GetRawText())!.AsObject();
        foreach (var key in new List<string> { "path", "pattern", "paths_file" }) snapshot.Remove(key);
        snapshot["paths"] = CompilerService.Strings(paths);
        using var snapshotDocument = JsonDocument.Parse(snapshot.ToJsonString(AutomationJsonContext.Default.Options));
        var copy = snapshotDocument.RootElement.Clone();
        _ = Task.Run(async () =>
        {
            var acquired = false;
            try
            {
                await CompilerService.ExecutionSlot.WaitAsync(job.Cancellation.Token).ConfigureAwait(false);
                acquired = true;
                Update(job, "running");
                var result = compile is not null ? compile(copy, job.Cancellation.Token) : CompilerService.Compile(copy, job.Cancellation.Token,
                    onStarted: process =>
                    {
                        lock (job.Sync)
                        {
                            job.Data["process_id"] = process.Id;
                            job.Data["process_start_utc"] = process.StartTime.ToUniversalTime().ToString("O");
                            Persist(job);
                        }
                    }, logCreated: logId =>
                    {
                        lock (job.Sync)
                        {
                            job.Data["log_id"] = logId;
                            Persist(job);
                        }
                    }, slotAcquired: true);
                lock (job.Sync)
                {
                    job.Data["result"] = result;
                    Update(job, job.Cancellation.IsCancellationRequested ? "cancelled" : result["success"]!.GetValue<bool>() ? "succeeded" : "failed");
                }
            }
            catch (OperationCanceledException)
            {
                Update(job, "cancelled");
            }
            catch (Exception exception)
            {
                lock (job.Sync)
                {
                    job.Data["error"] = exception.Message;
                    Update(job, "failed");
                }
            }
            finally
            {
                if (acquired) CompilerService.ExecutionSlot.Release();
                job.Dispose();
            }
        });
        return Status(id);
    }

    internal static JsonObject Status(string id)
    {
        Initialize();
        if (!Jobs.ContainsKey(id) && Guid.TryParseExact(id, "N", out _))
        {
            var path = Path.Combine(CompilerService.Storage, id + ".job.json");
            if (File.Exists(path))
            {
                var data = ReadMetadata(path);
                if (data["state"]!.GetValue<string>() is "queued" or "running" && HostIsAlive(data))
                {
                    data["cancellable_here"] = false;
                    data["recovery_note"] = "Job belongs to another live host; cancellation must use its original server.";
                    return data;
                }
                var recovered = new Job(data);
                if (data["state"]!.GetValue<string>() is "queued" or "running") Interrupt(recovered);
                if (!Jobs.TryAdd(id, recovered)) recovered.Dispose();
            }
        }
        var job = Find(id);
        lock (job.Sync) return (JsonObject)job.Data.DeepClone();
    }

    internal static JsonObject Cancel(string id)
    {
        var job = Find(id);
        lock (job.Sync)
        {
            if (job.Data["state"]!.GetValue<string>() is "queued" or "running") job.Cancellation.Cancel();
        }
        return Status(id);
    }

    private static Job Find(string id)
    {
        Initialize();
        if (!Guid.TryParseExact(id, "N", out _) || !Jobs.TryGetValue(id, out var job)) throw new ArgumentException("Unknown or not locally owned job_id; query status for persisted jobs.");
        return job;
    }

    private static void Update(Job job, string state)
    {
        lock (job.Sync)
        {
            job.Data["state"] = state;
            job.Data["updated_utc"] = DateTimeOffset.UtcNow.ToString("O");
            Persist(job);
        }
    }

    private static void Persist(Job job)
    {
        Directory.CreateDirectory(CompilerService.Storage);
        var path = Path.Combine(CompilerService.Storage, job.Data["job_id"]!.GetValue<string>() + ".job.json");
        File.WriteAllText(path + ".tmp", job.Data.ToJsonString(AutomationJsonContext.Default.Options));
        if (File.Exists(path)) File.Replace(path + ".tmp", path, null);
        else File.Move(path + ".tmp", path);
    }

    private static void Initialize()
    {
        lock (Initialization)
        {
            if (Initialized) return;
            Directory.CreateDirectory(CompilerService.Storage);
            foreach (var path in Directory.EnumerateFiles(CompilerService.Storage, "*.job.json"))
            {
                try
                {
                    var data = ReadMetadata(path);
                    var id = data["job_id"]!.GetValue<string>();
                    var state = data["state"]!.GetValue<string>();
                    if (state is "queued" or "running" && HostIsAlive(data)) continue;
                    var job = new Job(data);
                    if (state is "queued" or "running")
                    {
                        Interrupt(job);
                    }
                    Jobs[id] = job;
                }
                catch (Exception exception) when (exception is JsonException or InvalidOperationException or IOException or UnauthorizedAccessException)
                {
                    // A damaged metadata file is retained for inspection and never replayed.
                }
            }
            CleanupExpired();
            Initialized = true;
        }
    }

    private static JsonObject ReadMetadata(string path)
    {
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        var data = JsonNode.Parse(stream)?.AsObject() ?? throw new JsonException("Missing job object.");
        var id = data["job_id"]?.GetValue<string>() ?? throw new JsonException("Missing job_id.");
        if (!Guid.TryParseExact(id, "N", out _) || Path.GetFileName(path) != id + ".job.json") throw new JsonException("Invalid job identity.");
        var state = data["state"]?.GetValue<string>() ?? throw new JsonException("Missing state.");
        if (state is not ("queued" or "running" or "succeeded" or "failed" or "cancelled" or "interrupted")) throw new JsonException("Invalid state.");
        return data;
    }

    private static bool HostIsAlive(JsonObject data)
    {
        if (data["host_process_id"] is null || data["host_process_start_utc"] is null) return false;
        try
        {
            using var host = Process.GetProcessById(data["host_process_id"]!.GetValue<int>());
            return !host.HasExited && host.StartTime.ToUniversalTime().ToString("O") == data["host_process_start_utc"]!.GetValue<string>();
        }
        catch (ArgumentException)
        {
            return false;
        }
        catch (InvalidOperationException)
        {
            return false;
        }
        catch (System.ComponentModel.Win32Exception)
        {
            return true;
        }
    }

    private static void Interrupt(Job job)
    {
        job.Data["possible_surviving_process"] = job.Data.ContainsKey("process_id");
        job.Data["recovery_note"] = "Host exited; process may survive. No stale PID is signalled or restarted.";
        Update(job, "interrupted");
    }

    private static void CleanupExpired()
    {
        lock (Initialization)
        {
            foreach (var (id, job) in Jobs)
            {
                lock (job.Sync)
                {
                    if (job.Data["state"]!.GetValue<string>() is "queued" or "running") continue;
                    var path = Path.Combine(CompilerService.Storage, id + ".job.json");
                    if (!File.Exists(path) || File.GetLastWriteTimeUtc(path) >= DateTime.UtcNow.AddDays(-7)) continue;
                    File.Delete(path);
                    Jobs.TryRemove(id, out _);
                    job.Dispose();
                }
            }
        }
    }
}
