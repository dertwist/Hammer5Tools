using System.Text.Json;
using System.Text.Json.Nodes;
using Hammer5Tools.Core.IO.Automation;

namespace Hammer5Tools.Core.Tests;

public sealed class CompilationJobTests
{
    [Test]
    public async Task RunningJobIsQueryableAndCancellationIsTerminalWithoutSlowTimeouts()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(Path.Combine(root, "game", "bin", "win64"));
        File.WriteAllText(Path.Combine(root, "game", "bin", "win64", "resourcecompiler.exe"), "fake");
        var path = Path.Combine(root, "asset.vmdl");
        File.WriteAllText(path, "fake");
        using var started = new ManualResetEventSlim();
        try
        {
            using var request = JsonDocument.Parse(JsonSerializer.Serialize(new { path, cs2_path = root, background = true }));
            var result = CompilationJobs.Start(request.RootElement, (_, cancellation) =>
            {
                started.Set();
                cancellation.WaitHandle.WaitOne();
                cancellation.ThrowIfCancellationRequested();
                return new JsonObject { ["success"] = true };
            });
            var id = result["job_id"]!.GetValue<string>();
            await Assert.That(started.Wait(TimeSpan.FromSeconds(5))).IsTrue();
            await Assert.That(CompilationJobs.Status(id)["state"]!.GetValue<string>()).IsEqualTo("running");
            var queued = CompilationJobs.Start(request.RootElement, (_, _) => throw new InvalidOperationException("Queued job must not run after cancellation"));
            var queuedId = queued["job_id"]!.GetValue<string>();
            await Assert.That(CompilationJobs.Status(queuedId)["state"]!.GetValue<string>()).IsEqualTo("queued");
            _ = CompilationJobs.Cancel(queuedId);
            _ = CompilationJobs.Cancel(id);
            var timer = System.Diagnostics.Stopwatch.StartNew();
            while (CompilationJobs.Status(id)["state"]!.GetValue<string>() != "cancelled" && timer.Elapsed < TimeSpan.FromSeconds(5))
                await Task.Delay(10);
            await Assert.That(CompilationJobs.Status(id)["state"]!.GetValue<string>()).IsEqualTo("cancelled");
            var persisted = JsonNode.Parse(File.ReadAllText(Path.Combine(CompilerService.Storage, id + ".job.json")))!;
            await Assert.That(persisted["state"]!.GetValue<string>()).IsEqualTo("cancelled");
            File.Delete(Path.Combine(CompilerService.Storage, id + ".job.json"));
            while (CompilationJobs.Status(queuedId)["state"]!.GetValue<string>() != "cancelled" && timer.Elapsed < TimeSpan.FromSeconds(5))
                await Task.Delay(10);
            await Assert.That(CompilationJobs.Status(queuedId)["state"]!.GetValue<string>()).IsEqualTo("cancelled");
            File.Delete(Path.Combine(CompilerService.Storage, queuedId + ".job.json"));
            var failure = CompilationJobs.Start(request.RootElement, (_, _) => new JsonObject { ["success"] = false, ["error"] = "Fixture failure 模型" });
            var failedId = failure["job_id"]!.GetValue<string>();
            timer.Restart();
            while (CompilationJobs.Status(failedId)["state"]!.GetValue<string>() is "queued" or "running" && timer.Elapsed < TimeSpan.FromSeconds(5))
                await Task.Delay(10);
            await Assert.That(CompilationJobs.Status(failedId)["state"]!.GetValue<string>()).IsEqualTo("failed");
            _ = CompilationJobs.Cancel(failedId);
            File.Delete(Path.Combine(CompilerService.Storage, failedId + ".job.json"));
            using var host = System.Diagnostics.Process.GetCurrentProcess();
            var foreignId = Guid.NewGuid().ToString("N");
            var foreignPath = Path.Combine(CompilerService.Storage, foreignId + ".job.json");
            File.WriteAllText(foreignPath, JsonSerializer.Serialize(new { job_id = foreignId, state = "running",
                host_process_id = Environment.ProcessId, host_process_start_utc = host.StartTime.ToUniversalTime().ToString("O") }));
            try
            {
                var foreign = CompilationJobs.Status(foreignId);
                await Assert.That(foreign["state"]!.GetValue<string>()).IsEqualTo("running");
                await Assert.That(foreign["cancellable_here"]!.GetValue<bool>()).IsFalse();
                await Assert.That(() => CompilationJobs.Cancel(foreignId)).Throws<ArgumentException>();
                await Assert.That(JsonNode.Parse(File.ReadAllText(foreignPath))!["state"]!.GetValue<string>()).IsEqualTo("running");
            }
            finally { File.Delete(foreignPath); }
        }
        finally { Directory.Delete(root, true); }
    }
}
