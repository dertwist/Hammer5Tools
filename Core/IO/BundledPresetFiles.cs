namespace Hammer5Tools.Core.IO;

/// <summary>Locates immutable presets shipped with the application, outside its runtime bin folder.</summary>
public static class BundledPresetFiles
{
    /// <summary>Returns a shipped preset category for a published or development build.</summary>
    public static string GetDirectory(string category, string? baseDirectory = null)
    {
        if (category is not ("addons" or "soundeventeditor" or "smartpropeditor" or "hotkeys"))
        {
            throw new ArgumentException("Unknown bundled preset category.", nameof(category));
        }

        var directory = Path.TrimEndingDirectorySeparator(baseDirectory ?? AppContext.BaseDirectory);
        var current = new DirectoryInfo(directory);
        while (current is not null)
        {
            var target = Path.Combine(current.FullName, "presets", category);
            if (Directory.Exists(target))
            {
                return target;
            }

            var devPath = Path.Combine(current.FullName, "Presets", category switch
            {
                "hotkeys" => "Hotkeys",
                "addons" => "Addons",
                "soundeventeditor" => "SoundEventEditor/Presets",
                "smartpropeditor" => "SmartPropEditor/Presets",
                _ => category
            });

            if (Directory.Exists(devPath))
            {
                return devPath;
            }

            current = current.Parent;
        }

        var root = Path.GetFileName(directory).Equals("bin", StringComparison.OrdinalIgnoreCase)
            ? Path.GetDirectoryName(directory)!
            : directory;
        return Path.Combine(root, "presets", category);
    }
}
