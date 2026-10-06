namespace Hammer5Tools.Core.IO.Addons;

using Hammer5Tools.Core.Addons;

/// <summary>A discovered addon template with source and optional compiled files.</summary>
public sealed record AddonPreset(string Name, string Path);

/// <summary>Discovers and stages addon templates without overwriting existing addons.</summary>
public static class AddonPresetFiles
{
    private static readonly string[] Areas = ["content", "game"];
    /// <summary>Discovers templates in priority order, retaining the first of each name.</summary>
    public static IReadOnlyList<AddonPreset> Discover(IEnumerable<string>? roots = null)
    {
        roots ??= [
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Hammer5Tools", "Presets"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Hammer5Tools", "userdata", "Presets"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Hammer5Tools", "Presets"),
            BundledPresetFiles.GetDirectory("addons"),
            Path.Combine(AppContext.BaseDirectory, "Presets")];
        var found = new Dictionary<string, AddonPreset>(StringComparer.OrdinalIgnoreCase);
        foreach (var root in roots.Where(Directory.Exists))
        {
            foreach (var path in Directory.EnumerateDirectories(root))
            {
                if (Directory.Exists(Path.Combine(path, "content"))) found.TryAdd(Path.GetFileName(path), new(Path.GetFileName(path), path));
            }
        }
        return found.Values.OrderBy(preset => preset.Name, StringComparer.OrdinalIgnoreCase).ToArray();
    }

    /// <summary>Reads the saved Hammer map thumbnail from a preset.</summary>
    public static byte[]? ReadThumbnail(AddonPreset preset)
    {
        var path = Path.Combine(preset.Path, "content", "maps", "xxx_mapname_xxx.vmap");
        if (!File.Exists(path)) return null;
        using var stream = File.OpenRead(path);
        var model = Datamodel.Datamodel.Load(stream);
        return model.PrefixAttributes.TryGetValue("asset_preview_thumbnail", out var value) && value is IEnumerable<byte> bytes ? bytes.ToArray() : null;
    }

    /// <summary>Creates a staged template copy and substitutes legacy filename tokens.</summary>
    public static void Create(string installation, string addonName, string? presetPath)
    {
        AddonArchive.ValidateName(addonName);
        if (addonName.Any(character => !(character is >= 'a' and <= 'z' or >= '0' and <= '9' or '_')))
            throw new ArgumentException("Use lowercase letters, numbers and underscores for the addon name.", nameof(addonName));
        var destinations = Areas.Select(area => Path.Combine(installation, area, "csgo_addons", addonName)).ToArray();
        if (destinations.Any(path => Directory.Exists(path) || File.Exists(path))) throw new IOException("An addon with that name already exists.");
        if (presetPath is not null && !Directory.Exists(Path.Combine(presetPath, "content"))) throw new DirectoryNotFoundException("The preset content folder was not found.");
        var staging = Path.Combine(installation, $".h5t-create-{Guid.NewGuid():N}");
        var moved = new List<string>();
        try
        {
            foreach (var area in Areas)
            {
                var target = Path.Combine(staging, area);
                Directory.CreateDirectory(target);
                if (presetPath is null) continue;
                var source = Path.Combine(presetPath, area);
                if (!Directory.Exists(source)) continue;
                if ((File.GetAttributes(source) & FileAttributes.ReparsePoint) != 0) throw new IOException("Presets cannot contain symbolic links.");
                foreach (var entry in Directory.EnumerateFileSystemEntries(source, "*", new EnumerationOptions { RecurseSubdirectories = true, AttributesToSkip = 0 }))
                {
                    var attributes = File.GetAttributes(entry);
                    if ((attributes & FileAttributes.ReparsePoint) != 0) throw new IOException("Presets cannot contain symbolic links.");
                    var relative = Path.GetRelativePath(source, entry).Replace("xxx_mapname_xxx", addonName, StringComparison.Ordinal);
                    var destination = Path.Combine(target, relative);
                    if ((attributes & FileAttributes.Directory) != 0) Directory.CreateDirectory(destination);
                    else
                    {
                        Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
                        File.Copy(entry, destination);
                    }
                }
            }
            if (presetPath is null)
            {
                foreach (var folder in new[] { "maps", "materials", "models", "sounds", "particles", "scripts", "smartprops", "soundevents", "postprocess" })
                    Directory.CreateDirectory(Path.Combine(staging, "content", folder));
            }
            for (var i = 0; i < destinations.Length; i++)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(destinations[i])!);
                Directory.Move(Path.Combine(staging, i == 0 ? "content" : "game"), destinations[i]);
                moved.Add(destinations[i]);
            }
        }
        catch
        {
            foreach (var path in moved) Directory.Delete(path, recursive: true);
            throw;
        }
        finally
        {
            if (Directory.Exists(staging)) Directory.Delete(staging, recursive: true);
        }
    }
}
