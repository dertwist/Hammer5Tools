namespace SourcePorter.Core.Toolchain;

/// <summary>
/// Writes a minimal Source 1 <c>gameinfo.txt</c> into a staged content root so
/// <c>source1import</c> treats that root as a <b>GAME</b> search path.
/// <para>
/// A decompiled <c>.bsp</c>'s embedded materials/models are unpacked into the content root,
/// but <c>source1import</c> imports materials only from the game path — it <i>finds</i> a
/// custom <c>.vmt</c> via the content path (<c>-src1contentdir</c>) yet resolves its
/// <c>.vtf</c> textures via the game path and fails with a bare <c>*** Error Importing</c>.
/// Making the content root a game path (while keeping <c>SteamAppId 730</c> and the real CS:GO
/// dir as a second game path so the base assets still mount) lets those custom materials
/// import. Verified end-to-end: a custom <c>de_coastal</c> material that fails from the
/// content path imports cleanly once the root is a game path.
/// </para>
/// <para>
/// Only ever applied to our own staged temp content roots (under
/// <see cref="MapStaging.StagingRoot"/>) — never the user's folders.
/// </para>
/// </summary>
public static class ImportGameInfo
{
    /// <summary>
    /// True when <paramref name="contentDir"/> is one of our staged temp content roots — the
    /// only place we may drop a <c>gameinfo.txt</c>. Guards against writing into a user folder
    /// (e.g. an in-place loose-vmf import whose content root is the mapper's own directory).
    /// </summary>
    public static bool IsStagedContentDir(string contentDir)
    {
        if (string.IsNullOrEmpty(contentDir))
            return false;
        var staging = Path.GetFullPath(MapStaging.StagingRoot);
        var full = Path.GetFullPath(contentDir);
        return full.StartsWith(staging, StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>
    /// Writes <c>gameinfo.txt</c> into <paramref name="contentRoot"/> (idempotent) so it is a
    /// source1import game search path, with the real <paramref name="csgoDir"/> + app 730 as a
    /// second path for the base CS:GO assets. Returns <paramref name="contentRoot"/>.
    /// </summary>
    public static string EnsureCustomGameInfo(string contentRoot, string csgoDir)
    {
        File.WriteAllText(Path.Combine(contentRoot, "gameinfo.txt"), BuildGameInfo(csgoDir));
        return contentRoot;
    }

    /// <summary>The gameinfo body. <c>|gameinfo_path|.</c> is the dir holding this file (the
    /// content root), so its unpacked materials/models are a game search path; the second
    /// <c>Game</c> path + <c>SteamAppId 730</c> mount the base CS:GO assets.</summary>
    internal static string BuildGameInfo(string csgoDir) =>
        "\"GameInfo\"\r\n" +
        "{\r\n" +
        "\tgame\t\"Counter-Strike: Global Offensive\"\r\n" +
        "\ttitle\t\"COUNTER-STRIKE'\"\r\n" +
        "\ttitle2\t\"GO\"\r\n" +
        "\ttype\tmultiplayer_only\r\n" +
        "\tGameData\t\"csgo.fgd\"\r\n" +
        "\tFileSystem\r\n" +
        "\t{\r\n" +
        "\t\tSteamAppId\t730\r\n" +
        "\t\tToolsAppId\t211\r\n" +
        "\t\tSearchPaths\r\n" +
        "\t\t{\r\n" +
        "\t\t\tGame\t|gameinfo_path|.\r\n" +
        $"\t\t\tGame\t\"{csgoDir}\"\r\n" +
        "\t\t}\r\n" +
        "\t}\r\n" +
        "}\r\n";
}
