using SourcePorter.Core.Domain;
using SourcePorter.Core.Toolchain;
using SourcePorter.Core.Validation;
using SourcePorter.Core.Vmap;

// Headless harness for porting + validating maps — used to test imports in bulk.
//
//   port     <cs2dir> <sourceMap.vmf|.bsp> <addon> [--no-bsp] [--no-unpack] [--compile] [--no-compile-assets] [--collapse-prefabs] [--skybox-template] [--no-uv-fix] [--repair] [--verbose]
//   validate <cs2dir> <addon>
//   batch    <cs2dir> <mapsDir> [--limit N] [--no-bsp] [--no-unpack] [--compile] [--no-compile-assets] [--collapse-prefabs] [--skybox-template] [--repair] [--verbose]
//
// --collapse-prefabs: after importing, merge the map's prefab/sub-map references into the
// root .vmap (the sub-map files are kept), then flatten the redundant single-child/empty
// CMapGroup wrappers it leaves behind (shrinks the .vmap). --skybox-template: scaffold a
// 3D-skybox setup (a separate <map>_sky.vmap flagged skybox + a skybox_reference at 0 0 0).
// See PostImportVmapTools.
//
// --repair: after validating, re-import the materials/models the importer missed
// (a model's gib/breakpiece children, a skybox material from a lighting prefab, …),
// looping import→re-validate to a fixpoint. See MissingAssetImporter.
//
// Console output is compacted by default (one "Ported X" line per asset); pass
// --verbose for the raw, unfiltered toolchain output.
//
// By default the map .vmap_c compile (slow lighting bake) is SKIPPED — import +
// validate-dependencies only, which is what answers "any missing files?".
// Pass --compile to also compile the map (surfaces map-level skybox/particle gaps).
// Dependency asset compile (materials/models -> _c) is ON by default here so the
// validator has _c files to check; pass --no-compile-assets for a faster import-only
// pass (validation then reports nothing, since there is nothing compiled to scan).

if (args.Length == 0)
{
    Console.Error.WriteLine("usage: port|validate|batch …");
    return 2;
}

try
{
    return args[0].ToLowerInvariant() switch
    {
        "port" => await Port(args[1], args[2], args[3], NoBsp(args), args.Contains("--compile"), CompileAssets(args), !NoUnpack(args), Threads(args), Compact(args), Repair(args), Collapse(args), Skybox(args), NoUvFix(args)),
        "validate" => Validate(args[1], args[2]),
        "repair" => await StandaloneRepair(args[1], args[2]),
        "force-import" => await ForceImport(args[1], args[2], args.Skip(3).ToArray(), CompileAssets(args)),
        "batch" => await Batch(args[1], args[2], Limit(args), NoBsp(args), args.Contains("--compile"), CompileAssets(args), !NoUnpack(args), Threads(args), Compact(args), Repair(args), Collapse(args), Skybox(args), NoUvFix(args)),
        _ => Fail($"unknown command '{args[0]}'"),
    };
}
catch (Exception ex)
{
    Console.Error.WriteLine($"ERROR: {ex.Message}");
    return 1;
}

static bool NoBsp(string[] a) => a.Contains("--no-bsp");
static bool NoUnpack(string[] a) => a.Contains("--no-unpack");
static bool CompileAssets(string[] a) => !a.Contains("--no-compile-assets");
static bool Compact(string[] a) => !a.Contains("--verbose");
static bool Repair(string[] a) => a.Contains("--repair");
static bool Collapse(string[] a) => a.Contains("--collapse-prefabs");
static bool Skybox(string[] a) => a.Contains("--skybox-template");
static bool NoUvFix(string[] a) => a.Contains("--no-uv-fix");
static int Limit(string[] a)
{
    var i = Array.IndexOf(a, "--limit");
    return i >= 0 && i + 1 < a.Length && int.TryParse(a[i + 1], out var n) ? n : int.MaxValue;
}
static int Threads(string[] a)
{
    var i = Array.IndexOf(a, "--threads");
    return i >= 0 && i + 1 < a.Length && int.TryParse(a[i + 1], out var n) && n >= 1 ? n : Math.Max(1, Environment.ProcessorCount - 1);
}
static int Fail(string m) { Console.Error.WriteLine(m); return 2; }

static async Task<int> Port(string cs2Dir, string sourceMap, string addon, bool noBsp, bool compile, bool compileAssets, bool unpack, int threads, bool compact, bool repair, bool collapse, bool skybox, bool noUvFix)
{
    var cs2 = new Cs2Install(cs2Dir);
    if (!cs2.IsValid(out var err)) { Console.Error.WriteLine(err); return 1; }

    // Stop before decompiling/staging: while CS2 holds vpk.signatures open the guide -1.1
    // workaround can't be applied and source1import always fails to read csgo\pak01.vpk.
    if (VpkSignaturesGuard.IsLocked(cs2.Tools.VpkSignatures))
    {
        Console.Error.WriteLine(VpkSignaturesGuard.LockedAdvice);
        return 1;
    }

    // The decompiler forwards its own output via OnLog and the import service via OnLog
    // (compacted when enabled), so we subscribe to those — not runner.OnOutput — to keep
    // each tool line printed exactly once.
    var runner = new ProcessRunner();

    string vmf;
    // Decompiled BSPs are flat (func_instances inlined), so there are no instances to merge
    // and plain -usebsp can crash source1import's merge pass — use -usebsp_nomergeinstances for
    // decompiled input. A loose .vmf keeps the default -usebsp (it may have real instances).
    var noMerge = false;
    var bspImported = false;
    if (sourceMap.EndsWith(".bsp", StringComparison.OrdinalIgnoreCase) && !noBsp)
    {
        var decompiler = new BspDecompiler(runner);
        decompiler.OnLog += Console.WriteLine;
        vmf = await MapStaging.StageBspAsync(decompiler, sourceMap, unpack);
        noMerge = true;
        bspImported = true;
    }
    else
    {
        vmf = MapStaging.StageVmf(sourceMap, Console.WriteLine);
    }

    var project = cs2.BuildProject(vmf, addon, new ImportOptions { UseBsp = !noMerge, UseBspNoMergeInstances = noMerge, MaxParallelism = threads, CompileAssets = compileAssets, CompactLog = compact });
    var service = new MapImportService(cs2.Tools, runner, ResolveImportScriptsDir(cs2));
    service.OnLog += Console.WriteLine;

    Console.WriteLine($"=== IMPORT {project.MapName} -> {addon} ===");
    await service.ImportAsync(project);

    // Brush UV scale fix for a decompiled BSP's custom materials (source1import bakes them at a
    // 16x16-default scale because it can't read their .vtf). On by default for BSP imports; the
    // staged content holds only the BSP's custom materials, so stock faces are never touched.
    if (bspImported && !noUvFix)
        PostImportVmapTools.FixBrushUvScale(cs2, addon, project.MapName, project.S1ContentDir, Console.WriteLine);

    // Opt-in post-import .vmap edits, before the compile so a --compile picks them up.
    if (collapse)
    {
        PostImportVmapTools.CollapsePrefabs(cs2, addon, project.MapName, Console.WriteLine);
        // Collapsing leaves single-child group wrappers behind — flatten them automatically.
        PostImportVmapTools.FlattenSingleChildGroups(cs2, addon, Console.WriteLine);
    }
    if (skybox)
        PostImportVmapTools.CreateSkyboxTemplate(cs2, addon, project.MapName, Console.WriteLine);

    if (compile)
    {
        Console.WriteLine($"=== COMPILE {project.MapName} ===");
        await service.CompileMapAsync(project);
    }

    foreach (var line in AddonStats.Collect(cs2.ContentAddonDir(addon), Path.Combine(cs2.GameDir, "csgo_addons", addon)).Format())
        Console.WriteLine(line);

    var report = new AssetValidator(cs2, addon).Validate(Console.WriteLine);

    // Optional remediation: re-import the materials/models the importer missed.
    if (repair && report.MissingImportCount > 0)
    {
        var importer = new MissingAssetImporter(service, cs2);
        importer.OnLog += Console.WriteLine;
        var rr = await importer.RepairAsync(project, report);
        Console.WriteLine($"=== REPAIR {addon}: imported {rr.ModelsImported} model(s)/{rr.MaterialsImported} material(s) " +
                          $"in {rr.Rounds} round(s); resolved {rr.Resolved}/{rr.InitialMissing}, still missing {rr.StillMissing} ===");
        report = rr.FinalReport;
    }

    PrintReport(addon, report);
    return report.HasIssues ? 1 : 0;
}

static int Validate(string cs2Dir, string addon)
{
    var cs2 = new Cs2Install(cs2Dir);
    var report = new AssetValidator(cs2, addon).Validate(Console.WriteLine);
    PrintReport(addon, report);
    return report.HasIssues ? 1 : 0;
}

static void PrintReport(string addon, ValidationReport report)
{
    foreach (var issue in report.Issues.Take(40))
        Console.WriteLine($"  [{issue.Kind}] {issue.Source} -> {issue.Detail}");
    if (report.Issues.Count > 40)
        Console.WriteLine($"  … and {report.Issues.Count - 40} more.");

    Console.WriteLine($"=== {addon}: contentFiles={report.ContentFilesScanned} refs={report.ReferencesChecked} " +
                      $"missingPrefabs={report.MissingPrefabCount} notImported={report.MissingImportCount} " +
                      $"(mats={report.MissingImportMaterials} models={report.MissingImportModels}) " +
                      $"missingSources={report.MissingSourceCount} compiled={report.CompiledResourcesScanned} " +
                      $"missingCompiledDeps={report.MissingReferenceCount} readErrors={report.ErrorCount} ===");
}

static async Task<int> Batch(string cs2Dir, string mapsDir, int limit, bool noBsp, bool compile, bool compileAssets, bool unpack, int threads, bool compact, bool repair, bool collapse, bool skybox, bool noUvFix)
{
    var maps = Directory.EnumerateFiles(mapsDir, "*.vmf").Take(limit).ToList();
    Console.WriteLine($"Batch porting {maps.Count} map(s) from {mapsDir} (compile={compile}, compileAssets={compileAssets}, threads={threads})");

    var results = new List<string>();
    foreach (var map in maps)
    {
        var name = Path.GetFileNameWithoutExtension(map);
        var addon = $"{name}_test";
        try
        {
            var code = await Port(cs2Dir, map, addon, noBsp, compile, compileAssets, unpack, threads, compact, repair, collapse, skybox, noUvFix);
            results.Add($"{name}: {(code == 0 ? "CLEAN" : "ISSUES")}");
        }
        catch (Exception ex)
        {
            results.Add($"{name}: FAILED ({ex.Message})");
        }
    }

    Console.WriteLine("\n===== BATCH SUMMARY =====");
    results.ForEach(Console.WriteLine);
    return results.All(r => r.EndsWith("CLEAN")) ? 0 : 1;
}

static async Task<int> StandaloneRepair(string cs2Dir, string addon)
{
    var cs2 = new Cs2Install(cs2Dir);
    if (!cs2.IsValid(out var err)) { Console.Error.WriteLine(err); return 1; }

    if (VpkSignaturesGuard.IsLocked(cs2.Tools.VpkSignatures))
    {
        Console.Error.WriteLine(VpkSignaturesGuard.LockedAdvice);
        return 1;
    }

    var runner = new ProcessRunner();
    var service = new MapImportService(cs2.Tools, runner, ResolveImportScriptsDir(cs2));
    service.OnLog += Console.WriteLine;

    var report = new AssetValidator(cs2, addon).Validate(Console.WriteLine);
    if (report.MissingImportCount > 0)
    {
        var importer = new MissingAssetImporter(service, cs2);
        importer.OnLog += Console.WriteLine;
        var dummyProject = cs2.BuildProject(Path.Combine(cs2.ContentAddonDir(addon), "dummy.vmf"), addon, new ImportOptions());
        var rr = await importer.RepairAsync(dummyProject, report);
        Console.WriteLine($"=== REPAIR {addon}: imported {rr.ModelsImported} model(s)/{rr.MaterialsImported} material(s) in {rr.Rounds} round(s) ===");
        report = rr.FinalReport;
    }
    else
    {
        Console.WriteLine($"=== REPAIR {addon}: no missing imports reported ===");
    }
    PrintReport(addon, report);
    return report.HasIssues ? 1 : 0;
}

static async Task<int> ForceImport(string cs2Dir, string addon, string[] assetPaths, bool compileAssets)
{
    var cs2 = new Cs2Install(cs2Dir);
    if (!cs2.IsValid(out var err)) { Console.Error.WriteLine(err); return 1; }

    if (VpkSignaturesGuard.IsLocked(cs2.Tools.VpkSignatures))
    {
        Console.Error.WriteLine(VpkSignaturesGuard.LockedAdvice);
        return 1;
    }

    var options = new ImportOptions { CompileAssets = compileAssets };
    var project = new PortProject
    {
        S1GameInfoDir = cs2.S1GameInfoDir,
        S2GameInfoDir = cs2.S2GameInfoDir,
        AddonName = addon,
        MapName = addon,
        Import = options,
    };

    var runner = new ProcessRunner();
    var service = new MapImportService(cs2.Tools, runner, ResolveImportScriptsDir(cs2));
    service.OnLog += Console.WriteLine;

    var importer = new MissingAssetImporter(service, cs2);
    importer.OnLog += Console.WriteLine;

    var parsed = assetPaths.SelectMany(MissingAssetImporter.ParseAssetList).Distinct().ToList();
    Console.WriteLine($"=== FORCE IMPORT into {addon}: {parsed.Count} asset path(s) ===");
    var report = await importer.ForceImportAsync(project, parsed);
    Console.WriteLine($"=== FORCE IMPORT {addon}: imported {report.ModelsImported} model(s)/{report.MaterialsImported} material(s) ===");
    return 0;
}

// source1import needs its real home dir as cwd (config lists + ./bin/vbsp.exe).
static string ResolveImportScriptsDir(Cs2Install cs2) =>
    Directory.Exists(cs2.ImportScriptsDir) ? cs2.ImportScriptsDir : AppContext.BaseDirectory;
