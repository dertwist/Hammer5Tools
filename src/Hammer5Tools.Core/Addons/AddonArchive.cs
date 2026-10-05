namespace Hammer5Tools.Core.Addons;

using System.IO.Compression;

/// <summary>Exports and imports the legacy content/game addon ZIP layout.</summary>
public static class AddonArchive
{
    /// <summary>Rejects names that could escape an addon directory.</summary>
    public static void ValidateName(string name)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(name);
        if (name is "." or ".." || name.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0
            || name.Contains('/') || name.Contains('\\') || name.EndsWith('.') || name.EndsWith(' '))
        {
            throw new ArgumentException("Use a single valid folder name for the addon.", nameof(name));
        }
    }

    /// <summary>Writes source and compiled files into a ZIP, replacing it only after completion.</summary>
    public static void Export(Addon addon, string destination)
    {
        ValidateName(addon.Name);
        var temporary = destination + $".{Guid.NewGuid():N}.tmp";
        try
        {
            using (var zip = ZipFile.Open(temporary, ZipArchiveMode.Create))
            {
                AddFolder(zip, addon.ContentPath, $"content/csgo_addons/{addon.Name}");
                AddFolder(zip, addon.GamePath, $"game/csgo_addons/{addon.Name}");
            }
            File.Move(temporary, destination, overwrite: true);
        }
        finally
        {
            File.Delete(temporary);
        }
    }

    private static void AddFolder(ZipArchive zip, string folder, string prefix)
    {
        if (!Directory.Exists(folder))
        {
            return;
        }
        foreach (var file in Directory.EnumerateFiles(folder, "*", new EnumerationOptions { RecurseSubdirectories = true, AttributesToSkip = FileAttributes.ReparsePoint, IgnoreInaccessible = false }))
        {
            if ((File.GetAttributes(file) & FileAttributes.ReparsePoint) != 0)
            {
                throw new IOException("Addon archives cannot include symbolic links.");
            }
            zip.CreateEntryFromFile(file, $"{prefix}/{Path.GetRelativePath(folder, file).Replace('\\', '/')}", CompressionLevel.Optimal);
        }
    }

    /// <summary>Imports a single addon without overwriting existing content or game folders.</summary>
    public static string Import(string archive, string installation)
    {
        using var zip = ZipFile.OpenRead(archive);
        var files = zip.Entries.Where(entry => !entry.FullName.EndsWith('/')).ToArray();
        if (files.Length == 0)
        {
            throw new InvalidDataException("The archive contains no addon files.");
        }
        string? addonName = null;
        foreach (var entry in files)
        {
            var parts = entry.FullName.Replace('\\', '/').Split('/');
            if (parts.Length < 4 || parts[0] is not ("content" or "game") || parts[1] != "csgo_addons"
                || parts.Any(part => part is "." or ".." or "" || part.Contains(':')))
            {
                throw new InvalidDataException("The archive contains a file outside the addon layout.");
            }
            ValidateName(parts[2]);
            addonName ??= parts[2];
            if (addonName != parts[2])
            {
                throw new InvalidDataException("Import one addon at a time.");
            }
        }
        foreach (var area in new[] { "content", "game" })
        {
            if (Directory.Exists(Path.Combine(installation, area, "csgo_addons", addonName!)))
            {
                throw new IOException($"Addon {addonName} already exists. Import does not overwrite addons.");
            }
        }
        var staging = Path.Combine(installation, $".h5t-import-{Guid.NewGuid():N}");
        try
        {
            zip.ExtractToDirectory(staging);
            foreach (var area in new[] { "content", "game" })
            {
                var source = Path.Combine(staging, area, "csgo_addons", addonName!);
                if (!Directory.Exists(source))
                {
                    continue;
                }
                var target = Path.Combine(installation, area, "csgo_addons", addonName!);
                Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                Directory.Move(source, target);
            }
            return addonName!;
        }
        finally
        {
            if (Directory.Exists(staging))
            {
                Directory.Delete(staging, recursive: true);
            }
        }
    }
}
