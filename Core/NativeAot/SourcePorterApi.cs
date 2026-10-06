using System.Diagnostics.CodeAnalysis;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using Hammer5Tools.Core.Format.Toolchain;
using Hammer5Tools.Core.Format.Validation;
using Hammer5Tools.Core.Format.Vmap;
using Hammer5Tools.Core.IO.Domain;
using Hammer5Tools.Core.IO.Toolchain;

namespace Hammer5Tools.Core;

/// <summary>
/// NativeAOT ABI for the SourcePorter map-porting/asset-repair pipeline
/// (validate/force-import/repair/port). Each entry point streams progress
/// through <paramref name="logCallback"/> (matching the exact
/// <c>"  [{Kind}] {Source} -> {Detail}"</c> issue-line format the GUI already
/// parses) and returns a status code rather than a JSON payload, since nothing
/// here needs a structured return value beyond that stream.
/// </summary>
internal static unsafe class SourcePorterApi
{
    /// <summary>0 = success, no issues.</summary>
    private const int StatusOk = 0;

    /// <summary>Success, but the resulting validation report has issues — not a failure.</summary>
    private const int StatusHasIssues = 1;

    /// <summary>The operation was cancelled via <paramref name="cancellationId"/>.</summary>
    private const int StatusCancelled = -2;

    /// <summary>An exception was thrown; see the last log line for details.</summary>
    private const int StatusError = -1;

    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    /// <summary>Request: {cs2Dir, addon}.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_source_porter_validate", CallConvs = [typeof(CallConvCdecl)])]
    public static int Validate(
        byte* request, int requestLength,
        delegate* unmanaged[Cdecl]<byte*, int, void> logCallback,
        long cancellationId) =>
        InvokeCommand(logCallback, () =>
        {
            var root = ParseRequest(request, requestLength);
            var cs2 = new Cs2Install(RequireString(root, "cs2Dir"));
            var addon = RequireString(root, "addon");
            var ct = NativeInterop.GetCancellationToken(cancellationId);

            var validator = new AssetValidator(cs2, addon);
            var report = validator.Validate(line => EmitLog(logCallback, line), ct);
            EmitIssues(logCallback, report.Issues, ct);
            return report.HasIssues ? StatusHasIssues : StatusOk;
        });

    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    /// <summary>Request: {cs2Dir, addon, importScriptsDir, assetPaths: [...], noCompileAssets}.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_source_porter_force_import", CallConvs = [typeof(CallConvCdecl)])]
    public static int ForceImport(
        byte* request, int requestLength,
        delegate* unmanaged[Cdecl]<byte*, int, void> logCallback,
        long cancellationId) =>
        InvokeCommand(logCallback, () =>
        {
            var root = ParseRequest(request, requestLength);
            var cs2 = new Cs2Install(RequireString(root, "cs2Dir"));
            var addon = RequireString(root, "addon");
            var ct = NativeInterop.GetCancellationToken(cancellationId);
            void Log(string line) => EmitLog(logCallback, line);

            var runner = new ProcessRunner();
            runner.OnOutput += line => Log(line.Text);

            var importOptions = new ImportOptions { CompileAssets = !GetBool(root, "noCompileAssets") };
            var dummyVmf = Path.Combine(cs2.ContentAddonDir(addon), "maps", "import.vmf");
            var project = cs2.BuildProject(dummyVmf, addon, importOptions);

            var importScriptsDir = ResolveImportScriptsDir(cs2);
            var service = new MapImportService(cs2.Tools, runner, importScriptsDir);
            service.OnLog += Log;

            var importer = new MissingAssetImporter(service, cs2);
            importer.OnLog += Log;

            var assetPaths = RequireStringArray(root, "assetPaths");
            var extraRoots = CollectExtraContentRoots();

            var result = importer.ForceImportAsync(project, assetPaths, ct, extraContentRoots: extraRoots)
                .GetAwaiter().GetResult();
            Log($"=== FORCE IMPORT {addon}: imported {result.ModelsImported} model(s), {result.MaterialsImported} material(s) ===");
            return StatusOk;
        });

    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    /// <summary>Request: {cs2Dir, addon}.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_source_porter_repair", CallConvs = [typeof(CallConvCdecl)])]
    public static int Repair(
        byte* request, int requestLength,
        delegate* unmanaged[Cdecl]<byte*, int, void> logCallback,
        long cancellationId) =>
        InvokeCommand(logCallback, () =>
        {
            var root = ParseRequest(request, requestLength);
            var cs2 = new Cs2Install(RequireString(root, "cs2Dir"));
            var addon = RequireString(root, "addon");
            var ct = NativeInterop.GetCancellationToken(cancellationId);
            void Log(string line) => EmitLog(logCallback, line);

            var runner = new ProcessRunner();
            runner.OnOutput += line => Log(line.Text);

            var validator = new AssetValidator(cs2, addon);
            var report = validator.Validate(Log, ct);

            if (report.MissingImportCount > 0)
            {
                var importScriptsDir = ResolveImportScriptsDir(cs2);
                var service = new MapImportService(cs2.Tools, runner, importScriptsDir);
                service.OnLog += Log;

                var importOptions = new ImportOptions();
                var dummyVmf = Path.Combine(cs2.ContentAddonDir(addon), "maps", "repair.vmf");
                var project = cs2.BuildProject(dummyVmf, addon, importOptions);

                var importer = new MissingAssetImporter(service, cs2);
                importer.OnLog += Log;

                var extraRoots = CollectExtraContentRoots();
                var repairResult = importer.RepairAsync(project, report, ct: ct, extraContentRoots: extraRoots)
                    .GetAwaiter().GetResult();
                Log($"=== REPAIR {addon}: imported {repairResult.ModelsImported} model(s)/{repairResult.MaterialsImported} material(s) in {repairResult.Rounds} round(s) ===");
                report = repairResult.FinalReport;
            }

            EmitIssues(logCallback, report.Issues, ct);
            return report.HasIssues ? StatusHasIssues : StatusOk;
        });

    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    /// <summary>
    /// Request: {cs2Dir, sourceMap, addon, bspsrcLocation, threads, noBsp, noMerge,
    /// noDeps, noUnpack, compileMap, noCompileAssets, collapsePrefabs, repair,
    /// useFilelist, compact}. <paramref name="request"/>'s <c>bspsrcLocation</c> is
    /// resolved on the Python side (it knows where the packaged app's tools live);
    /// empty/omitted means "not found", matching the CLI's behavior when bspsrc
    /// isn't bundled.
    /// </summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_source_porter_port", CallConvs = [typeof(CallConvCdecl)])]
    public static int Port(
        byte* request, int requestLength,
        delegate* unmanaged[Cdecl]<byte*, int, void> logCallback,
        long cancellationId) =>
        InvokeCommand(logCallback, () =>
        {
            var root = ParseRequest(request, requestLength);
            var cs2 = new Cs2Install(RequireString(root, "cs2Dir"));
            var addon = RequireString(root, "addon");
            var sourceMap = RequireString(root, "sourceMap");
            var ct = NativeInterop.GetCancellationToken(cancellationId);
            void Log(string line) => EmitLog(logCallback, line);

            var noBsp = GetBool(root, "noBsp");
            var noMerge = GetBool(root, "noMerge");
            var noDeps = GetBool(root, "noDeps");
            var noUnpack = GetBool(root, "noUnpack");
            var compileMap = GetBool(root, "compileMap");
            var noCompileAssets = GetBool(root, "noCompileAssets");
            var collapse = GetBool(root, "collapsePrefabs");
            var repair = GetBool(root, "repair");
            var useFilelist = GetBool(root, "useFilelist");
            var compact = GetBool(root, "compact", defaultValue: true);
            var threads = GetInt32(root, "threads", 1);
            var bspsrcLocation = GetOptionalString(root, "bspsrcLocation");

            var runner = new ProcessRunner();
            runner.OnOutput += line => Log(line.Text);

            string vmf;
            if (sourceMap.EndsWith(".bsp", StringComparison.OrdinalIgnoreCase) && !noBsp)
            {
                var decompiler = new BspDecompiler(runner, bspsrcLocation);
                decompiler.OnLog += Log;
                vmf = MapStaging.StageBspAsync(decompiler, sourceMap, !noUnpack, ct).GetAwaiter().GetResult();
                noMerge = true;
            }
            else
            {
                vmf = MapStaging.StageVmf(sourceMap, Log);
            }

            var importOptions = new ImportOptions
            {
                UseBsp = !noBsp && !noMerge,
                UseBspNoMergeInstances = noMerge && !noBsp,
                SkipDeps = noDeps,
                MaxParallelism = Math.Max(1, threads),
                CompileAssets = !noCompileAssets,
                CompactLog = compact,
                UseFilelist = useFilelist,
            };

            var project = cs2.BuildProject(vmf, addon, importOptions);
            var importScriptsDir = ResolveImportScriptsDir(cs2);
            var service = new MapImportService(cs2.Tools, runner, importScriptsDir);
            service.OnLog += Log;

            Log($"=== IMPORT {project.MapName} -> {addon} ===");
            service.ImportAsync(project, ct).GetAwaiter().GetResult();

            if (collapse)
            {
                PostImportVmapTools.CollapsePrefabs(cs2, addon, project.MapName, Log, ct);
                PostImportVmapTools.FlattenSingleChildGroups(cs2, addon, Log, ct);
            }

            if (compileMap)
            {
                Log($"=== COMPILE {project.MapName} ===");
                service.CompileMapAsync(project, ct).GetAwaiter().GetResult();
            }

            var stats = AddonStats.Collect(cs2.ContentAddonDir(addon), Path.Combine(cs2.GameDir, "csgo_addons", addon));
            foreach (var line in stats.Format())
                Log(line);

            var validator = new AssetValidator(cs2, addon);
            var report = validator.Validate(Log, ct);

            if (repair && report.MissingImportCount > 0)
            {
                var importer = new MissingAssetImporter(service, cs2);
                importer.OnLog += Log;
                var repairResult = importer.RepairAsync(project, report, ct: ct).GetAwaiter().GetResult();
                Log($"=== REPAIR {addon}: imported {repairResult.ModelsImported} model(s)/{repairResult.MaterialsImported} material(s) in {repairResult.Rounds} round(s) ===");
                report = repairResult.FinalReport;
            }

            EmitIssues(logCallback, report.Issues, ct);
            return report.HasIssues ? StatusHasIssues : StatusOk;
        });

    /// <summary>Runs <paramref name="operation"/>, translating exceptions into a logged error and a status code.</summary>
    private static int InvokeCommand(delegate* unmanaged[Cdecl]<byte*, int, void> logCallback, Func<int> operation)
    {
        try
        {
            return operation();
        }
        catch (OperationCanceledException)
        {
            EmitLog(logCallback, "[SourcePorter] Cancelled.");
            return StatusCancelled;
        }
        catch (Exception exception)
        {
            EmitLog(logCallback, $"[SourcePorter Error] {NativeInterop.DescribeException(exception)}");
            return StatusError;
        }
    }

    private static void EmitLog(delegate* unmanaged[Cdecl]<byte*, int, void> logCallback, string line)
    {
        if (logCallback is null)
            return;
        var bytes = Encoding.UTF8.GetBytes(line);
        fixed (byte* pointer = bytes)
            logCallback(pointer, bytes.Length);
    }

    /// <summary>Streams issues in the exact <c>"  [{Kind}] {Source} -> {Detail}"</c> format the GUI parses.</summary>
    private static void EmitIssues(
        delegate* unmanaged[Cdecl]<byte*, int, void> logCallback, IReadOnlyList<AssetIssue> issues, CancellationToken ct)
    {
        foreach (var issue in issues)
        {
            if (ct.IsCancellationRequested)
                break;
            EmitLog(logCallback, $"  [{issue.Kind}] {issue.Source} -> {issue.Detail}");
        }
    }

    /// <summary>
    /// Extra custom-content roots to search for missing sources: every per-map staging
    /// dir under <see cref="MapStaging.StagingRoot"/>, plus its own BSPSource unpack
    /// subfolder (same name) when present.
    /// </summary>
    private static List<string> CollectExtraContentRoots()
    {
        var extraRoots = new List<string>();
        var stagingRoot = MapStaging.StagingRoot;
        if (!Directory.Exists(stagingRoot))
            return extraRoots;

        foreach (var candidate in Directory.GetDirectories(stagingRoot))
        {
            extraRoots.Add(candidate);
            var unpackSubdir = Path.Combine(candidate, Path.GetFileName(candidate));
            if (Directory.Exists(unpackSubdir))
                extraRoots.Add(unpackSubdir);
        }
        return extraRoots;
    }

    private static string ResolveImportScriptsDir(Cs2Install cs2) =>
        Directory.Exists(cs2.ImportScriptsDir) ? cs2.ImportScriptsDir : Environment.CurrentDirectory;

    private static JsonElement ParseRequest(byte* request, int requestLength) =>
        JsonDocument.Parse(NativeInterop.ReadUtf8(request, requestLength)).RootElement;

    private static string RequireString(JsonElement root, string propertyName) =>
        root.GetProperty(propertyName).GetString()
        ?? throw new ArgumentException($"'{propertyName}' must not be null.");

    private static string? GetOptionalString(JsonElement root, string propertyName) =>
        root.TryGetProperty(propertyName, out var property) && property.ValueKind == JsonValueKind.String
            ? property.GetString()
            : null;

    private static List<string> RequireStringArray(JsonElement root, string propertyName)
    {
        var values = new List<string>();
        foreach (var item in root.GetProperty(propertyName).EnumerateArray())
            values.Add(item.GetString() ?? "");
        return values;
    }

    private static bool GetBool(JsonElement root, string propertyName, bool defaultValue = false) =>
        root.TryGetProperty(propertyName, out var property) ? property.GetBoolean() : defaultValue;

    private static int GetInt32(JsonElement root, string propertyName, int defaultValue) =>
        root.TryGetProperty(propertyName, out var property) ? property.GetInt32() : defaultValue;
}
