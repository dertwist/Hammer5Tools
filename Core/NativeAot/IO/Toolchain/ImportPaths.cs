namespace Hammer5Tools.Core.IO.Toolchain;

/// <summary>
/// Derives add-on game and content paths from an S2 gameinfo directory and map
/// name, then exposes the per-map artifact paths the importer reads and writes.
/// </summary>
public sealed class ImportPaths
{
    public ImportPaths(string s2GameInfoDir, string addon, string mapName)
    {
        S2GameCsgo = s2GameInfoDir;
        Addon = addon;
        MapName = mapName;

        var gameRoot = Directory.GetParent(s2GameInfoDir)?.Parent?.FullName
            ?? throw new ArgumentException("S2 gameinfo directory must be inside a game directory.", nameof(s2GameInfoDir));
        S2GameAddon = Path.Combine(gameRoot, "game", "csgo_addons", addon);
        S2ContentCsgo = Path.Combine(gameRoot, "content", "csgo_addons", addon);
        S2ContentCsgoImported = S2ContentCsgo;
    }

    public string S2GameCsgo { get; }
    public string Addon { get; }

    /// <summary>Map name relative to <c>maps\</c>; after import, <c>instances</c>→<c>prefabs</c>.</summary>
    public string MapName { get; private set; }

    public string S2GameAddon { get; }
    public string S2ContentCsgo { get; }
    public string S2ContentCsgoImported { get; }

    /// <summary>Mirror of the Python <c>mapname = mapname.replace("instances", "prefabs")</c> step.</summary>
    public void SwitchInstancesToPrefabs() => MapName = MapName.Replace("instances", "prefabs");

    private string MapsContent(string suffix) =>
        Path.Combine(S2ContentCsgoImported, "maps", MapName + suffix);

    public string PrefabRefs => MapsContent("_prefab_refs.txt");
    public string PrefabMdlList => MapsContent("_prefab_mdl_lst.txt");
    public string PrefabNewRefs => MapsContent("_prefab_new_refs.txt");
    public string PrefabCompileNewRefs => MapsContent("_prefab_compile_new_refs.txt");

    /// <summary>
    /// The refs file source1import actually produced. The Python assumes
    /// <c>_prefab_refs.txt</c> (named that when -usebsp succeeds and merges
    /// instances); when -usebsp falls back (e.g. spaces in the content path) the
    /// tool writes plain <c>_refs.txt</c> instead. Return whichever exists.
    /// </summary>
    public string? ResolveRefsFile()
    {
        var prefab = MapsContent("_prefab_refs.txt");
        if (File.Exists(prefab))
            return prefab;
        var plain = MapsContent("_refs.txt");
        return File.Exists(plain) ? plain : null;
    }

    /// <summary>Main imported <c>.vmap</c> in the content tree.</summary>
    public string ContentMainVmap => Path.Combine(S2ContentCsgo, "maps", MapName + ".vmap");
    public string ImportedMainVmap => Path.Combine(S2ContentCsgoImported, "maps", MapName + ".vmap");
}
