using SourcePorter.Core.Toolchain;

namespace SourcePorter.Core.Domain;

/// <summary>
/// A Counter-Strike 2 install (the "…\Counter-Strike Global Offensive" root,
/// which holds both the S1 <c>csgo\</c> tree and the S2 <c>game\csgo\</c> tree).
/// Derives every path the importer needs so the GUI only has to ask for the
/// install directory, a source <c>.vmf</c>, and an output addon name.
/// </summary>
public sealed class Cs2Install(string installRoot)
{
    public string InstallRoot { get; } = installRoot.TrimEnd('\\', '/');

    /// <summary>The S2 game tree root: <c>&lt;root&gt;\game</c>.</summary>
    public string GameDir => Path.Combine(InstallRoot, "game");

    /// <summary>S1 gameinfo dir (compiled CS:GO content): <c>&lt;root&gt;\csgo</c>.</summary>
    public string S1GameInfoDir => Path.Combine(InstallRoot, "csgo");

    /// <summary>S2 gameinfo dir: <c>&lt;root&gt;\game\csgo</c>.</summary>
    public string S2GameInfoDir => Path.Combine(GameDir, "csgo");

    /// <summary>Valve's import scripts/configs: <c>&lt;root&gt;\game\csgo\import_scripts</c>.</summary>
    public string ImportScriptsDir => Path.Combine(S2GameInfoDir, "import_scripts");

    /// <summary>
    /// Parent of all addon content folders: <c>&lt;root&gt;\content\csgo_addons</c>.
    /// (The content tree is where <c>source1import</c> writes the imported map and
    /// assets — the working output a porter finishes in Hammer.)
    /// </summary>
    public string ContentAddonsDir => Path.Combine(InstallRoot, "content", "csgo_addons");

    /// <summary>A specific addon's content folder: <c>&lt;root&gt;\content\csgo_addons\&lt;addon&gt;</c>.</summary>
    public string ContentAddonDir(string addon) => Path.Combine(ContentAddonsDir, addon);

    /// <summary>Resolves the Valve command-line tools under this install.</summary>
    public ValveToolLocator Tools => new(GameDir);

    /// <summary>Verifies the directory looks like a CS2 install.</summary>
    public bool IsValid(out string? error)
    {
        if (!File.Exists(Path.Combine(S1GameInfoDir, "gameinfo.txt")))
        {
            error = $"Not a CS2 install: missing {S1GameInfoDir}\\gameinfo.txt";
            return false;
        }
        if (!File.Exists(Path.Combine(S2GameInfoDir, "gameinfo.gi")))
        {
            error = $"Not a CS2 install: missing {S2GameInfoDir}\\gameinfo.gi";
            return false;
        }
        error = null;
        return true;
    }

    /// <summary>
    /// Splits a source <c>.vmf</c> path into its S1 content dir (the folder
    /// containing <c>maps\</c>) and the map name relative to <c>maps\</c>
    /// (no extension), as <c>source1import</c> expects.
    /// </summary>
    public static bool TryParseSourceMap(string vmfPath, out string s1ContentDir, out string mapName)
    {
        s1ContentDir = "";
        mapName = "";

        var normalized = vmfPath.Replace('/', '\\');
        var marker = "\\maps\\";
        var idx = normalized.LastIndexOf(marker, StringComparison.OrdinalIgnoreCase);
        if (idx < 0)
            return false;

        s1ContentDir = normalized[..idx];
        var rel = normalized[(idx + marker.Length)..];
        if (rel.EndsWith(".vmf", StringComparison.OrdinalIgnoreCase))
            rel = rel[..^4];

        // source1import / the GUI use forward slashes for sub-folders under maps\.
        mapName = rel.Replace('\\', '/');
        return mapName.Length > 0;
    }

    /// <summary>Builds the <see cref="PortProject"/> the import service consumes.</summary>
    public PortProject BuildProject(string sourceMapPath, string addon, ImportOptions options)
    {
        if (!TryParseSourceMap(sourceMapPath, out var s1Content, out var mapName))
            throw new ArgumentException("Source map must be inside a 'maps' folder.", nameof(sourceMapPath));

        return new PortProject
        {
            S1GameInfoDir = S1GameInfoDir,
            S1ContentDir = s1Content,
            S2GameInfoDir = S2GameInfoDir,
            AddonName = addon,
            MapName = mapName,
            Import = options,
        };
    }
}
