using Hammer5Tools.Core.Addons;
using ValveResourceFormat.IO;

namespace Hammer5Tools.Core.IO;

/// <summary>Opens the game and addon mount used by the managed SmartProp renderer.</summary>
public static class SmartPropRenderFiles
{
    /// <summary>Creates a renderer-owned loader with addon files taking priority over game files.</summary>
    public static GameFileLoader Open(string gameDirectory, string addon)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(gameDirectory);
        if (!string.IsNullOrWhiteSpace(addon))
        {
            AddonArchive.ValidateName(addon);
        }
        var game = Path.GetFullPath(gameDirectory);
        var addonFolder = Path.Combine(game, "csgo_addons", addon);
        var mount = string.IsNullOrWhiteSpace(addon) ? Path.Combine(game, "csgo") : addonFolder;
        var loader = new GameFileLoader(null, Path.Combine(mount, "h5t-preview.vmdl_c"));
        try
        {
            if (!string.IsNullOrWhiteSpace(addon) && Directory.Exists(addonFolder))
            {
                loader.AddDiskPathToSearch(addonFolder);
            }
            return loader;
        }
        catch
        {
            loader.Dispose();
            throw;
        }
    }
}
