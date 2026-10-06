namespace Hammer5Tools.Core.Cs2;

using System.IO;

/// <summary>
/// Canonical path resolution for Counter-Strike 2 and Workshop Tools directory layouts.
/// </summary>
public static class Cs2Paths
{
    public const string ExeRelativePath = "game/bin/win64/cs2.exe";
    public const string ResourceCompilerRelativePath = "game/bin/win64/resourcecompiler.exe";
    public const string GameInfoRelativePath = "game/csgo/gameinfo.gi";
    public const string ContentAddonsRelativePath = "content/csgo_addons";
    public const string GameAddonsRelativePath = "game/csgo_addons";
    public const string KeybindingsRelativePath = "game/core/tools/keybindings";

    public static string GetContentAddonsPath(string cs2Root) =>
        Path.Combine(cs2Root, "content", "csgo_addons");

    public static string GetGameAddonsPath(string cs2Root) =>
        Path.Combine(cs2Root, "game", "csgo_addons");

    public static string GetBinWin64Path(string cs2Root) =>
        Path.Combine(cs2Root, "game", "bin", "win64");

    public static string GetCs2ExePath(string cs2Root) =>
        Path.Combine(cs2Root, "game", "bin", "win64", "cs2.exe");

    public static string GetResourceCompilerPath(string cs2Root) =>
        Path.Combine(cs2Root, "game", "bin", "win64", "resourcecompiler.exe");

    public static string GetKeybindingsPath(string cs2Root) =>
        Path.Combine(cs2Root, "game", "core", "tools", "keybindings");

    public static string GetGameInfoPath(string cs2Root) =>
        Path.Combine(cs2Root, "game", "csgo", "gameinfo.gi");

    public static string GetAddonContentPath(string cs2Root, string addonName) =>
        Path.Combine(GetContentAddonsPath(cs2Root), addonName);

    public static string GetAddonGamePath(string cs2Root, string addonName) =>
        Path.Combine(GetGameAddonsPath(cs2Root), addonName);

    /// <summary>Gets the addon containing an absolute content file, or null outside the installation.</summary>
    public static string? GetContentAddonName(string cs2Root, string filePath)
    {
        if (!Path.IsPathRooted(filePath)) return null;
        var relative = Path.GetRelativePath(Path.GetFullPath(GetContentAddonsPath(cs2Root)), Path.GetFullPath(filePath));
        var segments = relative.Split([Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar], StringSplitOptions.RemoveEmptyEntries);
        return segments.Length >= 2 && segments[0] is not "." and not ".." && !Path.IsPathRooted(relative)
            ? segments[0] : null;
    }

    public static bool IsValidCs2Path(string? path)
    {
        if (string.IsNullOrWhiteSpace(path) || !Directory.Exists(path))
        {
            return false;
        }

        var exePath = GetCs2ExePath(path);
        var gameInfoPath = GetGameInfoPath(path);

        return File.Exists(exePath) || File.Exists(gameInfoPath);
    }
}
