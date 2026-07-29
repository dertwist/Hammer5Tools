using System.Linq;
using Microsoft.Win32;
using ValveKeyValue;

namespace SourcePorter.Core.Domain;

/// <summary>
/// Locates the installed Counter-Strike 2 (Steam app <see cref="Cs2AppId"/>)
/// without prompting the user: reads Steam's install path from the Windows
/// registry, walks Steam's library folders (<c>libraryfolders.vdf</c>), and
/// returns the first one that holds a valid CS2 install — the same chain Steam
/// itself uses to find an installed game. Best-effort: never throws, returns
/// null when Steam or CS2 can't be found.
/// </summary>
public static class Cs2InstallLocator
{
    /// <summary>Steam application id for Counter-Strike 2 (formerly CS:GO).</summary>
    public const int Cs2AppId = 730;

    /// <summary>The <c>steamapps\common</c> sub-folder CS2 installs into.</summary>
    private const string Cs2FolderName = "Counter-Strike Global Offensive";

    /// <summary>
    /// Tries to find a valid CS2 install root (the folder <see cref="Cs2Install"/>
    /// wraps). Returns null if Steam or CS2 can't be located.
    /// </summary>
    public static string? TryLocate()
    {
        try
        {
            var steamPath = FindSteamPath();
            if (steamPath is null)
                return null;

            foreach (var library in EnumerateLibraries(steamPath))
            {
                var install = new Cs2Install(Path.Combine(library, "steamapps", "common", Cs2FolderName));
                if (install.IsValid(out _))
                    return install.InstallRoot;
            }
        }
        catch
        {
            // Auto-detect is a convenience — any failure just means "not found".
        }

        return null;
    }

    /// <summary>Reads the Steam install directory from the registry, or null.</summary>
    private static string? FindSteamPath()
    {
        if (!OperatingSystem.IsWindows())
            return null;

        // The per-user key (written by the running client) first, then the
        // machine-wide keys for the 64-bit OS / 32-bit Steam layout.
        var path = ReadRegistryString(Registry.CurrentUser, @"Software\Valve\Steam", "SteamPath")
                ?? ReadRegistryString(Registry.LocalMachine, @"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath")
                ?? ReadRegistryString(Registry.LocalMachine, @"SOFTWARE\Valve\Steam", "InstallPath");

        if (string.IsNullOrWhiteSpace(path))
            return null;

        // HKCU\…\SteamPath stores forward slashes; normalize for Path.Combine.
        path = path.Replace('/', '\\');
        return Directory.Exists(path) ? path : null;
    }

    private static string? ReadRegistryString(RegistryKey hive, string subKey, string valueName)
    {
        if (!OperatingSystem.IsWindows())
            return null;

        using var key = hive.OpenSubKey(subKey);
        return key?.GetValue(valueName) as string;
    }

    /// <summary>
    /// Yields every Steam library folder — the one that owns app 730 first — by
    /// parsing <c>steamapps\libraryfolders.vdf</c>. The Steam root is always
    /// included as a fallback in case the file is missing or unparseable.
    /// </summary>
    private static IEnumerable<string> EnumerateLibraries(string steamPath)
    {
        var ownsCs2 = new List<string>();
        var others = new List<string>();

        try
        {
            var vdf = Path.Combine(steamPath, "steamapps", "libraryfolders.vdf");
            if (File.Exists(vdf))
            {
                using var stream = File.OpenRead(vdf);
                var serializer = KVSerializer.Create(KVSerializationFormat.KeyValues1Text);
                var root = serializer.Deserialize(stream);

                foreach (var entry in root)
                {
                    var path = Child(entry, "path")?.Value?.ToString();
                    if (string.IsNullOrWhiteSpace(path))
                        continue;
                    path = path.Replace('/', '\\');

                    var apps = Child(entry, "apps");
                    var hasCs2 = apps is not null &&
                                 apps.Any(a => a.Name == Cs2AppId.ToString());
                    (hasCs2 ? ownsCs2 : others).Add(path);
                }
            }
        }
        catch
        {
            // Malformed vdf → fall back to the Steam root below.
        }

        others.Add(steamPath);

        return ownsCs2.Concat(others)
                      .Where(Directory.Exists)
                      .Distinct(StringComparer.OrdinalIgnoreCase);
    }

    private static KVObject? Child(KVObject obj, string name) =>
        obj.FirstOrDefault(child => string.Equals(child.Name, name, StringComparison.OrdinalIgnoreCase));
}
