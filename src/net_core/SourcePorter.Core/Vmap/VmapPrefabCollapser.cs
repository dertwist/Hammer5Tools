using System.Numerics;
using Datamodel;
using DM = Datamodel.Datamodel;

namespace SourcePorter.Core.Vmap;

/// <summary>
/// Collapses a map's prefab / sub-map references into the root map: each referenced
/// <c>.vmap</c> (the auto-generated gameplay / environment / lighting / cubemap sub-maps,
/// and any <c>CMapPrefab</c> node) is loaded, its world child-nodes are deep-copied into
/// the main map's world, and the reference is removed. <see cref="Result.MergedFiles"/>
/// lists every file that was successfully merged so the caller can delete them.
///
/// The cross-document copy is the library's own <see cref="DM.ImportElement"/> (recursive,
/// re-owning each element to the main Datamodel), so referenced sub-elements (entity
/// properties, mesh data, connections) come along intact.
/// </summary>
public static class VmapPrefabCollapser
{
    /// <summary>Outcome of a collapse pass.</summary>
    public sealed record Result(int ReferencesMerged, int NodesMoved, int Skipped, IReadOnlyList<string> MergedFiles)
    {
        public bool DidAnything => ReferencesMerged > 0;
    }

    /// <summary>
    /// Merges every prefab/sub-map reference in <paramref name="main"/> into its world.
    /// <paramref name="contentRoot"/> is the addon content folder (<c>…\content\csgo_addons\&lt;addon&gt;</c>)
    /// used to resolve content-relative <c>maps/…\.vmap</c> targets. The caller saves
    /// <paramref name="main"/> afterwards.
    /// </summary>
    public static Result Collapse(VmapDocument main, string contentRoot, Action<string>? log = null, CancellationToken ct = default)
    {
        var children = main.WorldChildren;
        var references = GatherReferences(main, children).ToList();
        if (references.Count == 0)
        {
            log?.Invoke("  No prefab / sub-map references found — nothing to collapse.");
            return new Result(0, 0, 0, []);
        }

        int merged = 0, moved = 0, skipped = 0;
        var mergedFiles = new List<string>();
        foreach (var reference in references)
        {
            ct.ThrowIfCancellationRequested();

            var file = ResolveSubMap(reference.TargetPath, contentRoot);
            if (file is null)
            {
                log?.Invoke($"  Skipped (sub-map file not found): {reference.TargetPath}");
                skipped++;
                continue;
            }

            VmapDocument sub;
            try
            {
                sub = VmapDocument.Load(file);
            }
            catch (Exception ex)
            {
                log?.Invoke($"  Skipped (could not read {System.IO.Path.GetFileName(file)}): {ex.Message}");
                skipped++;
                continue;
            }

            if (reference.HasOffset)
                log?.Invoke($"  WARNING: {System.IO.Path.GetFileName(file)} is referenced with a non-zero offset; " +
                            "its geometry was merged WITHOUT applying that offset — verify placement in Hammer.");

            var subChildren = sub.TryGetWorldChildren();
            var count = 0;
            if (subChildren is not null)
            {
                foreach (var child in subChildren.ToList())
                {
                    if (child is null)
                        continue;
                    var imported = main.Model.ImportElement(child, DM.ImportRecursionMode.Recursive, DM.ImportOverwriteMode.All);
                    children.Add(imported);
                    count++;
                }
            }

            reference.Remove();
            mergedFiles.Add(file);
            merged++;
            moved += count;
            log?.Invoke($"  Merged {count} node(s) from {System.IO.Path.GetFileName(file)} into the root map.");
        }

        PurgePrefabReferences(main, mergedFiles);

        return new Result(merged, moved, skipped, mergedFiles);
    }

    private static void PurgePrefabReferences(VmapDocument main, IReadOnlyList<string> mergedFiles)
    {
        var mergedSet = new HashSet<string>(mergedFiles.Select(System.IO.Path.GetFileName).OfType<string>(), StringComparer.OrdinalIgnoreCase);

        // Purge map_asset_references on main.Root
        var root = main.Root;
        foreach (var key in new[] { "map_asset_references", "m_ReferencedMaps", "referencedMaps" })
        {
            if (!root.ContainsKey(key) || root[key] is not StringArray paths)
                continue;

            foreach (var path in paths.ToList())
            {
                if (string.IsNullOrEmpty(path))
                    continue;

                var fileName = System.IO.Path.GetFileName(path);
                if (mergedSet.Contains(fileName) || path.Contains("prefabs/", StringComparison.OrdinalIgnoreCase))
                {
                    paths.Remove(path);
                }
            }
        }

        // Purge CMapPrefab or CMapInstance nodes in main.WorldChildren that point to merged prefabs
        var children = main.WorldChildren;
        foreach (var node in children.ToList())
        {
            if (node is null) continue;
            var className = node.ClassName;
            if (className is "CMapPrefab" or "CMapInstance" or "CMapVariableSet")
            {
                string? target = null;
                if (node.ContainsKey("targetMapPath") && node["targetMapPath"] is string tmp1) target = tmp1;
                else if (node.ContainsKey("target") && node["target"] is string tmp2) target = tmp2;

                if (!string.IsNullOrEmpty(target))
                {
                    var fileName = System.IO.Path.GetFileName(target);
                    if (mergedSet.Contains(fileName) || target.Contains("prefabs/", StringComparison.OrdinalIgnoreCase))
                    {
                        children.Remove(node);
                    }
                }
            }
        }
    }

    /// <summary>A resolvable prefab/sub-map reference and how to detach it from the main map.</summary>
    private sealed record Reference(string TargetPath, bool HasOffset, Action Remove);

    private static IEnumerable<Reference> GatherReferences(VmapDocument main, ElementArray children)
    {
        // (a) CMapPrefab nodes in the world children — each points at a sub-map via targetMapPath.
        foreach (var node in children.ToList())
        {
            if (!string.Equals(node.ClassName, "CMapPrefab", StringComparison.Ordinal))
                continue;
            if (!node.ContainsKey("targetMapPath") || node["targetMapPath"] is not string target || target.Length == 0)
                continue;

            var captured = node;
            yield return new Reference(target, HasNonZeroOrigin(node), () => children.Remove(captured));
        }

        // (b) Root-level reference lists (the auto-split sub-maps may live here instead of, or
        // in addition to, CMapPrefab nodes — handle whichever a real import produced).
        var root = main.Root;
        foreach (var key in new[] { "map_asset_references", "m_ReferencedMaps", "referencedMaps" })
        {
            if (!root.ContainsKey(key) || root[key] is not StringArray paths)
                continue;
            foreach (var path in paths.ToList())
            {
                if (string.IsNullOrEmpty(path))
                    continue;
                var captured = path;
                yield return new Reference(captured, false, () => paths.Remove(captured));
            }
        }
    }

    private static bool HasNonZeroOrigin(Element node) =>
        node.ContainsKey("origin") && node["origin"] is Vector3 origin && origin != Vector3.Zero;

    /// <summary>
    /// Resolves a referenced map path (content-relative like <c>maps/foo_gameplay.vmap</c>, or
    /// a bare name) to an existing file: first under the addon content root, then by file name
    /// in the same <c>maps\</c> folder. Returns <c>null</c> if neither exists.
    /// </summary>
    private static string? ResolveSubMap(string targetPath, string contentRoot)
    {
        var relative = targetPath.Replace('/', '\\').TrimStart('\\');
        var direct = System.IO.Path.Combine(contentRoot, relative);
        if (File.Exists(direct))
            return direct;

        var byName = System.IO.Path.Combine(contentRoot, "maps", System.IO.Path.GetFileName(relative));
        return File.Exists(byName) ? byName : null;
    }
}
