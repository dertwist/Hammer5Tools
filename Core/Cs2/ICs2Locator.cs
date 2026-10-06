namespace Hammer5Tools.Core.Cs2;

/// <summary>
/// Service for locating Counter-Strike 2, Workshop Tools, and Steam library directories.
/// </summary>
public interface ICs2Locator
{
    /// <summary>
    /// Gets the resolved valid Counter-Strike 2 installation root path, if detected.
    /// </summary>
    string? ResolvedCs2Path { get; }

    /// <summary>
    /// Finds or refreshes the Counter-Strike 2 installation path.
    /// Checks settings override first, then Steam libraries.
    /// </summary>
    string? FindCs2Path();

    /// <summary>
    /// Discovers all Steam library paths from libraryfolders.vdf.
    /// </summary>
    IReadOnlyList<string> FindSteamLibraries();

    /// <summary>
    /// Checks whether Workshop Tools DLC is installed.
    /// </summary>
    bool HasWorkshopTools(string? cs2Path = null);

    /// <summary>
    /// Validates whether the given directory contains a valid CS2 installation.
    /// </summary>
    bool IsValidCs2Path(string? path);
}
