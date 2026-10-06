using Hammer5Tools.Core.Format.Validation;
using Hammer5Tools.Core.IO.Domain;
using Hammer5Tools.Core.IO.Toolchain;

namespace Hammer5Tools.Core.Format.Toolchain;

/// <summary>Outcome of a <see cref="MissingAssetImporter.RepairAsync"/> pass.</summary>
public sealed class MissingAssetRepairReport
{
    /// <summary>Un-imported material/model count in the report the repair started from.</summary>
    public int InitialMissing { get; set; }

    /// <summary>How many import→re-validate rounds actually ran.</summary>
    public int Rounds { get; set; }

    /// <summary>Distinct models the repair attempted to import across all rounds.</summary>
    public int ModelsImported { get; set; }

    /// <summary>Distinct materials the repair attempted to import across all rounds.</summary>
    public int MaterialsImported { get; set; }

    /// <summary>Distinct sources found inside the stock CS:GO VPK archives.</summary>
    public int SourcedFromCsgoVpk { get; set; }

    /// <summary>Distinct sources found in the map's custom content (e.g. a decompiled BSP's unpack).</summary>
    public int SourcedFromCustomContent { get; set; }

    /// <summary>
    /// Tool materials written by the non-binary <c>MaterialConverter</c> fallback because
    /// <c>source1import</c> blacklists them (e.g. <c>tools/toolsclip_*</c>) and won't import them.
    /// </summary>
    public int MaterialsConvertedNonBinary { get; set; }

    /// <summary><c>error.vfx</c> materials remapped to the correct shader from their embedded
    /// <c>legacy_import</c> VMT (e.g. a water material source1import couldn't map).</summary>
    public int ErrorMaterialsRemapped { get; set; }

    /// <summary>
    /// Source paths the repair could not find in either CS:GO VPKs or custom content — genuinely
    /// sourceless assets (e.g. break-model children absent from the BSP unpack and the install).
    /// Reported honestly; never imported.
    /// </summary>
    public List<string> Unsourced { get; } = [];

    /// <summary>The validation report after the final round (the authoritative end state).</summary>
    public ValidationReport FinalReport { get; set; } = new();

    /// <summary>Un-imported material/model count still remaining (couldn't be sourced from S1).</summary>
    public int StillMissing => FinalReport.MissingImportCount;

    /// <summary>How many of the initially-missing materials/models the repair resolved.</summary>
    public int Resolved => Math.Max(0, InitialMissing - StillMissing);
}

/// <summary>
/// Re-imports the materials/models the validator reports as un-imported
/// (<see cref="AssetIssueKind.MissingImport"/>) — the transitive dependencies the main
/// import misses (a model's gib/breakpiece children, a skybox material referenced only by
/// a lighting prefab, …). It maps each missing <c>.vmdl</c>/<c>.vmat</c> back to its
/// Source 1 source (<c>.mdl</c>/<c>.vmt</c>), drives
/// <see cref="MapImportService.ImportSpecificAssetsAsync"/>, then re-validates — looping
/// to a fixpoint because a freshly-imported model can reveal its own missing children. Whatever
/// is still un-imported afterward gets one final <see cref="ForceImportAsync"/> attempt (which,
/// unlike the loop above, fires the toolchain even for a source the locator couldn't find) before
/// giving up; anything that still won't resolve is left in
/// <see cref="MissingAssetRepairReport.FinalReport"/> and reported honestly, never faked.
///
/// Detection stays in <see cref="AssetValidator"/> (no toolchain coupling); this is the
/// separate remediation step that consumes its report.
/// </summary>
public sealed class MissingAssetImporter(MapImportService service, Cs2Install cs2)
{
    /// <summary>Progress banners (per-round summaries). Tool output flows via the service's own log.</summary>
    public event Action<string>? OnLog;

    /// <summary>
    /// Repairs <paramref name="initialReport"/>'s un-imported materials/models against
    /// <paramref name="project"/>, looping at most <paramref name="maxRounds"/> times.
    /// </summary>
    /// <param name="bspPath">The original <c>.bsp</c> (when porting one), so the repair can read its
    /// embedded pakfile directly — finding custom files BSPSource didn't unpack.</param>
    /// <param name="extraContentRoots">Additional custom-content folders to search (e.g. the
    /// <c>.bsp</c>'s own directory).</param>
    public async Task<MissingAssetRepairReport> RepairAsync(
        PortProject project, ValidationReport initialReport, int maxRounds = 4, CancellationToken ct = default,
        string? bspPath = null, IEnumerable<string>? extraContentRoots = null)
    {
        var result = new MissingAssetRepairReport
        {
            InitialMissing = initialReport.MissingImportCount,
            FinalReport = initialReport,
        };

        // Track every S1 source we've already tried so an asset with no source (which keeps
        // reappearing in each report) is attempted once, not every round — this is also what
        // guarantees the loop terminates.
        var attempted = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var unsourced = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var report = initialReport;

        var mergedExtra = new List<string>(extraContentRoots ?? []);
        if (!string.IsNullOrWhiteSpace(bspPath) && File.Exists(bspPath))
        {
            var stagedRoot = MapStaging.GetOrStageBspContentRoot(bspPath, OnLog);
            if (!string.IsNullOrEmpty(stagedRoot) && !mergedExtra.Contains(stagedRoot, StringComparer.OrdinalIgnoreCase))
                mergedExtra.Add(stagedRoot);
        }

        // Search both the stock CS:GO VPKs and the map's custom content for each missing asset's
        // Source 1 source, so we only fire the toolchain at files that actually exist.
        using var locator = new S1SourceLocator(
            project.S1GameInfoDir, project.S1ContentDir, mergedExtra, bspPath);
        OnLog?.Invoke(
            $"Searching {locator.CsgoVpkCount} CS:GO VPK archive(s), custom content, and " +
            $"{locator.BspEmbeddedCount} BSP-embedded file(s) for missing sources…");

        for (var round = 1; round <= maxRounds; round++)
        {
            ct.ThrowIfCancellationRequested();

            var (allModels, allMaterials) = PlanFromReport(report);
            var models = Classify(allModels, "m|", locator, attempted, unsourced, result, "model");
            var materials = Classify(allMaterials, "t|", locator, attempted, unsourced, result, "material");

            // Tool materials (e.g. tools/toolsclip_*) are blacklisted by source1import — it refuses
            // to import them. Pull them out of both groups and convert them with the non-binary
            // MaterialConverter (which emits a correct, texture-free `generic.vfx` tools .vmat).
            var toolMaterials = ExtractToolMaterials(materials.Stock)
                .Concat(ExtractToolMaterials(materials.Custom)).ToList();

            var total = models.Stock.Count + models.Custom.Count
                + materials.Stock.Count + materials.Custom.Count + toolMaterials.Count;
            if (total == 0)
                break;

            OnLog?.Invoke(
                $"Repair round {round}: importing {models.Stock.Count + models.Custom.Count} model(s), " +
                $"{materials.Stock.Count + materials.Custom.Count} material(s), and converting " +
                $"{toolMaterials.Count} tool material(s) the importer missed…");

            // Stock (CS:GO VPK) assets import through the real csgo gameinfo dir (stockOnly: true);
            // custom (BSP-unpacked) assets through the staged content root. Mixing them makes
            // source1import miss the stock ones — see ImportSpecificAssetsAsync.
            if (models.Stock.Count > 0 || materials.Stock.Count > 0)
                await service.ImportSpecificAssetsAsync(project, models.Stock, materials.Stock, ct, stockOnly: true);
            var customProject = CustomContentProject(project, locator, mergedExtra, materials.Custom, models.Custom);

            // Custom assets the locator found only in the BSP's embedded pakfile aren't on disk, so
            // source1import/cs_mdl_import can't read them — extract them (and a material's textures)
            // into the staged content root first.
            ExtractBspEmbeddedToDisk(customProject, locator, materials.Custom, models.Custom);

            if (models.Custom.Count > 0 || materials.Custom.Count > 0)
                await service.ImportSpecificAssetsAsync(customProject, models.Custom, materials.Custom, ct);

            var converted = ConvertToolMaterials(project, locator, toolMaterials);
            result.MaterialsConvertedNonBinary += converted;

            result.ModelsImported += models.Stock.Count + models.Custom.Count;
            result.MaterialsImported += materials.Stock.Count + materials.Custom.Count;
            result.Rounds = round;

            // Re-validate to confirm what resolved and surface any deeper transitive deps.
            report = new AssetValidator(cs2, project.AddonName).Validate(null, ct);
            result.FinalReport = report;

            OnLog?.Invoke(
                $"Repair round {round} complete: {report.MissingImportCount} material/model(s) still un-imported.");
        }

        // Anything still un-imported after the locate-then-import loop above gets one final "force"
        // attempt: unlike the loop, ForceImportAsync fires the toolchain even for a source the
        // locator couldn't find, so it occasionally resolves what the loop gave up on and always
        // leaves the tool's own diagnostic in the log instead of a silent "no source found".
        if (report.MissingImportCount > 0)
        {
            var (remModels, remMaterials) = PlanFromReport(report);
            var remaining = remModels.Concat(remMaterials).ToList();
            if (remaining.Count > 0)
            {
                OnLog?.Invoke(
                    $"{remaining.Count} asset(s) still un-imported after {result.Rounds} round(s) — forcing a final import attempt…");
                var forced = await ForceImportAsync(project, remaining, ct, bspPath, extraContentRoots);
                result.ModelsImported += forced.ModelsImported;
                result.MaterialsImported += forced.MaterialsImported;
                result.SourcedFromCsgoVpk += forced.SourcedFromCsgoVpk;
                result.SourcedFromCustomContent += forced.SourcedFromCustomContent;
                result.MaterialsConvertedNonBinary += forced.MaterialsConvertedNonBinary;
                unsourced.UnionWith(forced.Unsourced);

                report = new AssetValidator(cs2, project.AddonName).Validate(null, ct);
                result.FinalReport = report;
                OnLog?.Invoke(
                    $"Forced import complete: {report.MissingImportCount} material/model(s) still un-imported.");
            }
        }

        // Fix any material source1import left as error.vfx (e.g. water) by re-converting its embedded
        // legacy_import VMT — independent of the missing-import loop above (these .vmat exist on disk).
        var remap = Materials.ErrorVmatRemapper.FixAddon(cs2.ContentAddonDir(project.AddonName), OnLog);
        result.ErrorMaterialsRemapped = remap.Remapped;
        if (remap.Remapped > 0)
            OnLog?.Invoke($"Remapped {remap.Remapped} error.vfx material(s) to the correct shader.");

        result.Unsourced.AddRange(unsourced.OrderBy(s => s, StringComparer.OrdinalIgnoreCase));
        if (result.Unsourced.Count > 0)
            OnLog?.Invoke(
                $"{result.Unsourced.Count} asset(s) had no Source 1 source in the CS:GO VPKs or custom content — left as missing.");

        return result;
    }

    /// <summary>
    /// "Asset force import": imports an explicit, user-supplied list of Source 1 assets
    /// (<c>models/…/x.mdl</c>, <c>materials/…/y.vmt</c>, textures) into the addon — with their
    /// references, since each <c>.mdl</c> goes through the model pass that also imports the
    /// materials it uses. Unlike <see cref="RepairAsync"/> there is no validation loop: the user
    /// says what to port, so a path that can't be sourced is still attempted (and reported), which
    /// is what "force" means here.
    /// <para>Reuses <see cref="MissingAssetRepairReport"/> for the counts; the validation-only
    /// fields (<c>InitialMissing</c>, <c>FinalReport</c>, …) stay unset.</para>
    /// </summary>
    public async Task<MissingAssetRepairReport> ForceImportAsync(
        PortProject project, IEnumerable<string> assetPaths, CancellationToken ct = default,
        string? bspPath = null, IEnumerable<string>? extraContentRoots = null)
    {
        var result = new MissingAssetRepairReport { Rounds = 1 };

        // Parse free-text asset paths into normalized S1 source paths (.vmdl -> .mdl, .vmat -> .vmt, .vtex -> .vtf, drop _c)
        var parsedSources = ParseAssetList(string.Join("\n", assetPaths));

        var models = new List<string>();
        var refs = new List<string>();
        foreach (var path in parsedSources)
            (path.EndsWith(".mdl", StringComparison.OrdinalIgnoreCase) ? models : refs).Add(path);

        var mergedExtra = new List<string>(extraContentRoots ?? []);
        if (!string.IsNullOrWhiteSpace(bspPath) && File.Exists(bspPath))
        {
            var stagedRoot = MapStaging.GetOrStageBspContentRoot(bspPath, OnLog);
            if (!string.IsNullOrEmpty(stagedRoot) && !mergedExtra.Contains(stagedRoot, StringComparer.OrdinalIgnoreCase))
                mergedExtra.Add(stagedRoot);
        }

        using var locator = new S1SourceLocator(
            project.S1GameInfoDir, project.S1ContentDir, mergedExtra, bspPath);
        var attempted = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var unsourced = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        var m = Classify(models, "m|", locator, attempted, unsourced, result, "model", importUnsourced: true);
        var t = Classify(refs, "t|", locator, attempted, unsourced, result, "material", importUnsourced: true);

        // source1import blacklists tool materials — convert those non-binarily instead (as the repair does).
        var toolMaterials = ExtractToolMaterials(t.Stock).Concat(ExtractToolMaterials(t.Custom)).ToList();

        OnLog?.Invoke($"Force importing {m.Stock.Count + m.Custom.Count} model(s) and " +
                      $"{t.Stock.Count + t.Custom.Count} material/texture(s)…");

        if (m.Stock.Count > 0 || t.Stock.Count > 0)
            await service.ImportSpecificAssetsAsync(project, m.Stock, t.Stock, ct, stockOnly: true);

        var customProject = CustomContentProject(project, locator, mergedExtra, t.Custom, m.Custom);

        ExtractBspEmbeddedToDisk(customProject, locator, t.Custom, m.Custom);
        if (m.Custom.Count > 0 || t.Custom.Count > 0)
            await service.ImportSpecificAssetsAsync(customProject, m.Custom, t.Custom, ct);

        result.MaterialsConvertedNonBinary = ConvertToolMaterials(project, locator, toolMaterials);
        result.ModelsImported = m.Stock.Count + m.Custom.Count;
        result.MaterialsImported = t.Stock.Count + t.Custom.Count;
        result.Unsourced.AddRange(unsourced.OrderBy(s => s, StringComparer.OrdinalIgnoreCase));
        return result;
    }

    /// <summary>
    /// Parses the free-text asset list of the force-import tool into Source 1 source paths: one per
    /// line, either slash style, optionally quoted, blank and <c>//</c>/<c>#</c> lines skipped, and
    /// Source 2 output extensions mapped back to their source (<c>.vmdl</c>→<c>.mdl</c>,
    /// <c>.vmat</c>→<c>.vmt</c>, <c>.vtex</c>→<c>.vtf</c>, trailing <c>_c</c> dropped) so a path
    /// copied straight out of a compile error works as typed. Duplicates removed, order preserved.
    /// Pure and side-effect-free so it can be unit-tested without a CS2 install.
    /// </summary>
    public static List<string> ParseAssetList(string text)
    {
        var paths = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var raw in text.Split('\n'))
        {
            var line = raw.Trim().Trim('"').Trim();
            if (line.Length == 0 || line.StartsWith("//", StringComparison.Ordinal) || line.StartsWith('#'))
                continue;

            var path = line.Replace('\\', '/').TrimStart('/');
            if (path.EndsWith("_c", StringComparison.OrdinalIgnoreCase))
                path = path[..^2];
            path = Path.GetExtension(path).ToLowerInvariant() switch
            {
                ".vmdl" => path[..^5] + ".mdl",
                ".vmat" => path[..^5] + ".vmt",
                ".vtex" => path[..^5] + ".vtf",
                _ => path,
            };

            if (seen.Add(path))
                paths.Add(path);
        }
        return paths;
    }

    /// <summary>
    /// The project to run the custom-content dependency import against: <paramref name="project"/>
    /// with <c>S1ContentDir</c> pointed at the root that actually holds
    /// <paramref name="materials"/>/<paramref name="models"/>.
    /// <para>
    /// <c>source1import</c> mounts a single <c>-src1contentdir</c>, while the staging area keeps one
    /// folder per previously-ported map and the caller hands us all of them. Taking the first of
    /// those ran a <c>de_swamp</c> import against a leftover <c>cs_climb_a71</c> unpack, so every
    /// material came back <c>*** Found no files matching specification</c>. The locator already knows
    /// which root each source was found in — ask it, and only fall back to "first root that exists"
    /// when nothing is loose on disk (e.g. everything is still inside the BSP pakfile).
    /// </para>
    /// </summary>
    private static PortProject CustomContentProject(
        PortProject project, S1SourceLocator locator, IEnumerable<string> extraRoots,
        IEnumerable<string> materials, IEnumerable<string> models)
    {
        var customDir =
            materials.Concat(models)
                .Select(locator.TryGetCustomRoot)
                .FirstOrDefault(root => !string.IsNullOrEmpty(root))
            ?? extraRoots.FirstOrDefault(dir => Directory.Exists(dir) && !PathsEqual(dir, project.S1GameInfoDir))
            ?? project.S1ContentDir;

        if (string.IsNullOrEmpty(customDir)
            || PathsEqual(customDir, project.S1GameInfoDir)
            || PathsEqual(customDir, project.S1ContentDir))
            return project;

        return new PortProject
        {
            S2GameInfoDir = project.S2GameInfoDir,
            S1GameInfoDir = project.S1GameInfoDir,
            S1ContentDir = customDir,
            AddonName = project.AddonName,
            MapName = project.MapName,
            Import = project.Import
        };
    }

    /// <summary>
    /// Splits sources into those found in the stock CS:GO VPKs vs the map's custom content (the two
    /// import through different gameinfo dirs), recording where each came from and collecting the
    /// genuinely-sourceless ones. Each source is considered once (the <paramref name="attempted"/>
    /// set) so a sourceless asset that reappears every round is not re-searched — this also bounds
    /// the loop. With <paramref name="importUnsourced"/> a source that isn't found anywhere is still
    /// attempted (as stock) instead of skipped — what the user-driven "force import" wants, so the
    /// tool's own error surfaces for a path it typed.
    /// </summary>
    private (List<string> Stock, List<string> Custom) Classify(
        IEnumerable<string> sources, string keyPrefix, S1SourceLocator locator,
        HashSet<string> attempted, HashSet<string> unsourced,
        MissingAssetRepairReport result, string kindLabel, bool importUnsourced = false)
    {
        var stock = new List<string>();
        var custom = new List<string>();
        foreach (var source in sources)
        {
            if (!attempted.Add(keyPrefix + source))
                continue; // already considered in an earlier round

            switch (locator.Locate(source.Replace('\\', '/')))
            {
                case S1Source.CustomContent:
                    result.SourcedFromCustomContent++;
                    custom.Add(source);
                    break;
                case S1Source.CsgoVpk:
                    result.SourcedFromCsgoVpk++;
                    stock.Add(source);
                    break;
                default:
                    unsourced.Add(source);
                    OnLog?.Invoke($"No Source 1 source found for {kindLabel}: {source}");
                    if (importUnsourced)
                        stock.Add(source);
                    break;
            }
        }
        return (stock, custom);
    }

    /// <summary>
    /// Removes tool materials (which <c>source1import</c> blacklists) from <paramref name="materials"/>
    /// and returns them, so they can be converted non-binarily instead. A material is a tool material
    /// when its <c>.vmt</c> has <c>%compile*</c> keys or it lives under <c>materials/tools/</c>.
    /// </summary>
    internal static List<string> ExtractToolMaterials(List<string> materials)
    {
        var tools = new List<string>();
        materials.RemoveAll(vmt =>
        {
            var isTool = Materials.VmtFile.IsToolMaterialPath(vmt);
            if (isTool)
                tools.Add(vmt);
            return isTool;
        });
        return tools;
    }

    // Common .vmt keys whose value is a texture path (extension-less, under materials/).
    private static readonly string[] TextureKeys =
    [
        "$basetexture", "$basetexture2", "$basetexture3", "$basetexture4", "$bumpmap", "$normalmap",
        "$bumpmap2", "$normalmap2", "$envmapmask", "$detail", "$blendmodulatetexture",
        "$phongexponenttexture", "$selfillummask", "$ao", "$tintmasktexture",
    ];

    // Sibling files cs_mdl_import needs alongside a .mdl.
    private static readonly string[] ModelSiblings = [".vvd", ".dx90.vtx", ".dx80.vtx", ".vtx", ".phy", ".ani"];

    /// <summary>
    /// Extracts custom assets that exist only in the BSP's embedded pakfile (not unpacked to disk)
    /// into the staged content root, so the toolchain can read them: each <c>.mdl</c> with its
    /// render/physics siblings, and each <c>.vmt</c> with the <c>.vtf</c> textures it references.
    /// </summary>
    private void ExtractBspEmbeddedToDisk(
        PortProject project, S1SourceLocator locator,
        IReadOnlyList<string> materialVmts, IReadOnlyList<string> modelMdls)
    {
        var root = project.S1ContentDir;
        if (string.IsNullOrEmpty(root))
            return;

        foreach (var mdl in modelMdls)
        {
            var forward = mdl.Replace('\\', '/');
            Extract(locator, root, forward);
            var stem = forward[..^4]; // drop ".mdl"
            foreach (var ext in ModelSiblings)
                Extract(locator, root, stem + ext);
        }

        foreach (var vmt in materialVmts)
        {
            var forward = vmt.Replace('\\', '/');
            Extract(locator, root, forward);

            var text = locator.TryReadText(forward);
            if (text is null)
                continue;
            var parsed = Materials.VmtFile.Parse(text);
            foreach (var key in TextureKeys)
            {
                var tex = parsed[key];
                if (string.IsNullOrWhiteSpace(tex))
                    continue;
                var vtf = "materials/" + tex.Replace('\\', '/').Trim('/') + ".vtf";
                Extract(locator, root, vtf);
            }
        }
    }

    /// <summary>Writes a pakfile-only source into <paramref name="root"/> on disk (no-op otherwise).</summary>
    private void Extract(S1SourceLocator locator, string root, string forwardPath)
    {
        if (!locator.IsOnlyInBspPak(forwardPath))
            return;
        var bytes = locator.TryReadBytes(forwardPath);
        if (bytes is null)
            return;
        try
        {
            var outPath = Path.Combine(root, forwardPath.Replace('/', Path.DirectorySeparatorChar));
            Directory.CreateDirectory(Path.GetDirectoryName(outPath)!);
            File.WriteAllBytes(outPath, bytes);
            OnLog?.Invoke($"Extracted BSP-embedded file: {forwardPath}");
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            OnLog?.Invoke($"Could not extract {forwardPath}: {ex.Message}");
        }
    }

    /// <summary>
    /// Writes a <c>.vmat</c> for each tool material straight from its located <c>.vmt</c> via the
    /// non-binary <see cref="Materials.MaterialConverter"/> — no toolchain. Returns the count written.
    /// </summary>
    private int ConvertToolMaterials(PortProject project, S1SourceLocator locator, IReadOnlyList<string> toolVmts)
    {
        if (toolVmts.Count == 0)
            return 0;

        var contentRoot = cs2.ContentAddonDir(project.AddonName);
        var converted = 0;
        foreach (var vmt in toolVmts)
        {
            var forward = vmt.Replace('\\', '/');
            var text = locator.TryReadText(forward);
            if (text is null)
                continue;

            try
            {
                var parsed = Materials.VmtFile.Parse(text, locator.TryReadText, sourcePath: forward);
                var doc = new Materials.VmtToVmatConverter().Convert(parsed);

                var rel = Path.ChangeExtension(forward, ".vmat").Replace('/', Path.DirectorySeparatorChar);
                var outPath = Path.Combine(contentRoot, rel);
                Directory.CreateDirectory(Path.GetDirectoryName(outPath)!);
                File.WriteAllText(outPath, doc.ToText(Path.GetFileName(forward)));
                converted++;
                OnLog?.Invoke($"Converted tool material (non-binary): {forward}");
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
            {
                OnLog?.Invoke($"Could not write tool material {forward}: {ex.Message}");
            }
        }
        return converted;
    }

    /// <summary>
    /// Maps a report's un-imported (<see cref="AssetIssueKind.MissingImport"/>) materials,
    /// models, and textures back to the Source 1 source paths <c>cs_mdl_import</c>/
    /// <c>source1import</c> consume — <c>.vmdl</c>→<c>.mdl</c>, <c>.vmat</c>→<c>.vmt</c>,
    /// and a texture reference (<c>.tga</c>/<c>.png</c>/<c>.psd</c> under <c>materials/</c>)
    /// → the <c>.vtf</c> at the same path. Pure and side-effect-free so it can be unit-tested
    /// without a CS2 install.
    /// </summary>
    public static (List<string> Models, List<string> Materials) PlanFromReport(ValidationReport report)
    {
        var models = new List<string>();
        var materials = new List<string>();
        foreach (var issue in report.Issues)
        {
            if (issue.Kind != AssetIssueKind.MissingImport || issue.ReferencePath is null)
                continue;

            var path = issue.ReferencePath;
            if (path.EndsWith(".vmdl", StringComparison.OrdinalIgnoreCase))
                models.Add(path[..^5] + ".mdl");
            else if (path.EndsWith(".vmat", StringComparison.OrdinalIgnoreCase))
                materials.Add(path[..^5] + ".vmt");
            else if (IsTextureRef(path))
                materials.Add(Path.ChangeExtension(path, ".vtf"));
        }
        return (models, materials);
    }

    // A texture reference a .vmat points at (.tga/.png/.psd under materials/). Used both to
    // recognise the issue in PlanFromReport and to keep the validator's existence check aligned.
    private static bool IsTextureRef(string path) =>
        path.StartsWith("materials/", StringComparison.OrdinalIgnoreCase)
        && (path.EndsWith(".tga", StringComparison.OrdinalIgnoreCase)
            || path.EndsWith(".png", StringComparison.OrdinalIgnoreCase)
            || path.EndsWith(".psd", StringComparison.OrdinalIgnoreCase));

    private static bool PathsEqual(string a, string b)
    {
        static string Norm(string p) => Path.TrimEndingDirectorySeparator(
            Path.GetFullPath(p)).Replace('/', '\\');
        try
        {
            return string.Equals(Norm(a), Norm(b), StringComparison.OrdinalIgnoreCase);
        }
        catch
        {
            return string.Equals(a, b, StringComparison.OrdinalIgnoreCase);
        }
    }
}
