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
                            if (results.Count >= 500)
                            {
                                break;
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to read CS2 VPK sounds from {Path}", pakDir);
            }

            return results;
        }, cancellationToken);
    }
}
