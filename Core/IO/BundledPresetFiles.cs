namespace Hammer5Tools.Core.IO;

/// <summary>Locates immutable presets shipped with the application, outside its runtime bin folder.</summary>
public static class BundledPresetFiles
{
    /// <summary>Returns a shipped preset category for a published or development build.</summary>
    public static string GetDirectory(string category, string? baseDirectory = null)
    {
        if (category is not ("addons" or "soundeventeditor" or "smartpropeditor"))
        {
            throw new ArgumentException("Unknown bundled preset category.", nameof(category));
        }

        var directory = Path.TrimEndingDirectorySeparator(baseDirectory ?? AppContext.BaseDirectory);
        var root = Path.GetFileName(directory).Equals("bin", StringComparison.OrdinalIgnoreCase)
            ? Path.GetDirectoryName(directory)!
            : directory;
        return Path.Combine(root, "presets", category);
    }
}
