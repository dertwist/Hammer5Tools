using System.Collections.Concurrent;
using System.Text;
using System.Text.RegularExpressions;
using Hammer5Tools.Core.IO.Domain;
using Hammer5Tools.Core.IO.Toolchain;

namespace Hammer5Tools.Core.Format.Toolchain;

/// <summary>
/// C# port of Valve's <c>import_scripts/import_map_community.py</c>. Drives
/// <c>source1import</c>, <c>cs_mdl_import</c>, and <c>resourcecompiler</c> in the
/// same order, with the same arguments and the same model/material/2-UV handling
/// — only the console-input gate and the <c>| tee</c> logging are replaced
/// (confirmation is handled by the UI; output is captured via
/// <see cref="ProcessRunner"/>).
/// </summary>
public sealed partial class MapImportService
{
    private readonly ValveToolLocator _tools;
    private readonly ProcessRunner _runner;
    private readonly string _workingDir;
    private readonly string _global2UvListPath;
    private int _maxParallelism = 1;
    private bool _compileAssets;

    // Optional console compactor. Tool output arrives from several processes at once,
    // so the (stateful) compactor is guarded by _emitLock. Null = pass everything through.
    private LogCompactor? _compactor;
    private readonly object _emitLock = new();

    /// <summary>Status/header lines (mirrors the Python <c>print_I</c> banners).</summary>
    public event Action<string>? OnLog;

    /// <param name="tools">Resolves the Valve tool executables.</param>
    /// <param name="runner">Process runner (output is forwarded to <see cref="OnLog"/>).</param>
    /// <param name="importScriptsDir">
    /// The <c>import_scripts</c> directory — the working directory the tools run in
    /// and where <c>source1import_2uvmateriallist.txt</c> lives. Defaults to CWD,
    /// matching the Python.
    /// </param>
    public MapImportService(ValveToolLocator tools, ProcessRunner runner, string? importScriptsDir = null)
    {
        _tools = tools;
        _runner = runner;
        _workingDir = importScriptsDir ?? Environment.CurrentDirectory;
        _global2UvListPath = Path.Combine(_workingDir, "source1import_2uvmateriallist.txt");
        _runner.OnOutput += line => Emit(line.Text);
    }

    /// <summary>
    /// Routes a log line through the compactor (when enabled) and raises
    /// <see cref="OnLog"/>. The compactor is stateful and fed from multiple tool
    /// threads, so access is serialised.
    /// </summary>
    private void Emit(string line)
    {
        var compactor = _compactor;
        if (compactor is null)
        {
            OnLog?.Invoke(line);
            return;
        }

        lock (_emitLock)
        {
            foreach (var outLine in compactor.Process(line))
                OnLog?.Invoke(outLine);
        }
    }

    /// <summary>Flushes any pending compactor state (a trailing repeat-count).</summary>
    private void FlushLog()
    {
        var compactor = _compactor;
        if (compactor is null)
            return;

        lock (_emitLock)
        {
            foreach (var outLine in compactor.Flush())
                OnLog?.Invoke(outLine);
        }
    }

    /// <summary>
    /// Runs the full import. <paramref name="project"/> supplies the four paths,
    /// addon, map name, and <see cref="ImportOptions"/>.
    /// </summary>
    public async Task ImportAsync(PortProject project, CancellationToken ct = default)
    {
        var s1Game = project.S1GameInfoDir;
        var s1Content = project.S1ContentDir;
        var addon = project.AddonName;
        var originalMapName = project.MapName;
        _maxParallelism = Math.Max(1, project.Import.MaxParallelism);
        _compileAssets = project.Import.CompileAssets;
        _compactor = project.Import.CompactLog ? new LogCompactor() : null;

        try
        {

            var paths = new ImportPaths(project.S2GameInfoDir, addon, originalMapName);

            // VALVE_NO_AUTO_P4=1 so the p4 libs run disconnected (utlc.SaveEnv).
            var env = new Dictionary<string, string> { ["VALVE_NO_AUTO_P4"] = "1" };

            // Guide §-1.1: disable vpk.signatures for the run (restored on dispose) so
            // source1import can read the CS:GO pak01.vpk.
            using var signatures = new VpkSignaturesGuard(_tools.VpkSignatures, Emit);
            ReportSignatures(signatures, "import");

            // Terrain fix: -usebsp makes source1import shell out to vbsp to clean up the
            // geometry (displacements/terrain), but it passes the content path to vbsp
            // UNQUOTED — a space in the install path ("Counter-Strike Global Offensive")
            // splits the argument, so vbsp prints usage, never runs, and the map falls back
            // to broken vmf-only geo. Hand source1import the 8.3 short path (no spaces) so
            // the path survives intact down to vbsp.
            if ((project.Import.UseBsp || project.Import.UseBspNoMergeInstances) && s1Content.Contains(' '))
                s1Content = ResolveSpaceFreeContentDir(s1Content);

            // Sync custom unpacked assets into the CS:GO game directory so source1import
            // resolves texture dimensions natively during the map import pass.
            SyncStagedContentToCsgoDir(s1Content, s1Game);
            var depsGameDir = PrepareDepsGameDir(s1Game, s1Content);

            // --- import vmf -> vmap (built once with the ORIGINAL map name, reused for the re-import) ---
            // source1import's -usebsp passes (instance merge, then vbsp geo cleanup) can each
            // access-violate on some maps (after the .vmap is written but before the refs list).
            // RunMapImportAsync degrades the BSP mode step by step (merge → no-merge → vmf-only) on
            // that crash and returns the mode that imported, so the step-5 re-import reuses it.
            // The map VMF import requires the real csgo gameinfo dir (s1Game) so CVMFtoVMAP calculates
            // the target addon vmap path correctly.
            var bspMode = await RunMapImportAsync(
                s1Game, s1Content, addon, originalMapName, InitialBspMode(project.Import), env, ct);
            var importArgs = BuildMapImportArgs(s1Game, s1Content, addon, originalMapName, bspMode);

            // replace 'instance' paths with 'prefab'
            paths.SwitchInstancesToPrefabs();

            if (project.Import.SkipDeps)
            {
                Emit("Skip dependencies is ON — no materials or models were imported. " +
                     "The map will be missing them; re-import with dependencies enabled for a complete addon.");
            }

            if (!project.Import.SkipDeps)
            {
                // Use whichever refs file source1import actually wrote (_prefab_refs.txt
                // when -usebsp merged instances, else plain _refs.txt) and derive the
                // mdl/new-refs names from the SAME base so the steps line up.
                var refsFile = paths.ResolveRefsFile();
                if (refsFile is null)
                {
                    Emit("WARNING: source1import produced no refs file — dependencies (materials/models) were not imported.");
                }
                else
                {
                    Emit($"Importing dependencies from {Path.GetFileName(refsFile)}");
                    if (!_compileAssets)
                        Emit("Compile Assets is off — importing asset sources only; skipping resourcecompiler. Enable 'Compile Assets' to compile materials/models.");

                    // We strip out models as they go through the new importer last.
                    StripMdlsFromRefs(refsFile);

                    var mdlList = refsFile.Replace("_refs.txt", "_mdl_lst.txt");
                    var newRefs = refsFile.Replace("_refs.txt", "_new_refs.txt");

                    // now import mdls (as modeldoc), and their materials
                    await ImportAndCompileMapMdlsAsync(mdlList, paths, s1Game, s1Content, depsGameDir, addon, env, ct, project.Import.UseFilelist);

                    // import refs (excluding mdls)
                    await ImportAndCompileMapRefsAsync(newRefs, paths, s1Content, depsGameDir, addon, env, ct, project.Import.UseFilelist);

                    // quick import vmf again, now that dependencies (materials especially) are compiled
                    await RunAsync(_tools.Source1Import, "source1import.exe", importArgs, env, ct,
                        standardInput: ConfirmIfNotCsgo(s1Game));
                }
            }

            // explicit copy of main .vmap to game maps if not already there (it can only be compiled from there)
            if (!File.Exists(paths.ContentMainVmap) && File.Exists(paths.ImportedMainVmap))
            {
                Directory.CreateDirectory(Path.GetDirectoryName(paths.ContentMainVmap)!);
                File.Copy(paths.ImportedMainVmap, paths.ContentMainVmap, overwrite: true);
            }

        }
        finally
        {
            FlushLog();
            _compactor = null;
        }
    }

    /// <summary>
    /// Reports the outcome of the <c>vpk.signatures</c> workaround (guide §-1.1).
    /// <paramref name="context"/> names the pass (import / repair pass / compile).
    /// <para>
    /// A locked file is <b>fatal</b> for the passes that mount the Source 1 game dir: they run
    /// <c>source1import</c>, which cannot read the unsigned <c>csgo\pak01.vpk</c> while
    /// <c>vpk.signatures</c> is in place, so the run is guaranteed to fail — better to stop now
    /// with <see cref="VpkSignaturesGuard.LockedAdvice"/> than to grind on into the FATAL. Pass
    /// <paramref name="fatal"/> false for a pass that only touches Source 2 content (the map
    /// compile), where the workaround is precautionary and the lock harmless.
    /// </para>
    /// </summary>
    private void ReportSignatures(VpkSignaturesGuard signatures, string context, bool fatal = true)
    {
        switch (signatures.State)
        {
            case VpkSignaturesState.Disabled:
                Emit($"Disabled vpk.signatures for this {context} (guide -1.1); will restore afterwards.");
                break;
            case VpkSignaturesState.Locked when fatal:
                throw new ImportToolException(VpkSignaturesGuard.LockedAdvice);
            case VpkSignaturesState.Locked:
                Emit($"WARNING: couldn't disable vpk.signatures for this {context}. " +
                     VpkSignaturesGuard.LockedAdvice);
                break;
        }
    }

    /// <summary>
    /// Returns a space-free form of <paramref name="contentDir"/> for the
    /// <c>-usebsp</c> path (see <see cref="ShortPath"/>). Falls back to the original
    /// path (with a warning) when no 8.3 short name is available, in which case the
    /// vbsp geometry pass will fail and the map imports with vmf-only terrain.
    /// </summary>
    private string ResolveSpaceFreeContentDir(string contentDir)
    {
        var shortPath = ShortPath.TryGet(contentDir);
        if (shortPath is not null && !shortPath.Contains(' '))
        {
            Emit($"Using 8.3 short path for the content dir so -usebsp/vbsp gets a space-free argument: {shortPath}");
            return shortPath;
        }

        Emit("WARNING: -usebsp may fail — the content path contains a space and no 8.3 short name is " +
             "available (terrain would import as vmf-only geometry). Move the install to a space-free " +
             "path, or enable 8.3 names on the volume (fsutil 8dot3name).");
        return contentDir;
    }

    private void SyncStagedContentToCsgoDir(string s1Content, string s1Game)
    {
        if (string.IsNullOrEmpty(s1Content) || string.IsNullOrEmpty(s1Game) ||
            string.Equals(s1Content, s1Game, StringComparison.OrdinalIgnoreCase) ||
            !Directory.Exists(s1Content) || !Directory.Exists(s1Game))
            return;

        int filesCopied = 0;
        var subDirs = new[] { "materials", "models", "sound", "scripts", "resource" };
        foreach (var sub in subDirs)
        {
            var srcSub = Path.Combine(s1Content, sub);
            if (!Directory.Exists(srcSub))
                continue;

            var dstSub = Path.Combine(s1Game, sub);
            foreach (var file in Directory.EnumerateFiles(srcSub, "*.*", SearchOption.AllDirectories))
            {
                var rel = Path.GetRelativePath(srcSub, file);
                var destFile = Path.Combine(dstSub, rel);
                var dir = Path.GetDirectoryName(destFile);
                if (!string.IsNullOrEmpty(dir))
                    Directory.CreateDirectory(dir);

                if (!File.Exists(destFile) || File.GetLastWriteTimeUtc(file) > File.GetLastWriteTimeUtc(destFile))
                {
                    try
                    {
                        File.Copy(file, destFile, overwrite: true);
                        filesCopied++;
                    }
                    catch { /* best-effort copy */ }
                }
            }
        }
        if (filesCopied > 0)
        {
            Emit($"Staged {filesCopied} custom unpacked asset(s) into CS:GO game directory ({s1Game}) for native Valve UV scale conversion.");
        }
    }

    /// <summary>
    /// Returns the dir to use as <c>-src1gameinfodir</c> for the dependency imports. For a staged
    /// content root (decompiled BSP / temp copy), drops a custom <see cref="ImportGameInfo"/> there
    /// and returns that root — so its unpacked custom <c>.vmt</c>/<c>.vtf</c> are a source1import
    /// GAME search path (materials import from the game path, not content) while the base CS:GO
    /// assets still mount. Otherwise returns <paramref name="s1Game"/> unchanged (never writes into
    /// the user's own folder). See <see cref="ImportGameInfo"/> for why the game path is required.
    /// </summary>
    private string PrepareDepsGameDir(string s1Game, string s1Content)
    {
        if (!ImportGameInfo.IsStagedContentDir(s1Content))
            return s1Game;

        ImportGameInfo.EnsureCustomGameInfo(s1Content, s1Game);
        Emit("Custom BSP content detected — exposing the unpacked materials/models to source1import as " +
             "a game search path so the map's embedded assets import (not just stock CS:GO ones).");
        return s1Content;
    }

    /// <summary>
    /// source1import prompts "…gameinfo.txt in csgo … Are you sure you want to continue? ('y')"
    /// whenever its <c>-src1gameinfodir</c> leaf isn't <c>csgo</c> — which is the case for our
    /// custom-content gameinfo (it lives in the <c>&lt;map&gt;</c>-named staged content root).
    /// Returns the stdin answer (<c>"y"</c>) for that case so the run doesn't hang, else null.
    /// </summary>
    internal static string? ConfirmIfNotCsgo(string gameInfoDir)
    {
        var leaf = gameInfoDir.TrimEnd('\\', '/').Split(['\\', '/'], StringSplitOptions.RemoveEmptyEntries).LastOrDefault();
        return string.Equals(leaf, "csgo", StringComparison.OrdinalIgnoreCase) ? null : "y\n";
    }

    /// <summary>
    /// Imports an explicit set of Source 1 models (<c>.mdl</c>) and materials (<c>.vmt</c>)
    /// into the addon — the "repair" primitive <see cref="MissingAssetImporter"/> drives
    /// when the validator finds dependencies the main import missed (a model's gib/breakpiece
    /// children, a skybox material referenced only by a lighting prefab, …). It reuses the
    /// exact dependency-phase passes: each model goes through <c>cs_mdl_import</c> (collecting
    /// and importing its own materials, forcing <c>F_FORCE_UV2</c> on 2-UV ones), and the
    /// standalone materials go through <c>source1import -usefilelist</c>. Honors
    /// <see cref="ImportOptions.CompileAssets"/> and <see cref="ImportOptions.CompactLog"/>.
    /// Per-asset failures are warnings (an asset with no S1 source simply stays missing),
    /// never fatal.
    /// </summary>
    public async Task ImportSpecificAssetsAsync(
        PortProject project,
        IReadOnlyCollection<string> modelMdls,
        IReadOnlyCollection<string> materialVmts,
        CancellationToken ct = default,
        bool stockOnly = false)
    {
        if (modelMdls.Count == 0 && materialVmts.Count == 0)
            return;

        _maxParallelism = Math.Max(1, project.Import.MaxParallelism);
        _compileAssets = project.Import.CompileAssets;
        _compactor = project.Import.CompactLog ? new LogCompactor() : null;
        try
        {
            var env = new Dictionary<string, string> { ["VALVE_NO_AUTO_P4"] = "1" };

            using var signatures = new VpkSignaturesGuard(_tools.VpkSignatures, Emit);
            ReportSignatures(signatures, "repair pass");

            var paths = new ImportPaths(project.S2GameInfoDir, project.AddonName, project.MapName);
            var mapsDir = Path.Combine(paths.S2ContentCsgoImported, "maps");
            Directory.CreateDirectory(mapsDir);

            var s1Game = project.S1GameInfoDir;

            // Stock assets (found in the CS:GO VPKs) MUST import through the real csgo gameinfo dir —
            // it's what mounts pak01_dir.vpk. Routing them through a staged custom-content gameinfo
            // (as custom BSP assets need) makes source1import report "Found no files matching". So the
            // repair calls this once per source group: stock -> real csgo dir, custom -> staged root.
            var s1Content = stockOnly ? s1Game : project.S1ContentDir;
            var depsGameDir = stockOnly ? s1Game : PrepareDepsGameDir(s1Game, s1Content);

            // Models: a flat mdl list reused by the dependency-phase model importer (which
            // also imports each model's materials and applies the 2-UV fix). The list name
            // keeps the "mdl_lst" token that pass rewrites to "mtl_lst" for the material list.
            if (modelMdls.Count > 0)
            {
                var mdlListPath = Path.Combine(mapsDir, "repair_mdl_lst.txt");
                RefsFile.EnsureFileWritable(mdlListPath);
                File.WriteAllLines(mdlListPath, modelMdls.Select(m => m.Replace('/', '\\')));
                await ImportAndCompileMapMdlsAsync(mdlListPath, paths, s1Game, s1Content, depsGameDir, project.AddonName, env, ct, project.Import.UseFilelist);
            }

            // Materials: wrapped in the importfilelist format and reused by the refs importer
            // (the "_new_refs.txt" suffix is the token that pass rewrites for its compile list).
            if (materialVmts.Count > 0)
            {
                var refsPath = Path.Combine(mapsDir, "repair_new_refs.txt");
                RefsFile.EnsureFileWritable(refsPath);
                var refsContent = project.Import.UseFilelist
                    ? RefsFile.RefsStringFromListWithPrefixes(materialVmts, "materials/")
                    : RefsFile.RefsStringFromList(materialVmts);
                File.WriteAllText(refsPath, refsContent);
                await ImportAndCompileMapRefsAsync(refsPath, paths, s1Content, depsGameDir, project.AddonName, env, ct, project.Import.UseFilelist);
            }
        }
        finally
        {
            FlushLog();
            _compactor = null;
        }
    }

    /// <summary>
    /// Compiles the imported main <c>.vmap</c> to <c>.vmap_c</c> via resourcecompiler
    /// so it can be validated/loaded. The Python importer leaves this to Hammer;
    /// we do it explicitly. Returns true on success (non-throwing).
    /// </summary>
    public async Task<bool> CompileMapAsync(PortProject project, CancellationToken ct = default)
    {
        _compactor = project.Import.CompactLog ? new LogCompactor() : null;
        using var signatures = new VpkSignaturesGuard(_tools.VpkSignatures, Emit);
        // Not fatal here: resourcecompiler works on Source 2 content and never mounts the
        // unsigned S1 csgo\pak01.vpk, so a locked signatures file doesn't stop the compile.
        ReportSignatures(signatures, "compile", fatal: false);
        var paths = new ImportPaths(project.S2GameInfoDir, project.AddonName, project.MapName);
        var vmap = paths.ContentMainVmap;
        if (!File.Exists(vmap))
        {
            Emit($"No imported .vmap to compile at {vmap}");
            return false;
        }

        var env = new Dictionary<string, string> { ["VALVE_NO_AUTO_P4"] = "1" };
        try
        {
            Emit($"Compiling map {Path.GetFileName(vmap)} -> .vmap_c");
            await RunAsync(_tools.ResourceCompiler, "resourcecompiler.exe",
                $"-retail -nop4 -game csgo \"{vmap}\"", env, ct);
            return true;
        }
        catch (ImportToolException ex)
        {
            Emit($"Map compile failed: {ex.Message}");
            return false;
        }
        finally
        {
            FlushLog();
            _compactor = null;
        }
    }

    /// <summary>Which BSP-cleanup mode source1import runs the map import in.</summary>
    internal enum BspMode { None, UseBsp, NoMerge }

    /// <summary>Windows STATUS_ACCESS_VIOLATION (0xC0000005) as a signed process exit code.</summary>
    internal const int AccessViolationExitCode = unchecked((int)0xC0000005);

    internal static BspMode InitialBspMode(ImportOptions o) =>
        o.UseBsp ? BspMode.UseBsp
        : o.UseBspNoMergeInstances ? BspMode.NoMerge
        : BspMode.None;

    /// <summary>
    /// The next, less aggressive BSP mode to try when <paramref name="mode"/> crashes
    /// source1import with an access violation, or null when there is nothing safer left.
    /// The cascade is <c>UseBsp → NoMerge → None</c>:
    /// <list type="bullet">
    /// <item><c>-usebsp</c>'s instance-merge pass can access-violate (after the <c>.vmap</c>
    /// is written, before the refs list) — <c>-usebsp_nomergeinstances</c> skips merging.</item>
    /// <item><c>-usebsp</c>'s vbsp geometry-cleanup pass can <i>also</i> access-violate on some
    /// maps (e.g. de_gracia) — dropping <c>-usebsp</c> entirely (vmf-only geo) avoids vbsp.
    /// Terrain still imports because <see cref="VmfNormalizer.EnsureDisplacementOffsets"/>
    /// repaired the displacements; only vbsp's brush-geo cleanup is lost.</item>
    /// </list>
    /// </summary>
    internal static BspMode? NextFallback(BspMode mode) => mode switch
    {
        BspMode.UseBsp => BspMode.NoMerge,
        BspMode.NoMerge => BspMode.None,
        _ => null, // vmf-only already; no safer geometry mode remains
    };

    private static string FallbackMessage(BspMode to) => to switch
    {
        BspMode.NoMerge =>
            "source1import crashed (access violation) in the -usebsp instance-merge pass — a known Valve " +
            "tool crash. Retrying with -usebsp_nomergeinstances (skips instance merging; a flat/decompiled " +
            "map has nothing to merge)…",
        BspMode.None =>
            "source1import crashed (access violation) in the vbsp geometry pass — retrying with vmf-only " +
            "geometry (no -usebsp). Terrain is preserved by the displacement-offset repair; only vbsp's " +
            "brush-geo cleanup is skipped.",
        _ => "source1import crashed (access violation) — retrying…",
    };

    internal static string BuildMapImportArgs(string s1Game, string s1Content, string addon, string mapName, BspMode bsp)
    {
        var bspArg = bsp switch
        {
            BspMode.UseBsp => "-usebsp ",
            BspMode.NoMerge => "-usebsp_nomergeinstances ",
            _ => "",
        };
        return $"-retail -nop4 -nop4sync {bspArg}-src1gameinfodir \"{s1Game}\" -src1contentdir \"{s1Content}\" -s2addon \"{addon}\" -game csgo maps\\{mapName}.vmf";
    }

    /// <summary>
    /// Runs the main map import, recovering from the known source1import <c>-usebsp</c>
    /// access-violation crashes by degrading the BSP mode one step at a time
    /// (<see cref="NextFallback"/>): merge → no-merge → vmf-only. Returns the mode that
    /// actually imported so the step-5 re-import reuses it. Any non-access-violation exit
    /// (or a crash with no safer mode left) stays fatal (rethrown by RunAsync).
    /// </summary>
    private async Task<BspMode> RunMapImportAsync(
        string s1Game, string s1Content, string addon, string mapName,
        BspMode bspMode, IReadOnlyDictionary<string, string> env, CancellationToken ct)
    {
        while (true)
        {
            try
            {
                await RunAsync(_tools.Source1Import, "source1import.exe",
                    BuildMapImportArgs(s1Game, s1Content, addon, mapName, bspMode), env, ct,
                    standardInput: ConfirmIfNotCsgo(s1Game));
                return bspMode;
            }
            catch (ImportToolException ex)
                when (ex.ExitCode == AccessViolationExitCode && !ct.IsCancellationRequested
                      && NextFallback(bspMode) is { } next)
            {
                Emit(FallbackMessage(next));
                bspMode = next;
            }
        }
    }

    // ---- StripMDLsFromRefs ----
    private static void StripMdlsFromRefs(string refsPath)
    {
        if (!File.Exists(refsPath))
            return;

        var refs = RefsFile.ReadTextFile(refsPath);
        var (mdls, others) = RefsFile.SplitMdlFromRefs(refs);

        var mdlListPath = refsPath.Replace("_refs.txt", "_mdl_lst.txt");
        RefsFile.EnsureFileWritable(mdlListPath);
        File.WriteAllLines(mdlListPath, mdls);

        var newRefsPath = refsPath.Replace("_refs.txt", "_new_refs.txt");
        RefsFile.EnsureFileWritable(newRefsPath);
        File.WriteAllText(newRefsPath, RefsFile.RefsStringFromList(others));
    }

    // ---- ImportAndCompileMapMDLs ----
    private async Task ImportAndCompileMapMdlsAsync(
        string mdlListPath, ImportPaths paths, string s1Game, string s1Content, string depsGameDir, string addon,
        IReadOnlyDictionary<string, string> env, CancellationToken ct, bool useFilelist = false)
    {
        if (!File.Exists(mdlListPath))
            return;

        var mdlFiles = RefsFile.ReadTextFile(mdlListPath);
        if (mdlFiles.Count < 1)
        {
            Emit("No MDLs to import");
            return;
        }

        var s2Content = paths.S2ContentCsgoImported;

        // Resolve each model's extra options sequentially first ("-…" lines apply
        // to the models that follow), so the imports themselves can run in parallel.
        var modelJobs = new List<(string Mdl, string Options)>();
        var extraOptions = "";
        foreach (var entry in mdlFiles)
        {
            if (entry.StartsWith('-'))
                extraOptions = entry is "-" or "-nooptions" ? "" : entry;
            else
                modelJobs.Add((entry.Replace('/', '\\'), extraOptions));
        }

        var parallel = new ParallelOptions { MaxDegreeOfParallelism = _maxParallelism, CancellationToken = ct };
        if (_maxParallelism > 1)
            Emit($"Importing {modelJobs.Count} models with up to {_maxParallelism} parallel workers.");

        // (1) Import each model in parallel; collect its material refs thread-safely.
        // Each cs_mdl_import writes model-specific files (.vmdl + _refs.txt), so the
        // imports are independent.
        var mdlMtls = new ConcurrentDictionary<string, byte>(StringComparer.Ordinal);
        await Parallel.ForEachAsync(modelJobs, parallel, async (job, token) =>
        {
            // Custom (BSP-unpacked) models live under the content root; stock ones under the
            // CS:GO game dir. cs_mdl_import takes a single -i, so pick the root that has the .mdl.
            var modelRoot = File.Exists(Path.Combine(s1Content, job.Mdl)) ? s1Content : s1Game;
            var importArgs = $"-nop4 {job.Options} -i \"{modelRoot}\" -o \"{s2Content}\" \"{job.Mdl}\"".Replace("  ", " ");
            await RunAsync(_tools.ModelImporter, "cs_mdl_import.exe", importArgs, env, token, critical: false);

            var refsName = Path.Combine(s2Content, job.Mdl.Replace(".mdl", "_refs.txt"));
            if (File.Exists(refsName))
            {
                foreach (var mtl in RefsFile.ListStringFromRefs(RefsFile.ReadTextFile(refsName)).Split('\n'))
                    if (mtl.Length > 0)
                        mdlMtls.TryAdd(mtl, 0);
            }
        });

        // (2) Import the materials used by the models in one filelist (single op).
        var mtlListPath = mdlListPath.Replace("mdl_lst", "mtl_lst");
        RefsFile.EnsureFileWritable(mtlListPath);
        File.WriteAllText(mtlListPath, RefsFile.RefsStringFromList(mdlMtls.Keys));

        // -src1gameinfodir = depsGameDir (the custom-gameinfo'd content root for staged maps, so
        // custom model materials resolve from the game path) and -src1contentdir = the content root.
        var importRefsArgs = $"-retail -nop4 -nop4sync -src1gameinfodir \"{depsGameDir}\" -src1contentdir \"{s1Content}\" -s2addon {addon} -game csgo -usefilelist \"{mtlListPath}\"";
        await RunAsync(_tools.Source1Import, "source1import.exe", importRefsArgs, env, ct, critical: false,
            standardInput: ConfirmIfNotCsgo(depsGameDir));

        // (3) Re-apply F_FORCE_UV2 from the global list (sequential — shared file).
        var global2Uv = new HashSet<string>(StringComparer.Ordinal);
        if (File.Exists(_global2UvListPath))
        {
            foreach (var mtl in RefsFile.ReadTextFile(_global2UvListPath))
            {
                global2Uv.Add(mtl);
                ForceUv2ForVmat(s2Content, mtl);
            }
        }

        // (4) Compile materials in parallel — each writes a unique .vmat_c.
        // (Gated by Compile Assets; the imported .vmat sources above are always written.)
        var materials = mdlMtls.Keys.Where(m => m.Length > 0 && !m.StartsWith('-')).ToList();
        if (_compileAssets)
            await Parallel.ForEachAsync(materials, parallel, async (mtl, token) =>
            {
                var vmat = Path.Combine(s2Content, mtl.Replace('/', '\\').Replace(".vmt", ".vmat"));
                await RunAsync(_tools.ResourceCompiler, "resourcecompiler.exe",
                    $"-retail -nop4 -game csgo \"{vmat}\"", env, token, critical: false);
            });

        // (5) The 2-UV pass mutates shared state (the global list and shared .vmat
        // files), so it stays sequential. The F_FORCE_UV2 source-patching always runs
        // (cheap, keeps the .vmat correct for any later compile); only the per-model
        // resourcecompiler invocation is gated by Compile Assets.
        RefsFile.EnsureFileWritable(_global2UvListPath);
        using var global2UvWriter = new StreamWriter(_global2UvListPath, append: true);
        foreach (var (mdlFile, _) in modelJobs)
        {
            var vmdl = Path.Combine(s2Content, mdlFile.Replace(".mdl", ".vmdl"));
            if (!File.Exists(vmdl))
                continue;

            var refsName = Path.Combine(s2Content, mdlFile.Replace(".mdl", "_refs.txt"));
            var force = Force2UvsIfRequired(s2Content, refsName, global2Uv, global2UvWriter);

            if (!_compileAssets)
                continue;

            var f = force ? "-f " : "";
            await RunAsync(_tools.ResourceCompiler, "resourcecompiler.exe",
                $"-retail -nop4 {f}-game csgo \"{vmdl}\"", env, ct, critical: false);
        }
    }

    // ---- ImportAndCompileMapRefs ----
    private async Task ImportAndCompileMapRefsAsync(
        string refsFile, ImportPaths paths, string s1Content, string depsGameDir, string addon,
        IReadOnlyDictionary<string, string> env, CancellationToken ct, bool useFilelist = false)
    {
        if (!File.Exists(refsFile))
            return;

        // -src1gameinfodir = depsGameDir so custom (BSP-unpacked) materials resolve from the game
        // path; -src1contentdir keeps the content root available too.
        var importArgs = $"-retail -nop4 -nop4sync -src1gameinfodir \"{depsGameDir}\" -src1contentdir \"{s1Content}\" -s2addon {addon} -game csgo -usefilelist \"{refsFile}\"";
        await RunAsync(_tools.Source1Import, "source1import.exe", importArgs, env, ct, critical: false,
            standardInput: ConfirmIfNotCsgo(depsGameDir));

        // The refs are now imported as sources; only the compile below is gated.
        if (!_compileAssets)
            return;

        var s2Content = paths.S2ContentCsgoImported;
        var flat = RefsFile.ListStringFromRefs(RefsFile.ReadTextFile(refsFile)).Split('\n');

        var sb = new StringBuilder();
        foreach (var raw in flat)
        {
            if (raw.Length == 0)
                continue;
            var line = raw.Replace(".vmt", ".vmat").Replace(" ", "_");
            sb.Append(Path.Combine(s2Content, line.Replace('/', '\\'))).Append('\n');
        }

        var tmpFile = refsFile.Replace("_new_refs.txt", "_compile_new_refs.txt");
        RefsFile.EnsureFileWritable(tmpFile);
        File.WriteAllText(tmpFile, sb.ToString());

        await RunAsync(_tools.ResourceCompiler, "resourcecompiler.exe",
            $"-retail -nop4 -game csgo -f -filelist \"{tmpFile}\"", env, ct, critical: false);
    }

    // ---- ForceUV2ForVMAT: ensure the vmat has F_FORCE_UV2 right after its "shader" line ----
    private static void ForceUv2ForVmat(string s2Content, string mtlFile)
    {
        var vmat = Path.Combine(s2Content, mtlFile.Replace(".vmt", ".vmat"));
        if (!File.Exists(vmat))
            return;

        var lines = RefsFile.ReadAllLinesShared(vmat).ToList();
        RefsFile.EnsureFileWritable(vmat);

        for (var i = 0; i < lines.Count; i++)
        {
            var txt = lines[i].Trim().ToLowerInvariant();
            if (!txt.StartsWith("\"shader\"", StringComparison.Ordinal))
                continue;

            // line + 1 is safe: there is always at least one more line after "Shader" "x.vfx".
            var next = lines[i + 1].Trim().Replace("\t", "");
            if (!next.StartsWith("\"F_FORCE_UV2\"", StringComparison.Ordinal))
                lines.Insert(i + 1, "\t\"F_FORCE_UV2\" \"1\"");
            break;
        }

        File.WriteAllLines(vmat, lines);
    }

    // ---- Force2UVsIfRequired: returns true if any material in this model is 2-UV ----
    private static bool Force2UvsIfRequired(string s2Content, string refsName, HashSet<string> global2Uv, TextWriter global2UvWriter)
    {
        var meshInfoPath = refsName.Replace("_refs.txt", "_refs/mesh/meshinfo.txt").Replace('/', '\\');
        if (!File.Exists(meshInfoPath) || !File.Exists(refsName))
            return false;

        var numUvs = ParseNumUvs(RefsFile.ReadAllTextShared(meshInfoPath));
        var b2Uv = false;
        var updated = new HashSet<string>(StringComparer.Ordinal);

        foreach (var mtl in RefsFile.ListStringFromRefs(RefsFile.ReadTextFile(refsName)).Split('\n'))
        {
            if (mtl.Length == 0 || !updated.Add(mtl))
                continue;

            if (global2Uv.Contains(mtl))
            {
                b2Uv = true;
            }
            else if (numUvs == 2)
            {
                b2Uv = true;
                global2UvWriter.WriteLine(mtl);
                global2Uv.Add(mtl);
                ForceUv2ForVmat(s2Content, mtl);
            }
        }

        return b2Uv;
    }

    /// <summary>Pulls <c>numuvs</c> out of the model's <c>meshinfo.txt</c> (a Python dict literal).</summary>
    private static int ParseNumUvs(string meshInfo)
    {
        var m = NumUvsRegex().Match(meshInfo);
        return m.Success ? int.Parse(m.Groups[1].Value) : 0;
    }

    // ---- RunCommand: log the banner, run. On non-zero exit, throw if critical
    // (the map import itself) or just warn (a single asset compile/import) so the
    // port completes and the validator can report what's actually missing. ----
    private async Task RunAsync(string toolPath, string fallbackExe, string arguments,
        IReadOnlyDictionary<string, string> env, CancellationToken ct, bool critical = true,
        string? standardInput = null)
    {
        var exe = File.Exists(toolPath) ? toolPath : fallbackExe;
        var display = $"{Path.GetFileName(exe)} {arguments}";

        Emit("--------------------------------");
        Emit("- Running Command: " + display);
        Emit("--------------------------------");

        var exitCode = await _runner.RunAsync(exe, arguments, _workingDir, env, captured: null, ct, standardInput);
        if (exitCode == 0)
            return;

        if (critical)
            throw new ImportToolException($"Error running:\n>>>{display}\nAborting (exit {exitCode})", exitCode);

        Emit($"WARNING: {Path.GetFileName(exe)} exited {exitCode} (continuing): {arguments}");
    }

    [GeneratedRegex(@"[""']?numuvs[""']?\s*[:=]\s*(\d+)", RegexOptions.IgnoreCase)]
    private static partial Regex NumUvsRegex();
}

/// <summary>Thrown when a Valve tool exits non-zero (mirrors <c>utlc.Error</c>'s abort).</summary>
public sealed class ImportToolException(string message, int exitCode = 0) : Exception(message)
{
    /// <summary>The failing tool's process exit code (0 when not supplied).</summary>
    public int ExitCode { get; } = exitCode;
}
