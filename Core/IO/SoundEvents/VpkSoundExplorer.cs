namespace Hammer5Tools.Core.IO.SoundEvents;

using Hammer5Tools.Core.Cs2;
using Microsoft.Extensions.Logging;
using SteamDatabase.ValvePak;

public class VpkSoundExplorer
{
    private readonly ICs2Locator Cs2Locator;
    private readonly ILogger<VpkSoundExplorer> Logger;

    public VpkSoundExplorer(ICs2Locator cs2Locator, ILogger<VpkSoundExplorer> logger)
    {
        Cs2Locator = cs2Locator;
        Logger = logger;
    }

    public async Task<IReadOnlyList<string>> EnumerateVpkSoundsAsync(string? filter = null, CancellationToken cancellationToken = default)
    {
        return await Task.Run(() =>
        {
            var results = new List<string>();
            var cs2Root = Cs2Locator.FindCs2Path();
            if (cs2Root is null)
            {
                return results;
            }

            var pakDir = Path.Combine(cs2Root, "game", "csgo", "pak01_dir.vpk");
            if (!File.Exists(pakDir))
            {
                return results;
            }

            try
            {
                using var package = new Package();
                package.Read(pakDir);

                if (package.Entries is not null && package.Entries.TryGetValue("vsnd_c", out var entries) && entries is not null)
                {
                    foreach (var entry in entries)
                    {
                        cancellationToken.ThrowIfCancellationRequested();
                        var fullName = $"{entry.DirectoryName}/{entry.FileName}.vsnd";
                        if (filter is null || fullName.Contains(filter, StringComparison.OrdinalIgnoreCase))
                        {
                            results.Add(fullName);
                        }
                    }
                }
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                Logger.LogError(ex, "Failed to read CS2 VPK sounds from {Path}", pakDir);
            }

            return results;
        }, cancellationToken);
    }
    /// <summary>Reads game sound-event definitions without mutating the source resources.</summary>
    public Task<IReadOnlyList<Hammer5Tools.Core.SoundEvents.SoundEvent>> ReadInternalEventsAsync(CancellationToken cancellationToken = default)
        => Task.Run<IReadOnlyList<Hammer5Tools.Core.SoundEvents.SoundEvent>>(() =>
        {
            var events = new Dictionary<string, Hammer5Tools.Core.SoundEvents.SoundEvent>(StringComparer.Ordinal);
            var root = Cs2Locator.FindCs2Path();
            if (root is null) return [];
            var looseRoot = Path.Combine(root, "game", "csgo", "soundevents");
            if (Directory.Exists(looseRoot))
            {
                foreach (var path in Directory.EnumerateFiles(looseRoot, "*.vsndevts", SearchOption.AllDirectories))
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    Add(File.ReadAllText(path));
                }
            }
            var archive = Path.Combine(root, "game", "csgo", "pak01_dir.vpk");
            if (File.Exists(archive))
            {
                using var package = new Package();
                package.Read(archive);
                if (package.Entries?.TryGetValue("vsndevts_c", out var entries) == true)
                {
                    foreach (var entry in entries)
                    {
                        cancellationToken.ThrowIfCancellationRequested();
                        try
                        {
                            package.ReadEntry(entry, out var bytes);
                            using var stream = new MemoryStream(bytes);
                            using var resource = new ValveResourceFormat.Resource();
                            resource.Read(stream);
                            using var content = ValveResourceFormat.IO.FileExtract.Extract(resource, null!);
                            if (content.Data is { } data) Add(System.Text.Encoding.UTF8.GetString(data));
                        }
                        catch (Exception ex) when (ex is not OperationCanceledException)
                        {
                            Logger.LogWarning(ex, "Could not read built-in sound events {Entry}", entry.FileName);
                        }
                    }
                }
            }
            return events.Values.OrderBy(item => item.Name, StringComparer.Ordinal).ToArray();

            void Add(string text)
            {
                foreach (var item in Hammer5Tools.Core.SoundEvents.SoundEventDocument.Parse(text).Events)
                    events.TryAdd(item.Name, item);
            }
        }, cancellationToken);

}
