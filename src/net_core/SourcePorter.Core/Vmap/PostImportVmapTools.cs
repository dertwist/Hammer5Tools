using SourcePorter.Core.Domain;
using SourcePorter.Core.Toolchain;

namespace SourcePorter.Core.Vmap;

/// <summary>
/// The post-import <c>.vmap</c> tools the GUI and CLI run after an import (each behind an
/// opt-in checkbox / flag): <see cref="CollapsePrefabs"/> and <see cref="CreateSkyboxTemplate"/>.
/// Resolves the imported main map's path from the install + addon + map name the same way
/// <c>MapImportService.CompileMapAsync</c> does, so both front-ends call these identically —
/// the pattern <see cref="Validation.AssetValidator"/> / <see cref="Validation.AddonStats"/> use.
/// </summary>
public static class PostImportVmapTools
{
    /// <summary>Merges the map's prefab / sub-map references into the root map (see <see cref="VmapPrefabCollapser"/>).</summary>
    public static VmapPrefabCollapser.Result CollapsePrefabs(
        Cs2Install cs2, string addon, string mapName, Action<string>? log = null, CancellationToken ct = default)
    {
        var mainVmap = ResolveMainVmap(cs2, addon, mapName);
        log?.Invoke("▶ Collapse prefabs: merging sub-maps into the root map…");
        if (!File.Exists(mainVmap))
        {
            log?.Invoke($"  No imported .vmap at {mainVmap} — skipping.");
            return new VmapPrefabCollapser.Result(0, 0, 0, []);
        }

        var doc = VmapDocument.Load(mainVmap);
        var result = VmapPrefabCollapser.Collapse(doc, cs2.ContentAddonDir(addon), log, ct);
        if (result.DidAnything)
        {
            var backup = VmapBackup.Backup(mainVmap, log);
            doc.Save();
            log?.Invoke($"  Collapsed {result.ReferencesMerged} reference(s), moved {result.NodesMoved} node(s) into the root map.");

            foreach (var file in result.MergedFiles)
            {
                try { File.Delete(file); log?.Invoke($"  Deleted sub-map: {System.IO.Path.GetFileName(file)}"); }
                catch (Exception ex) { log?.Invoke($"  WARNING: could not delete {System.IO.Path.GetFileName(file)}: {ex.Message}"); }
            }

            try { File.Delete(backup); log?.Invoke($"  Deleted backup: {System.IO.Path.GetFileName(backup)}"); }
            catch (Exception ex) { log?.Invoke($"  WARNING: could not delete backup {System.IO.Path.GetFileName(backup)}: {ex.Message}"); }
        }
        return result;
    }

    /// <summary>
    /// Corrects brush-face UV scale for custom (BSP-unpacked) materials across the addon's maps
    /// (see <see cref="VmapBrushUvFixer"/>). Needs the staged content root to read the real texture
    /// dimensions source1import couldn't.
    /// </summary>
    public static VmapBrushUvFixer.Result FixBrushUvScale(
        Cs2Install cs2, string addon, string mapName, string? stagedContentRoot,
        Action<string>? log = null, CancellationToken ct = default)
    {
        var mapsDir = Path.Combine(cs2.ContentAddonDir(addon), "maps");
        return VmapBrushUvFixer.FixAddon(mapsDir, mapName, stagedContentRoot, log, ct);
    }

    /// <summary>
    /// Removes redundant single-child / empty <c>CMapGroup</c> wrappers across the addon's maps
    /// (main + prefab sub-maps) to shrink the <c>.vmap</c> (see <see cref="VmapGroupFlattener"/>).
    /// </summary>
    public static VmapGroupFlattener.Result FlattenSingleChildGroups(
        Cs2Install cs2, string addon, Action<string>? log = null, CancellationToken ct = default)
    {
        var mapsDir = Path.Combine(cs2.ContentAddonDir(addon), "maps");
        return VmapGroupFlattener.FlattenAddon(mapsDir, log, ct);
    }

    /// <summary>Scaffolds the 3D-skybox template for the map (see <see cref="VmapSkyboxTemplate"/>).</summary>
    public static VmapSkyboxTemplate.Result CreateSkyboxTemplate(
        Cs2Install cs2, string addon, string mapName, Action<string>? log = null, CancellationToken ct = default)
    {
        var mainVmap = ResolveMainVmap(cs2, addon, mapName);
        log?.Invoke("▶ Skybox template: scaffolding the 3D skybox…");
        if (!File.Exists(mainVmap))
        {
            log?.Invoke($"  No imported .vmap at {mainVmap} — skipping.");
            return new VmapSkyboxTemplate.Result(false, false, "");
        }

        return VmapSkyboxTemplate.Create(mainVmap, log, ct);
    }

    private static string ResolveMainVmap(Cs2Install cs2, string addon, string mapName) =>
        new ImportPaths(cs2.S2GameInfoDir, addon, mapName).ContentMainVmap;
}
