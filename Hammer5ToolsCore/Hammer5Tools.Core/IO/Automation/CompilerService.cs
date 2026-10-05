using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Hammer5Tools.Core.IO.Toolchain;

namespace Hammer5Tools.Core.IO.Automation;

internal static class CompilerService
{
    private static readonly string[] InputKeys = ["paths", "path", "pattern", "paths_file"];
    // ponytail: one compiler slot across foreground/background calls until output scopes are verified.
    internal static readonly SemaphoreSlim ExecutionSlot = new(1);
    internal static readonly string Storage = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Hammer5Tools", "automation");

    internal static JsonObject Compile(JsonElement request, CancellationToken cancellation = default,
        Func<string, IReadOnlyList<string>, Action<ProcessLine>, CancellationToken, int>? execute = null,
        Action<Process>? onStarted = null, Action<string>? logCreated = null, bool slotAcquired = false)
    {
        if (slotAcquired || Flag(request, "dry_run")) return CompileCore(request, cancellation, execute, onStarted, logCreated);
        ExecutionSlot.Wait(cancellation);
        try
        {
            return CompileCore(request, cancellation, execute, onStarted, logCreated);
        }
        finally
        {
            ExecutionSlot.Release();
        }
    }

    private static JsonObject CompileCore(JsonElement request, CancellationToken cancellation,
        Func<string, IReadOnlyList<string>, Action<ProcessLine>, CancellationToken, int>? execute,
        Action<Process>? onStarted, Action<string>? logCreated)
    {
        var paths = ResolveInputs(request);
        var timeout = request.TryGetProperty("timeout_seconds", out var deadline) ? deadline.GetInt32() : 120;
        if (timeout <= 0)
        {
            throw new ArgumentException("timeout_seconds must be positive.");
        }
        if (Flag(request, "dry_run"))
        {
            return new JsonObject { ["dry_run"] = true, ["total"] = paths.Count, ["paths"] = Strings(paths.Take(50)), ["truncated"] = paths.Count > 50 };
        }
        var cs2 = request.GetProperty("cs2_path").GetString()!;
        var executable = new ValveToolLocator(Path.Combine(cs2, "game")).ResourceCompiler;
        if (!File.Exists(executable))
        {
            throw new FileNotFoundException("resourcecompiler.exe not found", executable);
        }
        Directory.CreateDirectory(Storage);
        CleanupLogs();
        var logId = Guid.NewGuid().ToString("N");
        var logPath = Path.Combine(Storage, logId + ".log");
        var fileList = Path.Combine(Storage, logId + ".inputs");
        var args = new List<string>();
        try
        {
            if (paths.Count == 1)
            {
                args.AddRange(["-i", paths[0]]);
            }
            else
            {
                File.WriteAllLines(fileList, paths, new UTF8Encoding(false));
                args.AddRange(["-filelist", fileList]);
            }
            if (Flag(request, "force"))
            {
                args.Add("-f");
            }
            var runner = new ProcessRunner();
            var sync = new object();
            var warnings = new List<string>();
            var errors = new List<string>();
            var tail = new Queue<string>();
            var warningCount = 0;
            var errorCount = 0;
            using var log = new StreamWriter(logPath, false, new UTF8Encoding(false)) { AutoFlush = true };
            logCreated?.Invoke(logId);
            void Emit(ProcessLine line)
            {
                lock (sync)
                {
                    log.WriteLine(line.Text);
                    var sample = BoundedSample(line.Text);
                    tail.Enqueue(sample);
                    if (tail.Count > 12)
                    {
                        tail.Dequeue();
                    }
                    if (IsDiagnostic(line.Text, "warning"))
                    {
                        warningCount++;
                        if (warnings.Count < 8) warnings.Add(sample);
                    }
                    if (IsDiagnostic(line.Text, "error") || line.Text.Contains("[FAIL]", StringComparison.OrdinalIgnoreCase))
                    {
                        errorCount++;
                        if (errors.Count < 8) errors.Add(sample);
                    }
                }
            }
            runner.OnOutput += Emit;
            using var deadlineSource = new CancellationTokenSource(TimeSpan.FromSeconds(timeout));
            using var linked = CancellationTokenSource.CreateLinkedTokenSource(cancellation, deadlineSource.Token);
            var timer = Stopwatch.StartNew();
            var exitCode = -1;
            string? failure = null;
            try
            {
                exitCode = execute is null
                    ? runner.RunAsync(executable, "", null, null, null, linked.Token, argumentList: args, onStarted: onStarted).GetAwaiter().GetResult()
                    : execute(executable, args, Emit, linked.Token);
            }
            catch (OperationCanceledException)
            {
                failure = cancellation.IsCancellationRequested ? "Compilation cancelled" : $"Compilation timed out after {timeout} seconds";
            }
            catch (Exception exception)
            {
                failure = exception.Message;
            }
            lock (sync)
            {
                // Aggregate compiler exit status does not establish individual asset outcomes.
                return new JsonObject
                {
                    ["path"] = paths.Count == 1 ? paths[0].Replace('\\', '/') : null,
                    ["success"] = exitCode == 0 && failure is null,
                    ["exit_code"] = exitCode,
                    ["error"] = failure is null ? null : BoundedSample(failure),
                    ["duration_seconds"] = timer.Elapsed.TotalSeconds,
                    ["total"] = paths.Count,
                    ["unknown_count"] = paths.Count,
                    ["compiled_count"] = 0,
                    ["skipped_count"] = 0,
                    ["failed_count"] = 0,
                    ["outcome_policy"] = "Aggregate exit status only; per-asset outcomes unknown",
                    ["process_count"] = 1,
                    ["warning_count"] = warningCount,
                    ["error_count"] = errorCount,
                    ["warnings"] = Strings(warnings),
                    ["errors"] = Strings(errors),
                    ["stdout"] = "",
                    ["stderr"] = "",
                    ["tail"] = Strings(exitCode == 0 && failure is null ? [] : tail),
                    ["log_id"] = logId,
                    ["logs_retained_days"] = 7,
                };
            }
        }
        finally
        {
            File.Delete(fileList);
        }
    }

    internal static List<string> ResolveInputs(JsonElement request)
    {
        var count = InputKeys.Count(key => request.TryGetProperty(key, out var value) && value.ValueKind != JsonValueKind.Null);
        if (count != 1) throw new ArgumentException("Specify exactly one of paths, pattern, paths_file (or single path).");
        var root = Text(request, "addon_root");
        IEnumerable<string> inputs;
        if (request.TryGetProperty("paths_file", out var file))
        {
            using var manifest = JsonDocument.Parse(File.ReadAllText(AssetPathResolver.Resolve(file.GetString()!, root)));
            inputs = manifest.RootElement.EnumerateArray().Select(item => item.GetString()!).ToArray();
        }
        else if (request.TryGetProperty("paths", out var array))
        {
            inputs = array.EnumerateArray().Select(item => item.GetString()!).ToArray();
        }
        else if (request.TryGetProperty("pattern", out var pattern))
        {
            if (root is null || !Directory.Exists(root)) throw new ArgumentException("pattern requires an existing addon_root.");
            var normalized = pattern.GetString()!.Replace('\\', '/');
            if (normalized.Contains("..", StringComparison.Ordinal) || Path.IsPathRooted(normalized)) throw new ArgumentException("pattern must remain addon-relative.");
            inputs = Directory.EnumerateFiles(root, "*", new EnumerationOptions { RecurseSubdirectories = true, AttributesToSkip = FileAttributes.ReparsePoint })
                .Where(path => System.IO.Enumeration.FileSystemName.MatchesSimpleExpression(normalized, Path.GetRelativePath(root, path).Replace('\\', '/'), true)).ToArray();
        }
        else inputs = [request.GetProperty("path").GetString()!];
        var paths = inputs.Select(path => AssetPathResolver.Resolve(path, root)).Distinct(StringComparer.OrdinalIgnoreCase).Order(StringComparer.OrdinalIgnoreCase).ToList();
        if (paths.Count == 0) throw new ArgumentException("No input assets matched.");
        if (paths.Any(path => path.Contains('\n') || path.Contains('\r'))) throw new ArgumentException("Input paths cannot contain newlines.");
        return paths;
    }

    internal static bool Flag(JsonElement request, string name) => request.TryGetProperty(name, out var value) && value.GetBoolean();
    internal static string? Text(JsonElement request, string name) => request.TryGetProperty(name, out var value) && value.ValueKind != JsonValueKind.Null ? value.GetString() : null;
    internal static JsonArray Strings(IEnumerable<string> values) => new(values.Select(value => (JsonNode?)JsonValue.Create(value)).ToArray());

    private static bool IsDiagnostic(string text, string kind)
    {
        var trimmed = text.TrimStart();
        return trimmed.Equals(kind, StringComparison.OrdinalIgnoreCase)
            || trimmed.StartsWith(kind + ":", StringComparison.OrdinalIgnoreCase)
            || trimmed.StartsWith(kind + " ", StringComparison.OrdinalIgnoreCase)
            || trimmed.Contains(" " + kind + ":", StringComparison.OrdinalIgnoreCase)
            || trimmed.Contains(": " + kind + " ", StringComparison.OrdinalIgnoreCase);
    }

    private static string BoundedSample(string text)
    {
        var result = new StringBuilder();
        var bytes = 0;
        foreach (var rune in text.EnumerateRunes())
        {
            var scalar = rune.ToString();
            var escapedBytes = JsonSerializer.SerializeToUtf8Bytes(scalar, AutomationJsonContext.Default.String).Length - 2;
            if (bytes + escapedBytes > 256) break;
            result.Append(scalar);
            bytes += escapedBytes;
        }
        return result.ToString();
    }

    internal static JsonObject ReadLog(JsonElement request)
    {
        var id = request.GetProperty("log_id").GetString()!;
        if (!Guid.TryParseExact(id, "N", out _)) throw new ArgumentException("Invalid log_id.");
        var offset = request.TryGetProperty("offset", out var position) ? position.GetInt32() : 0;
        var limit = request.TryGetProperty("limit", out var size) ? size.GetInt32() : 4096;
        if (offset < 0 || limit is < 1 or > 8192) throw new ArgumentException("Log offset must be nonnegative; limit must be 1..8192 characters.");
        using var stream = new FileStream(Path.Combine(Storage, id + ".log"), FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        using var reader = new StreamReader(stream, Encoding.UTF8);
        for (var remaining = offset; remaining > 0; remaining--)
        {
            if (ReadScalar(reader) is null) break;
        }
        var text = new StringBuilder();
        var read = 0;
        for (; read < limit; read++)
        {
            var scalar = ReadScalar(reader);
            if (scalar is null) break;
            text.Append(scalar);
        }
        return new JsonObject { ["log_id"] = id, ["offset"] = offset, ["returned"] = read, ["text"] = text.ToString(), ["truncated"] = reader.Peek() != -1 };
    }

    private static string? ReadScalar(TextReader reader)
    {
        var value = reader.Read();
        if (value < 0) return null;
        var character = (char)value;
        if (char.IsHighSurrogate(character) && reader.Peek() >= 0 && char.IsLowSurrogate((char)reader.Peek()))
            return new string([character, (char)reader.Read()]);
        return character.ToString();
    }

    private static void CleanupLogs()
    {
        var activeLogs = new HashSet<string>(StringComparer.Ordinal);
        foreach (var metadata in Directory.EnumerateFiles(Storage, "*.job.json"))
        {
            try
            {
                using var stream = new FileStream(metadata, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
                using var document = JsonDocument.Parse(stream);
                if (Text(document.RootElement, "state") is "queued" or "running" && Text(document.RootElement, "log_id") is { } logId)
                    activeLogs.Add(logId);
            }
            catch (Exception exception) when (exception is JsonException or InvalidOperationException or IOException)
            {
                // Damaged or concurrently replaced metadata is retained rather than replayed.
            }
        }
        foreach (var path in Directory.EnumerateFiles(Storage, "*.log"))
        {
            if (File.GetLastWriteTimeUtc(path) >= DateTime.UtcNow.AddDays(-7)) continue;
            if (activeLogs.Contains(Path.GetFileNameWithoutExtension(path))) continue;
            try
            {
                File.Delete(path);
            }
            catch (IOException)
            {
                // An open log may still belong to a surviving compiler.
            }
        }
    }
}
