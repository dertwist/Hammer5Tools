using System.Numerics;
using Datamodel;
using SourcePorter.Core.Materials;

namespace SourcePorter.Core.Vmap;

/// <summary>
/// Post-import fix for brush-face UV scale on custom (BSP-unpacked) materials.
/// <para>
/// When <c>source1import</c> imports a decompiled BSP whose custom <c>.vmt</c>/<c>.vtf</c> it
/// can't read (<c>GetMappingDimensionsForVMT: can't open …</c>), it bakes that face's texture
/// mapping using a fixed fallback texture size of <b>16×16</b> instead of the real dimensions — so
/// the stored per-face <c>textureScale</c> is off by <c>16/realDim</c> AND the baked per-corner
/// <c>texcoord</c> (which the renderer uses directly) is wrong. For every face whose material's
/// real texture dimensions we can read from the staged content this:
/// </para>
/// <list type="number">
///   <item>corrects <c>textureScale</c> back to the true S1 scale (× <c>realDim/16</c>); and</item>
///   <item><b>recomputes</b> each corner's <c>texcoord</c> from the corrected mapping, the same way
///   Hammer does on edit:
///   <c>u = (dot(P, axisU.xyz) / scale.u + axisU.w) / textureWidth</c> (and likewise for v).</item>
/// </list>
/// <para>
/// The texcoord is <b>recomputed</b>, not scaled — scaling the 16-default texcoord cannot reproduce
/// the correct value because the per-face offset (<c>axis.w / dim</c>) and slope
/// (<c>1 / (scale·dim)</c>) transform differently. This was confirmed against a Hammer-corrected
/// <c>.vmap</c>: for a <c>blend_roofing_tile_01</c> face (scale 0.125, axisU.w 97.82, 1024px),
/// <c>(11.7148/0.125 + 97.82)/1024 = 0.18705</c> exactly matched Hammer's re-baked texcoord.
/// </para>
/// Stock materials — whose <c>.vtf</c> source1import <i>could</i> read — aren't in the staged
/// content, so they're skipped and left untouched (no false positives). The texture axes are
/// already correct (dimension-independent) and are left as-is.
/// </summary>
public static class VmapBrushUvFixer
{
    /// <summary>The texture size source1import assumes when it can't read a custom <c>.vtf</c>.</summary>
    private const float FallbackDim = 16f;

    public sealed record Result(int FilesChanged, int FacesFixed, int MaterialsFixed)
    {
        public bool DidAnything => FilesChanged > 0;
    }

    /// <summary>
    /// Fixes the imported map <paramref name="mapName"/>'s own <c>.vmap</c>s under
    /// <paramref name="addonContentMapsDir"/> — the main <c>&lt;map&gt;.vmap</c> and its
    /// <c>prefabs/&lt;map&gt;/</c> sub-maps only — reading real texture dimensions from
    /// <paramref name="stagedContentRoot"/>. It is deliberately scoped to those files: the rescale
    /// is NOT idempotent, so it must never touch unrelated <c>.vmap</c>s a user may have placed in
    /// the maps dir (e.g. hand-saved copies), or it would double-apply the correction. Each changed
    /// file is backed up first. No-op when the staged content is gone or the map has no
    /// custom-material faces.
    /// </summary>
    public static Result FixAddon(
        string addonContentMapsDir, string mapName, string? stagedContentRoot,
        Action<string>? log = null, CancellationToken ct = default)
    {
        log?.Invoke("▶ Brush UV fix: correcting custom-material texture scale…");
        if (string.IsNullOrEmpty(stagedContentRoot) || !Directory.Exists(stagedContentRoot))
        {
            log?.Invoke("  No staged content available (real texture sizes unknown) — skipping.");
            return new Result(0, 0, 0);
        }
        if (!Directory.Exists(addonContentMapsDir))
        {
            log?.Invoke($"  No maps dir at {addonContentMapsDir} — skipping.");
            return new Result(0, 0, 0);
        }

        var dimCache = new Dictionary<string, (float W, float H)?>(StringComparer.OrdinalIgnoreCase);
        int filesChanged = 0, facesFixed = 0, materialsFixed = 0;

        foreach (var vmap in MapVmaps(addonContentMapsDir, mapName))
        {
            ct.ThrowIfCancellationRequested();

            // Idempotency guard: the rescale is NOT safe to apply twice (it would multiply the scale
            // again). A sidecar marker newer than the .vmap means we already fixed this exact file;
            // a re-import rewrites the .vmap (making it newer than the marker) so the fix re-runs on
            // the fresh, unfixed data. Protects against any flow that re-runs without re-importing.
            if (AlreadyFixed(vmap))
            {
                log?.Invoke($"  {Path.GetFileName(vmap)}: already fixed (skipping to avoid double-scaling).");
                continue;
            }

            VmapDocument doc;
            try { doc = VmapDocument.LoadInMemory(vmap); }
            catch (Exception ex) { log?.Invoke($"  WARNING: couldn't read {Path.GetFileName(vmap)}: {ex.Message}"); continue; }

            var (faces, mats) = FixDocument(doc, stagedContentRoot, dimCache, ct);
            if (faces == 0)
                continue;

            // Back up, overwrite, then drop the backup on success — the .vmap is regenerated by
            // every import, so keeping a (potentially tens-of-MB) .bak per prefab per run just bloats.
            var backup = VmapBackup.Backup(vmap, log);
            doc.Save();
            try { File.Delete(backup); }
            catch (Exception ex) { log?.Invoke($"  WARNING: could not delete backup {Path.GetFileName(backup)}: {ex.Message}"); }
            MarkFixed(vmap);
            filesChanged++;
            facesFixed += faces;
            materialsFixed += mats;
            log?.Invoke($"  {Path.GetFileName(vmap)}: rescaled {faces} face(s) across {mats} custom material(s).");
        }

        if (filesChanged == 0)
            log?.Invoke("  No custom-material brush faces needed rescaling.");
        else
            log?.Invoke($"  Brush UV fix complete: {facesFixed} face(s) in {filesChanged} file(s).");
        return new Result(filesChanged, facesFixed, materialsFixed);
    }

    /// <summary>The imported map's own <c>.vmap</c>s: the main <c>&lt;map&gt;.vmap</c> plus every
    /// <c>.vmap</c> under <c>prefabs/&lt;map&gt;/</c> (the auto-split gameplay/environment/lighting/
    /// cubemap sub-maps). Excludes any unrelated <c>.vmap</c> a user dropped in the maps dir.</summary>
    internal static IEnumerable<string> MapVmaps(string mapsDir, string mapName)
    {
        var main = Path.Combine(mapsDir, mapName + ".vmap");
        if (File.Exists(main))
            yield return main;

        var prefabDir = Path.Combine(mapsDir, "prefabs", mapName);
        if (Directory.Exists(prefabDir))
            foreach (var f in Directory.EnumerateFiles(prefabDir, "*.vmap", SearchOption.AllDirectories))
                yield return f;
    }

    /// <summary>
    /// The Source 2 brush-face UV formula (matches Hammer): for a vertex world position
    /// <paramref name="p"/>, the per-face texture axes (xyz direction + w offset) and the corrected
    /// per-axis <c>textureScale</c>, the baked texcoord is
    /// <c>u = (dot(P, axisU.xyz)/scaleU + axisU.w) / textureWidth</c> (and likewise for v).
    /// Confirmed bit-for-bit against a Hammer-corrected <c>.vmap</c>.
    /// </summary>
    internal static Vector2 RecomputeTexcoord(
        Vector3 p, Vector4 axisU, Vector4 axisV, float scaleU, float scaleV, float dimW, float dimH)
    {
        var u = (Vector3.Dot(p, new Vector3(axisU.X, axisU.Y, axisU.Z)) / scaleU + axisU.W) / dimW;
        var v = (Vector3.Dot(p, new Vector3(axisV.X, axisV.Y, axisV.Z)) / scaleV + axisV.W) / dimH;
        return new Vector2(u, v);
    }

    private static string MarkerPath(string vmap) => vmap + ".spuvfix";

    /// <summary>True when a marker exists and is at least as new as the <c>.vmap</c> (a re-import
    /// rewrites the .vmap newer than the marker, so the fix re-runs on fresh data).</summary>
    private static bool AlreadyFixed(string vmap)
    {
        var marker = MarkerPath(vmap);
        return File.Exists(marker)
            && File.GetLastWriteTimeUtc(marker) >= File.GetLastWriteTimeUtc(vmap);
    }

    /// <summary>Writes/updates the sidecar marker (mtime now &gt; the just-saved .vmap).</summary>
    private static void MarkFixed(string vmap)
    {
        try { File.WriteAllText(MarkerPath(vmap), "brush uv scale fixed"); }
        catch { /* marker is best-effort; a failure just means the guard can't short-circuit later */ }
    }

    /// <summary>Fixes one loaded document in place; returns (facesFixed, distinctMaterialsFixed).</summary>
    private static (int Faces, int Materials) FixDocument(
        VmapDocument doc, string stagedContentRoot,
        Dictionary<string, (float W, float H)?> dimCache, CancellationToken ct)
    {
        int faces = 0;
        var materials = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var seen = new HashSet<Element>();

        void Walk(Element? e)
        {
            if (e is null || !seen.Add(e))
                return;
            if (e.ClassName == "CDmePolygonMesh")
                faces += FixMesh(e, stagedContentRoot, dimCache, materials, ct);
            foreach (var kv in e)
            {
                if (kv.Value is Element c) Walk(c);
                else if (kv.Value is ElementArray a)
                    foreach (var x in a) Walk(x);
            }
        }
        Walk(doc.Model.Root);
        return (faces, materials.Count);
    }

    private static int FixMesh(
        Element mesh, string stagedContentRoot,
        Dictionary<string, (float W, float H)?> dimCache, HashSet<string> materialsFixed, CancellationToken ct)
    {
        if (Get(mesh, "materials") is not StringArray materials)
            return 0;

        var texScale = StreamList<Vector2>(mesh, "faceData", "textureScale");
        var matIndex = StreamList<int>(mesh, "faceData", "materialindex");
        var axisU = StreamList<Vector4>(mesh, "faceData", "textureAxisU");
        var axisV = StreamList<Vector4>(mesh, "faceData", "textureAxisV");
        var texcoord = StreamList<Vector2>(mesh, "faceVertexData", "texcoord");
        var positions = StreamList<Vector3>(mesh, "vertexData", "position");
        var faceEdge = Get(mesh, "faceEdgeIndices") as IList<int>;
        var edgeNext = Get(mesh, "edgeNextIndices") as IList<int>;
        var edgeVData = Get(mesh, "edgeVertexDataIndices") as IList<int>;
        var edgeVtx = Get(mesh, "edgeVertexIndices") as IList<int>;
        if (texScale is null || matIndex is null || axisU is null || axisV is null
            || texcoord is null || positions is null
            || faceEdge is null || edgeNext is null || edgeVData is null || edgeVtx is null)
            return 0;

        // Per material index: real (W,H) dims, or null to skip (stock material not in staged content,
        // or already at the 16×16 fallback — nothing to correct).
        var dims = new (float W, float H)?[materials.Count];
        for (var mi = 0; mi < materials.Count; mi++)
        {
            var dim = ResolveDim(materials[mi], stagedContentRoot, dimCache);
            if (dim is { } d && (d.W != FallbackDim || d.H != FallbackDim))
                dims[mi] = d;
        }

        var fixedFaces = 0;
        for (var f = 0; f < matIndex.Count && f < texScale.Count; f++)
        {
            ct.ThrowIfCancellationRequested();
            var mi = matIndex[f];
            if (mi < 0 || mi >= dims.Length || dims[mi] is not { } dim || f >= axisU.Count || f >= axisV.Count)
                continue;

            // 1) Correct textureScale: source1import baked this face at the 16×16 fallback, so the
            //    stored scale is off by 16/realDim. Scaling it back by realDim/16 yields the true S1
            //    (world-units-per-texel) scale — exactly what Hammer shows in the face editor.
            var ts = texScale[f];
            var sx = ts.X * dim.W / FallbackDim;
            var sy = ts.Y * dim.H / FallbackDim;
            texScale[f] = new Vector2(sx, sy);

            // 2) Rebuild each corner's baked texcoord from the (now-correct) texture mapping —
            //    the same formula Hammer uses on edit (verified against a Hammer-corrected .vmap):
            //        u = (dot(P, axisU.xyz) / scale.u + axisU.w) / textureWidth
            //        v = (dot(P, axisV.xyz) / scale.v + axisV.w) / textureHeight
            //    The renderer uses these baked texcoords directly, so this is what actually fixes the
            //    on-screen scale; scaling the old (16-default) texcoords could not reproduce it.
            var au = axisU[f];
            var av = axisV[f];

            var e0 = faceEdge[f];
            var e = e0;
            var guard = 0;
            do
            {
                if (e < 0 || e >= edgeVData.Count || e >= edgeVtx.Count) break;
                var fv = edgeVData[e];
                var vi = edgeVtx[e];
                if (fv >= 0 && fv < texcoord.Count && vi >= 0 && vi < positions.Count
                    && sx != 0f && sy != 0f)
                    texcoord[fv] = RecomputeTexcoord(positions[vi], au, av, sx, sy, dim.W, dim.H);
                e = e < edgeNext.Count ? edgeNext[e] : e0;
            } while (e != e0 && ++guard < 256);

            materialsFixed.Add(materials[mi] ?? "");
            fixedFaces++;
        }

        return fixedFaces;
    }

    /// <summary>Resolves a material's real basetexture dimensions from the staged content
    /// (parsing its <c>.vmt</c> for <c>$basetexture</c>), or null when not a readable custom
    /// material — which is exactly the set source1import mis-scaled. Cached per material.</summary>
    private static (float W, float H)? ResolveDim(
        string? vmat, string stagedContentRoot, Dictionary<string, (float W, float H)?> cache)
    {
        if (string.IsNullOrEmpty(vmat))
            return null;

        // "materials/de_coastal/stucco01.vmat" -> "de_coastal/stucco01"
        var rel = vmat.Replace('\\', '/');
        if (rel.StartsWith("materials/", StringComparison.OrdinalIgnoreCase))
            rel = rel["materials/".Length..];
        if (rel.EndsWith(".vmat", StringComparison.OrdinalIgnoreCase))
            rel = rel[..^".vmat".Length];

        if (cache.TryGetValue(rel, out var cached))
            return cached;

        (float, float)? result = null;
        var matRoot = Path.Combine(stagedContentRoot, "materials");
        var baseTex = rel;

        var vmtPath = Path.Combine(matRoot, rel.Replace('/', Path.DirectorySeparatorChar) + ".vmt");
        if (File.Exists(vmtPath))
        {
            try
            {
                var vmt = VmtFile.Load(vmtPath);
                var bt = vmt["$basetexture"];
                if (!string.IsNullOrWhiteSpace(bt))
                    baseTex = bt.Replace('\\', '/').Trim();
            }
            catch { /* fall back to the material-name texture */ }
        }

        var vtfPath = Path.Combine(matRoot, baseTex.Replace('/', Path.DirectorySeparatorChar) + ".vtf");
        if (VtfHeader.TryReadDimensions(vtfPath) is { } d && d.Width > 0 && d.Height > 0)
            result = (d.Width, d.Height);

        cache[rel] = result;
        return result;
    }

    private static object? Get(Element e, string key) => e.ContainsKey(key) ? e[key] : null;

    /// <summary>Returns the typed data list of a named stream inside a mesh data container
    /// (<c>faceData</c>/<c>faceVertexData</c>), or null if absent.</summary>
    private static IList<T>? StreamList<T>(Element mesh, string container, string standardAttribute)
    {
        if (Get(mesh, container) is not Element c || Get(c, "streams") is not ElementArray streams)
            return null;
        foreach (var s in streams)
        {
            if (s is null || Get(s, "standardAttributeName") as string != standardAttribute)
                continue;
            return Get(s, "data") as IList<T>;
        }
        return null;
    }
}
