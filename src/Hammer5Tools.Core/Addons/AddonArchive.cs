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
        => Export(addon, destination, new AddonExportOptions { IgnoreVersionControl = false, IgnoredExtensions = string.Empty, IncludeOtherCompiledFolders = true, IncludeThumbnailCache = true });

    /// <summary>Exports filtered, selected files with cancellation and completed-file progress.</summary>
    public static void Export(Addon addon, string destination, AddonExportOptions options, IProgress<int>? progress = null, CancellationToken cancellationToken = default)
    {
        ValidateName(addon.Name);
        var files = ListFiles(addon, options).Where(file => options.SelectedFiles is null || options.SelectedFiles.Contains(file.ArchivePath)).ToArray();
        if (files.Length == 0) throw new InvalidOperationException("Select at least one file to export.");
        var destinationPath = Path.GetFullPath(destination);
        if (files.Any(file => string.Equals(Path.GetFullPath(file.SourcePath), destinationPath, StringComparison.OrdinalIgnoreCase)))
            throw new IOException("Choose an archive destination outside the files being exported.");
        var temporary = destination + $".{Guid.NewGuid():N}.tmp";
        try
        {
            using (var zip = ZipFile.Open(temporary, ZipArchiveMode.Create))
            {
                var buffer = new byte[81920];
                for (var i = 0; i < files.Length; i++)
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    var file = files[i];
                    if ((File.GetAttributes(file.SourcePath) & FileAttributes.ReparsePoint) != 0) throw new IOException("Addon archives cannot include symbolic links.");
                    var entry = zip.CreateEntry(file.ArchivePath, options.Compression);
                    using var input = File.OpenRead(file.SourcePath);
                    using var output = entry.Open();
                    int read;
                    while ((read = input.Read(buffer)) > 0)
                    {
                        cancellationToken.ThrowIfCancellationRequested();
                        output.Write(buffer, 0, read);
                    }
                    progress?.Report(i + 1);
                }
            }
            cancellationToken.ThrowIfCancellationRequested();
            File.Move(temporary, destination, overwrite: true);
        }
        finally
        {
            File.Delete(temporary);
        }
    }

    /// <summary>Lists the files allowed by export filters, excluding linked directories.</summary>
    public static IReadOnlyList<AddonExportFile> ListFiles(Addon addon, AddonExportOptions options)
    {
        ValidateName(addon.Name);
        var result = new List<AddonExportFile>();
        var ignored = options.IgnoredExtensions.Split(',', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries)
            .Select(extension => extension.StartsWith('.') ? extension : "." + extension).ToArray();
        string[] defaultFolders = ["maps", "models", "materials", "postprocess", "smartprops", "soundevents", "sounds", "particles", "scripts"];
        foreach (var (area, folder) in new[] { ("content", addon.ContentPath), ("game", addon.GamePath) })
        {
            if (!Directory.Exists(folder)) continue;
            if ((File.GetAttributes(folder) & FileAttributes.ReparsePoint) != 0) throw new IOException("Addon archives cannot include symbolic links.");
            foreach (var file in Directory.EnumerateFiles(folder, "*", new EnumerationOptions { RecurseSubdirectories = true, AttributesToSkip = FileAttributes.ReparsePoint, IgnoreInaccessible = false }))
            {
                var relative = Path.GetRelativePath(folder, file).Replace('\\', '/');
                var parts = relative.Split('/');
                if (options.IgnoreVersionControl && parts.Any(part => part is ".git" or ".gitignore" or ".gitattributes" or ".diversion" or ".hg" or ".svn")) continue;
                if (ignored.Any(extension => file.EndsWith(extension, StringComparison.OrdinalIgnoreCase)) || (!options.IncludeThumbnailCache && parts[^1] == "tools_thumbnail_cache.bin")) continue;
                if (area == "content" && options.SkipNonDefaultContentFolders && parts.Length > 1 && !defaultFolders.Contains(parts[0], StringComparer.OrdinalIgnoreCase)) continue;
                if (area == "game" && parts.Length > 1 && !(parts[0].ToLowerInvariant() switch
                {
                    "maps" => options.IncludeCompiledMaps,
                    "materials" => options.IncludeCompiledMaterials,
                    "models" => options.IncludeCompiledModels,
                    _ => options.IncludeOtherCompiledFolders,
                })) continue;
                result.Add(new(file, $"{area}/csgo_addons/{addon.Name}/{relative}", new FileInfo(file).Length));
            }
        }
        return result.OrderBy(file => file.ArchivePath, StringComparer.OrdinalIgnoreCase).ToArray();
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
