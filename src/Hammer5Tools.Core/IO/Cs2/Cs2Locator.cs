namespace Hammer5Tools.Core.IO.Cs2;

using System.IO;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.Settings;
using Microsoft.Extensions.Logging;
#if WINDOWS
using Microsoft.Win32;
#endif

/// <summary>
/// Service locating Counter-Strike 2, Workshop Tools, and Steam libraries.
/// </summary>
public class Cs2Locator : ICs2Locator
{
    private readonly ISettingsService SettingsService;
    private readonly ILogger<Cs2Locator>? Logger;
    private readonly string? CustomSteamPath;

    public string? ResolvedCs2Path { get; private set; }

    public Cs2Locator(
        ISettingsService settingsService,
        ILogger<Cs2Locator>? logger = null,
        string? customSteamPath = null)
    {
        SettingsService = settingsService;
        Logger = logger;
        CustomSteamPath = customSteamPath;

        FindCs2Path();
    }

    /// <inheritdoc/>
    public string? FindCs2Path()
    {
        // 1. Settings override has top priority
        var overridePath = SettingsService.Settings.Cs2PathOverride;
        if (!string.IsNullOrWhiteSpace(overridePath) && IsValidCs2Path(overridePath))
        {
            ResolvedCs2Path = Path.GetFullPath(overridePath);
            Logger?.LogInformation("Using CS2 path override: {Path}", ResolvedCs2Path);
            return ResolvedCs2Path;
        }

        // 2. Discover via Steam libraries
        var libraries = FindSteamLibraries();
        foreach (var library in libraries)
        {
            var manifestPath = Path.Combine(library, "steamapps", "appmanifest_730.acf");
            var installDirName = "Counter-Strike Global Offensive";

            if (File.Exists(manifestPath))
            {
                try
                {
                    var acfContent = File.ReadAllText(manifestPath);
                    var parsedDir = SteamVdfParser.ParseInstallDir(acfContent);
                    if (!string.IsNullOrWhiteSpace(parsedDir))
                    {
                        installDirName = parsedDir;
                    }
                }
                catch (Exception ex)
                {
                    Logger?.LogWarning(ex, "Failed to parse {Path}", manifestPath);
                }
            }

            var candidate = Path.Combine(library, "steamapps", "common", installDirName);
            if (IsValidCs2Path(candidate))
            {
                ResolvedCs2Path = Path.GetFullPath(candidate);
                Logger?.LogInformation("Found valid CS2 installation: {Path}", ResolvedCs2Path);
                return ResolvedCs2Path;
            }
        }

        Logger?.LogWarning("Counter-Strike 2 installation was not found");
        ResolvedCs2Path = null;
        return null;
    }

    /// <inheritdoc/>
    public IReadOnlyList<string> FindSteamLibraries()
    {
        var steamPath = CustomSteamPath ?? GetSteamInstallPath();
        if (string.IsNullOrWhiteSpace(steamPath) || !Directory.Exists(steamPath))
        {
            return [];
        }

        var vdfPath = Path.Combine(steamPath, "steamapps", "libraryfolders.vdf");
        if (!File.Exists(vdfPath))
        {
            return [steamPath];
        }

        try
        {
            var content = File.ReadAllText(vdfPath);
            var libraries = SteamVdfParser.ParseLibraryFolders(content);
            if (!libraries.Contains(steamPath, StringComparer.OrdinalIgnoreCase))
            {
                libraries.Add(steamPath);
            }

            return libraries;
        }
        catch (Exception ex)
        {
            Logger?.LogError(ex, "Failed to read Steam libraryfolders.vdf from {Path}", vdfPath);
            return [steamPath];
        }
    }

    /// <inheritdoc/>
    public bool HasWorkshopTools(string? cs2Path = null)
    {
        var targetPath = cs2Path ?? ResolvedCs2Path;
        if (string.IsNullOrWhiteSpace(targetPath))
        {
            return false;
        }

        var rcPath = Cs2Paths.GetResourceCompilerPath(targetPath);
        return File.Exists(rcPath);
    }

    /// <inheritdoc/>
    public bool IsValidCs2Path(string? path) => Cs2Paths.IsValidCs2Path(path);

    private static string? GetSteamInstallPath()
    {
        var candidates = new List<string>();

#if WINDOWS
        if (OperatingSystem.IsWindows())
        {
            try
            {
                using var key = Registry.CurrentUser.OpenSubKey(@"Software\Valve\Steam");
                if (key?.GetValue("SteamPath") is string steamPath && !string.IsNullOrWhiteSpace(steamPath))
                {
                    candidates.Add(steamPath);
                }
            }
            catch
            {
                // Ignore registry errors
            }
        }
#endif

        if (OperatingSystem.IsWindows())
        {
            var p86 = Environment.GetEnvironmentVariable("ProgramFiles(x86)");
            if (!string.IsNullOrWhiteSpace(p86))
            {
                candidates.Add(Path.Combine(p86, "Steam"));
            }

            var pf = Environment.GetEnvironmentVariable("ProgramFiles");
            if (!string.IsNullOrWhiteSpace(pf))
            {
                candidates.Add(Path.Combine(pf, "Steam"));
            }
        }
        else if (OperatingSystem.IsMacOS())
        {
            var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            candidates.Add(Path.Combine(home, "Library", "Application Support", "Steam"));
        }
        else if (OperatingSystem.IsLinux())
        {
            var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            candidates.Add(Path.Combine(home, ".steam", "steam"));
            candidates.Add(Path.Combine(home, ".local", "share", "Steam"));
        }

        foreach (var candidate in candidates)
        {
            if (Directory.Exists(candidate))
            {
                return Path.GetFullPath(candidate);
            }
        }

        return null;
    }
}
