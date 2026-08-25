using System.Numerics;
using Datamodel;
using DM = Datamodel.Datamodel;

namespace SourcePorter.Core.Vmap;

/// <summary>
/// Scaffolds a Source 2 3D-skybox setup for an imported map. A CS2 skybox is a
/// <b>separate level</b>: this creates an empty <c>&lt;map&gt;_sky.vmap</c> flagged as a
/// skybox map (worldspawn <c>mapUsageType = "skybox"</c> — Hammer's <i>Map Type → skybox</i>)
/// and adds a <c>skybox_reference</c> entity at the origin (<c>0 0 0</c>) to the main map,
/// pointing at the skybox via <c>targetmapname</c>. The user then moves the actual sky
/// geometry into the skybox map in Hammer; this tool only lays down the template.
/// </summary>
public static class VmapSkyboxTemplate
{
    /// <summary>Outcome of a skybox-template pass.</summary>
    public sealed record Result(bool SkyboxCreated, bool ReferenceAdded, string SkyboxPath);

    /// <summary>
    /// Creates the skybox template for the main map at <paramref name="mainVmapPath"/>.
    /// Idempotent: skips creating <c>&lt;map&gt;_sky.vmap</c> if it already exists (never
    /// clobbers sky geometry added on a previous run) and skips adding a second
    /// <c>skybox_reference</c> if one is already present.
    /// </summary>
    public static Result Create(string mainVmapPath, Action<string>? log = null, CancellationToken ct = default)
    {
        var mapsDir = System.IO.Path.GetDirectoryName(mainVmapPath)
                      ?? throw new InvalidVmapException($"{mainVmapPath}: cannot determine maps directory.");
        var mapName = System.IO.Path.GetFileNameWithoutExtension(mainVmapPath);
        var skyName = mapName + "_sky";
        var skyPath = System.IO.Path.Combine(mapsDir, skyName + ".vmap");
        var targetMapName = $"maps/{skyName}.vmap"; // content-relative, forward-slashed

        // 1) Skybox .vmap — clone the main map's root (guarantees all required top-level keys),
        //    empty its world, flag it as a skybox map. Skip if it already exists.
        var skyboxCreated = false;
        if (File.Exists(skyPath))
        {
            log?.Invoke($"  Skybox map already exists — left untouched: {System.IO.Path.GetFileName(skyPath)}");
        }
        else
        {
            ct.ThrowIfCancellationRequested();
            var sky = VmapDocument.Load(mainVmapPath);
            sky.ClearWorldChildren();
            sky.World["mapUsageType"] = "skybox";
            sky.Save(skyPath);
            skyboxCreated = true;
            log?.Invoke($"  Created skybox template {System.IO.Path.GetFileName(skyPath)} (Map Type = skybox, empty world).");
        }

        // 2) skybox_reference entity in the MAIN map at 0 0 0 (idempotent).
        ct.ThrowIfCancellationRequested();
        var main = VmapDocument.Load(mainVmapPath);
        if (HasSkyboxReference(main))
        {
            log?.Invoke("  Main map already has a skybox_reference — not adding another.");
            return new Result(skyboxCreated, ReferenceAdded: false, skyPath);
        }

        VmapBackup.Backup(mainVmapPath, log);
        main.WorldChildren.Add(BuildSkyboxReference(main.Model, main.WorldChildren, targetMapName));
        main.Save();
        log?.Invoke($"  Added skybox_reference at 0 0 0 (targetmapname={targetMapName}) to {System.IO.Path.GetFileName(mainVmapPath)}.");
        return new Result(skyboxCreated, ReferenceAdded: true, skyPath);
    }

    private static bool HasSkyboxReference(VmapDocument main)
    {
        var children = main.TryGetWorldChildren();
        if (children is null)
            return false;
        foreach (var node in children)
            if (Classname(node) == "skybox_reference")
                return true;
        return false;
    }

    private static string? Classname(Element node) =>
        node.ContainsKey("entity_properties") && node["entity_properties"] is Element props
            && props.ContainsKey("classname") && props["classname"] is string classname
            ? classname
            : null;

    /// <summary>
    /// Builds a <c>skybox_reference</c> <c>CMapEntity</c> with the full MapNode/BaseEntity
    /// attribute set a Hammer-authored entity carries, so the scaffolded entity loads cleanly.
    /// </summary>
    private static Element BuildSkyboxReference(DM dm, ElementArray worldChildren, string targetMapName)
    {
        var entity = new Element(dm, "", null, "CMapEntity");
        entity["origin"] = Vector3.Zero;
        entity["angles"] = new QAngle(0, 0, 0);
        entity["scales"] = Vector3.One;
        entity["nodeID"] = NextNodeId(worldChildren);
        entity["referenceID"] = unchecked((ulong)Random.Shared.NextInt64());
        entity["children"] = new ElementArray();
        entity["editorOnly"] = false;
        entity["force_hidden"] = false;
        entity["transformLocked"] = false;
        entity["variableTargetKeys"] = new StringArray();
        entity["variableNames"] = new StringArray();

        var plugs = new Element(dm, "", null, "DmePlugList");
        plugs["names"] = new StringArray();
        plugs["dataTypes"] = new IntArray();
        plugs["plugTypes"] = new IntArray();
        plugs["descriptions"] = new StringArray();
        entity["relayPlugData"] = plugs;
        entity["connectionsData"] = new ElementArray();

        var props = new Element(dm, "", null, "EditGameClassProps");
        props["classname"] = "skybox_reference";
        props["targetmapname"] = targetMapName;
        entity["entity_properties"] = props;

        return entity;
    }

    /// <summary>A node id one past the largest among the world's direct children.</summary>
    private static int NextNodeId(ElementArray worldChildren)
    {
        var max = 0;
        foreach (var node in worldChildren)
            if (node.ContainsKey("nodeID") && node["nodeID"] is int id && id > max)
                max = id;
        return max + 1;
    }
}
