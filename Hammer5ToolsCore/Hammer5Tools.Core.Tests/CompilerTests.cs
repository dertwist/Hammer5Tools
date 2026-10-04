using System.Text.Json;
using Hammer5Tools.Core.IO.Automation;
using Hammer5Tools.Core.IO.Toolchain;

namespace Hammer5Tools.Core.Tests;

public sealed class CompilerTests
{
    [Test]
    public async Task UnicodeLogWindowsDoNotSplitSurrogatePairs()
    {
        Directory.CreateDirectory(CompilerService.Storage);
        var id = Guid.NewGuid().ToString("N");
        var path = Path.Combine(CompilerService.Storage, id + ".log");
        File.WriteAllText(path, "🙂模型");
        try
        {
            using var request = JsonDocument.Parse($$"""{"log_id":"{{id}}","offset":0,"limit":1}""");
            var first = CompilerService.ReadLog(request.RootElement);
            await Assert.That(first["text"]!.GetValue<string>()).IsEqualTo("🙂");
            await Assert.That(first["returned"]!.GetValue<int>()).IsEqualTo(1);
            using var next = JsonDocument.Parse($$"""{"log_id":"{{id}}","offset":1,"limit":2}""");
            await Assert.That(CompilerService.ReadLog(next.RootElement)["text"]!.GetValue<string>()).IsEqualTo("模型");
            using var writing = new StreamWriter(path, append: true) { AutoFlush = true };
            writing.Write(" live");
            await Assert.That(CompilerService.ReadLog(next.RootElement)["text"]!.GetValue<string>()).IsEqualTo("模型");
        }
        finally { File.Delete(path); }
    }

    [Test]
    public async Task BatchUsesOneFileListAndBoundsBothStreamDiagnostics()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(Path.Combine(root, "game", "bin", "win64"));
        File.WriteAllText(Path.Combine(root, "game", "bin", "win64", "resourcecompiler.exe"), "fake");
        try
        {
            var paths = Enumerable.Range(0, 100).Select(index => Path.Combine(root, $"模型 {index}.vmdl")).ToArray();
            foreach (var path in paths) File.WriteAllText(path, "fixture");
            using var request = JsonDocument.Parse(JsonSerializer.Serialize(new { paths = paths.Concat(paths), cs2_path = root, force = true }));
            var calls = 0;
            string? listPath = null;
            int Execute(string executable, IReadOnlyList<string> args, Action<ProcessLine> emit, CancellationToken token)
            {
                calls++;
                listPath = args[1];
                if (args[0] != "-filelist" || args[^1] != "-f" || File.ReadAllLines(listPath).Length != 100)
                    throw new InvalidDataException("Batch arguments or deduplication failed");
                for (var index = 0; index < 2000; index++)
                {
                    emit(new ProcessLine("Warning 模型 " + new string('x', 2000), true));
                    emit(new ProcessLine("Error 模型 " + new string('y', 2000), false));
                }
                return 1;
            }
            var result = CompilerService.Compile(request.RootElement, execute: Execute);
            await Assert.That(calls).IsEqualTo(1);
            await Assert.That(result["total"]!.GetValue<int>()).IsEqualTo(100);
            await Assert.That(result["warning_count"]!.GetValue<int>()).IsEqualTo(2000);
            await Assert.That(result["error_count"]!.GetValue<int>()).IsEqualTo(2000);
            await Assert.That(result["unknown_count"]!.GetValue<int>()).IsEqualTo(100);
            await Assert.That(System.Text.Encoding.UTF8.GetByteCount(result.ToJsonString()) < 16 * 1024).IsTrue();
            await Assert.That(File.Exists(listPath)).IsFalse();
            var logId = result["log_id"]!.GetValue<string>();
            using var logRequest = JsonDocument.Parse($"{{\"log_id\":\"{logId}\",\"limit\":4096}}");
            var log = CompilerService.ReadLog(logRequest.RootElement);
            await Assert.That(log["returned"]!.GetValue<int>()).IsEqualTo(4096);
            await Assert.That(log["truncated"]!.GetValue<bool>()).IsTrue();
            File.Delete(Path.Combine(CompilerService.Storage, logId + ".log"));
            var success = CompilerService.Compile(request.RootElement, execute: (_, _, emit, _) =>
            {
                for (var index = 0; index < 20; index++)
                {
                    emit(new ProcessLine("Warning 模型🙂" + new string('\u0001', 2000), true));
                    emit(new ProcessLine("Error 模型🙂" + new string('\u0001', 2000), false));
                }
                return 0;
            });
            await Assert.That(System.Text.Encoding.UTF8.GetByteCount(success.ToJsonString()) <= 8 * 1024).IsTrue();
            File.Delete(Path.Combine(CompilerService.Storage, success["log_id"]!.GetValue<string>() + ".log"));
            var clean = CompilerService.Compile(request.RootElement, execute: (_, _, emit, _) =>
            {
                emit(new ProcessLine(" OK: 100 compiled, 0 failed, 0 skipped, 0m:01s", false));
                return 0;
            });
            await Assert.That(clean["error_count"]!.GetValue<int>()).IsEqualTo(0);
            File.Delete(Path.Combine(CompilerService.Storage, clean["log_id"]!.GetValue<string>() + ".log"));
        }
        finally
        {
            Directory.Delete(root, true);
        }
    }

    [Test]
    public async Task InvalidBatchDoesNotLaunchAndDryRunDoesNotCreateLogs()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        var asset = Path.Combine(root, "model.vmdl");
        File.WriteAllText(asset, "fixture");
        try
        {
            using var invalid = JsonDocument.Parse(JsonSerializer.Serialize(new { paths = new[] { asset, Path.Combine(root, "missing.vmdl") } }));
            await Assert.That(() => CompilerService.Compile(invalid.RootElement, execute: (_, _, _, _) => throw new InvalidOperationException("launched"))).Throws<FileNotFoundException>();
            using var dry = JsonDocument.Parse(JsonSerializer.Serialize(new { path = asset, dry_run = true }));
            var result = CompilerService.Compile(dry.RootElement);
            await Assert.That(result["total"]!.GetValue<int>()).IsEqualTo(1);
            await Assert.That(result.ContainsKey("log_id")).IsFalse();
        }
        finally
        {
            Directory.Delete(root, true);
        }
    }
}
