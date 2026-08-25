using System.Numerics;
using Datamodel;
using Hammer5Tools.Core.Format.Materials;

namespace Hammer5Tools.Core.Format.Vmap;

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
        string addonContentMapsDir, string mapName, string? stagedContentRoot, string? addonContentDir = null,
        Action<string>? log = null, CancellationToken ct = default)
    {
        log?.Invoke("▶ Brush UV fix: correcting custom-material texture scale…");
        if ((string.IsNullOrEmpty(stagedContentRoot) || !Directory.Exists(stagedContentRoot)) &&
            (string.IsNullOrEmpty(addonContentDir) || !Directory.Exists(addonContentDir)))
        {
            log?.Invoke("  No content source available (real texture sizes unknown) — skipping.");
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

            VmapDocument doc;
            try { doc = VmapDocument.LoadInMemory(vmap); }
            catch (Exception ex) { log?.Invoke($"  WARNING: couldn't read {Path.GetFileName(vmap)}: {ex.Message}"); continue; }

            var matStats = new Dictionary<string, (int FaceCount, float Width, float Height)>(StringComparer.OrdinalIgnoreCase);
            var faces = FixDocument(doc, stagedContentRoot, addonContentDir, dimCache, matStats, ct);
            if (faces == 0)
                continue;

            var backup = VmapBackup.Backup(vmap, log);
            doc.Save();
            try { File.Delete(backup); }
            catch (Exception ex) { log?.Invoke($"  WARNING: could not delete backup {Path.GetFileName(backup)}: {ex.Message}"); }
            MarkFixed(vmap);
            filesChanged++;
            facesFixed += faces;
            materialsFixed += matStats.Count;

            log?.Invoke($"  {Path.GetFileName(vmap)}: rescaled {faces} face(s) across {matStats.Count} custom material(s):");
            foreach (var (matPath, stat) in matStats.OrderByDescending(kv => kv.Value.FaceCount))
            {
                log?.Invoke($"    • {matPath} ({stat.Width}x{stat.Height} px): {stat.FaceCount} face(s) rescaled");
            }
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
    /// <paramref name="p"/>, the per-face texture axes (xyz direction + w offset) and the per-axis
    /// <c>textureScale</c>, the baked texcoord is
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

    /// <summary>Writes/updates the sidecar marker (mtime now &gt; the just-saved .vmap).</summary>
    private static void MarkFixed(string vmap)
    {
        try { File.WriteAllText(MarkerPath(vmap), "brush uv scale fixed"); }
        catch { /* marker is best-effort */ }
    }

    /// <summary>Fixes one loaded document in place; returns total faces fixed.</summary>
    private static int FixDocument(
        VmapDocument doc, string? stagedContentRoot, string? addonContentDir,
        Dictionary<string, (float W, float H)?> dimCache,
        Dictionary<string, (int FaceCount, float Width, float Height)> matStats,
        CancellationToken ct)
    {
        int faces = 0;
        var seen = new HashSet<Element>();

        void Walk(Element? e)
        {
            if (e is null || !seen.Add(e))
                return;
            if (e.ClassName == "CDmePolygonMesh")
                faces += FixMesh(e, stagedContentRoot, addonContentDir, dimCache, matStats, ct);
            foreach (var kv in e)
            {
                if (kv.Value is Element c) Walk(c);
                else if (kv.Value is ElementArray a)
                    foreach (var x in a) Walk(x);
            }
        }
        Walk(doc.Model.Root);
        return faces;
    }

    private static int FixMesh(
        Element mesh, string? stagedContentRoot, string? addonContentDir,
        Dictionary<string, (float W, float H)?> dimCache,
        Dictionary<string, (int FaceCount, float Width, float Height)> matStats,
        CancellationToken ct)
    {
        if (Get(mesh, "materials") is not StringArray materials)
            return 0;

        var texScale = StreamList<Vector2>(mesh, "faceData", "textureScale");
        var matIndex = StreamList<int>(mesh, "faceData", "materialindex");
        var axisU = StreamList<Vector4>(mesh, "faceData", "textureAxisU");
        var axisV = StreamList<Vector4>(mesh, "faceData", "textureAxisV");
        var texcoordStreams = StreamListMatching<Vector2>(mesh, "faceVertexData", name => name.StartsWith("texcoord", StringComparison.OrdinalIgnoreCase));
        var positions = StreamList<Vector3>(mesh, "vertexData", "position");
        var faceEdge = Get(mesh, "faceEdgeIndices") as IList<int>;
        var edgeNext = Get(mesh, "edgeNextIndices") as IList<int>;
        var edgeVData = Get(mesh, "edgeVertexDataIndices") as IList<int>;
        var edgeVtx = Get(mesh, "edgeVertexIndices") as IList<int>;
        if (texScale is null || matIndex is null || axisU is null || axisV is null
            || texcoordStreams.Count == 0 || positions is null
            || faceEdge is null || edgeNext is null || edgeVData is null || edgeVtx is null)
            return 0;

        var dims = new (float W, float H)?[materials.Count];
        for (var mi = 0; mi < materials.Count; mi++)
        {
            var dim = ResolveDim(materials[mi], stagedContentRoot, addonContentDir, dimCache);
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

            var ts = texScale[f];
            var sx = ts.X;
            var sy = ts.Y;

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
                if (fv >= 0 && vi >= 0 && vi < positions.Count && sx != 0f && sy != 0f)
                {
                    var updatedUv = RecomputeTexcoord(positions[vi], au, av, sx, sy, dim.W, dim.H);
                    foreach (var tc in texcoordStreams)
                    {
                        if (fv < tc.Count)
                            tc[fv] = updatedUv;
                    }
                }
                e = e < edgeNext.Count ? edgeNext[e] : e0;
            } while (e != e0 && ++guard < 256);

            var matName = materials[mi] ?? "";
            if (matStats.TryGetValue(matName, out var existing))
                matStats[matName] = (existing.FaceCount + 1, dim.W, dim.H);
            else
                matStats[matName] = (1, dim.W, dim.H);

            fixedFaces++;
        }

        return fixedFaces;
    }

    /// <summary>Resolves a material's real basetexture dimensions from the staged content or addon content
    /// (parsing its <c>.vmt</c>/<c>.vmat</c> and reading <c>.vtf</c>/<c>.tga</c>/<c>.png</c> headers),
    /// or null when not a readable custom material. Cached per material.</summary>
    internal static (float W, float H)? ResolveDim(
        string? vmat, string? stagedContentRoot, Dictionary<string, (float W, float H)?> cache)
        => ResolveDim(vmat, stagedContentRoot, null, cache);

    internal static (float W, float H)? ResolveDim(
        string? vmat, string? stagedContentRoot, string? addonContentDir, Dictionary<string, (float W, float H)?> cache)
    {
        if (string.IsNullOrEmpty(vmat))
            return null;

        var rel = vmat.Replace('\\', '/');
        if (rel.StartsWith("materials/", StringComparison.OrdinalIgnoreCase))
            rel = rel["materials/".Length..];
        if (rel.EndsWith(".vmat", StringComparison.OrdinalIgnoreCase))
            rel = rel[..^".vmat".Length];

        if (cache.TryGetValue(rel, out var cached))
            return cached;

        (float, float)? result = null;
        var searchRoots = new List<string>();
        if (!string.IsNullOrEmpty(stagedContentRoot) && Directory.Exists(stagedContentRoot))
            searchRoots.Add(stagedContentRoot);
        if (!string.IsNullOrEmpty(addonContentDir) && Directory.Exists(addonContentDir))
            searchRoots.Add(addonContentDir);

        foreach (var root in searchRoots)
        {
            var matRoot = Path.Combine(root, "materials");
            var baseTex = rel;

            var vmtPath = Path.Combine(matRoot, rel.Replace('/', Path.DirectorySeparatorChar) + ".vmt");
            if (File.Exists(vmtPath))
            {
                try
                {
                    var vmt = VmtFile.Load(vmtPath);
                    var bt = vmt["$basetexture"];
                    if (string.IsNullOrWhiteSpace(bt))
                        bt = vmt["$basetexture2"];

                    if (!string.IsNullOrWhiteSpace(bt))
                    {
                        bt = bt.Replace('\\', '/').Trim();
                        if (bt.StartsWith("materials/", StringComparison.OrdinalIgnoreCase))
                            bt = bt["materials/".Length..];
                        baseTex = bt;
                    }
                }
                catch { /* fall back to the material-name texture */ }
            }

            var relPath = baseTex.Replace('/', Path.DirectorySeparatorChar);
            foreach (var ext in new[] { ".vtf", ".tga", ".png" })
            {
                var texPath = Path.Combine(matRoot, relPath + ext);
                if (TextureHeaderReader.TryReadDimensions(texPath) is { } d && d.Width > 0 && d.Height > 0)
                {
                    result = (d.Width, d.Height);
                    break;
                }
            }

            if (result is not null)
                break;
        }

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

    private static List<IList<T>> StreamListMatching<T>(Element mesh, string container, Func<string, bool> predicate)
    {
        var result = new List<IList<T>>();
        if (Get(mesh, container) is not Element c || Get(c, "streams") is not ElementArray streams)
            return result;
        foreach (var s in streams)
        {
            if (s is not null && Get(s, "standardAttributeName") as string is string attrName && predicate(attrName))
            {
                if (Get(s, "data") is IList<T> list)
                    result.Add(list);
            }
        }
        return result;
    }
}
