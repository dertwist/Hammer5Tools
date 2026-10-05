namespace Hammer5Tools.Core.IO.Addons;

using System.IO;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.Settings;
using Microsoft.Extensions.Logging;

/// <summary>
/// Service managing CS2 addons with filesystem discovery, watcher notifications, and lifecycle operations.
/// </summary>
public class AddonService : IAddonService, IDisposable
{
    private static readonly HashSet<string> ExcludedAddons = new(StringComparer.OrdinalIgnoreCase)
    {
        "addon_template",
        "workshop_items",
        ".git",
        ".vs",
    };

    private readonly ICs2Locator Cs2Locator;
    private readonly ISettingsService SettingsService;
    private readonly ILogger<AddonService>? Logger;
    private readonly Lock SyncLock = new();

    private List<Addon> CurrentAddons = [];
    private Addon? CurrentActiveAddon;
    private FileSystemWatcher? ContentWatcher;
    private Timer? DebounceTimer;

    public IReadOnlyList<Addon> Addons
    {
        get
        {
            lock (SyncLock)
            {
                return [.. CurrentAddons];
            }
        }
    }

    public Addon? ActiveAddon
    {
        get
        {
            lock (SyncLock)
            {
                return CurrentActiveAddon;
            }
        }
    }

    public event EventHandler<IReadOnlyList<Addon>>? AddonsChanged;
    public event EventHandler<Addon?>? ActiveAddonChanged;

    public AddonService(
        ICs2Locator cs2Locator,
        ISettingsService settingsService,
        ILogger<AddonService>? logger = null)
    {
        Cs2Locator = cs2Locator;
        SettingsService = settingsService;
        Logger = logger;

        RefreshAddons();
        SetupWatcher();
    }

    /// <inheritdoc/>
    public void RefreshAddons()
    {
        var cs2Path = Cs2Locator.ResolvedCs2Path;
        if (string.IsNullOrWhiteSpace(cs2Path) || !Directory.Exists(cs2Path))
        {
            lock (SyncLock)
            {
                CurrentAddons.Clear();
                CurrentActiveAddon = null;
            }

            AddonsChanged?.Invoke(this, []);
            ActiveAddonChanged?.Invoke(this, null);
            return;
        }

        var contentDir = Cs2Paths.GetContentAddonsPath(cs2Path);
        var gameDir = Cs2Paths.GetGameAddonsPath(cs2Path);

        var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        if (Directory.Exists(contentDir))
        {
            foreach (var dir in Directory.EnumerateDirectories(contentDir))
            {
                var name = Path.GetFileName(dir);
                if (!ExcludedAddons.Contains(name))
                {
                    names.Add(name);
                }
            }
        }

        if (Directory.Exists(gameDir))
        {
            foreach (var dir in Directory.EnumerateDirectories(gameDir))
            {
                var name = Path.GetFileName(dir);
                if (!ExcludedAddons.Contains(name))
                {
                    names.Add(name);
                }
            }
        }

        var newAddons = names
            .OrderBy(n => n, StringComparer.OrdinalIgnoreCase)
            .Select(name => new Addon(name, Cs2Paths.GetAddonContentPath(cs2Path, name), Cs2Paths.GetAddonGamePath(cs2Path, name)))
            .ToList();

        Addon? newActive = null;
        var savedName = SettingsService.Settings.SelectedAddon;

        if (!string.IsNullOrWhiteSpace(savedName))
        {
            newActive = newAddons.FirstOrDefault(a => string.Equals(a.Name, savedName, StringComparison.OrdinalIgnoreCase));
        }

        newActive ??= newAddons.FirstOrDefault();

        lock (SyncLock)
        {
            CurrentAddons = newAddons;
            CurrentActiveAddon = newActive;
        }

        AddonsChanged?.Invoke(this, [.. newAddons]);
        ActiveAddonChanged?.Invoke(this, newActive);
    }

    /// <inheritdoc/>
    public bool SetActiveAddon(string? addonName)
    {
        if (string.IsNullOrWhiteSpace(addonName))
        {
            lock (SyncLock)
            {
                CurrentActiveAddon = null;
            }

            SettingsService.Update(s => s.SelectedAddon = null);
            ActiveAddonChanged?.Invoke(this, null);
            return true;
        }

        Addon? target;
        lock (SyncLock)
        {
            target = CurrentAddons.FirstOrDefault(a => string.Equals(a.Name, addonName, StringComparison.OrdinalIgnoreCase));
            if (target is null)
            {
                return false;
            }

            CurrentActiveAddon = target;
        }

        SettingsService.Update(s => s.SelectedAddon = target.Name);
        Logger?.LogInformation("Active addon switched to {Addon}", target.Name);
        ActiveAddonChanged?.Invoke(this, target);
        return true;
    }

    /// <inheritdoc/>
    public Addon CreateAddon(string addonName)
    {
        AddonArchive.ValidateName(addonName);

        var cs2Path = Cs2Locator.ResolvedCs2Path;
        if (string.IsNullOrWhiteSpace(cs2Path) || !Directory.Exists(cs2Path))
        {
            throw new InvalidOperationException("Cannot create addon: CS2 installation directory is not resolved.");
        }

        var contentPath = Cs2Paths.GetAddonContentPath(cs2Path, addonName);
        var gamePath = Cs2Paths.GetAddonGamePath(cs2Path, addonName);

        string[] subdirs = ["maps", "materials", "models", "sounds", "particles", "scripts"];
        foreach (var sub in subdirs)
        {
            Directory.CreateDirectory(Path.Combine(contentPath, sub));
        }

        Directory.CreateDirectory(gamePath);

        RefreshAddons();
        SetActiveAddon(addonName);

        return new Addon(addonName, contentPath, gamePath);
    }

    /// <inheritdoc/>
    public bool DeleteAddon(string addonName)
    {
        AddonArchive.ValidateName(addonName);

        var cs2Path = Cs2Locator.ResolvedCs2Path;
        if (string.IsNullOrWhiteSpace(cs2Path))
        {
            return false;
        }

        var contentPath = Cs2Paths.GetAddonContentPath(cs2Path, addonName);
        var gamePath = Cs2Paths.GetAddonGamePath(cs2Path, addonName);

        try
        {
            if (Directory.Exists(contentPath))
            {
                Directory.Delete(contentPath, recursive: true);
            }

            if (Directory.Exists(gamePath))
            {
                Directory.Delete(gamePath, recursive: true);
            }

            RefreshAddons();
            return true;
        }
        catch (Exception ex)
        {
            Logger?.LogError(ex, "Failed to delete addon {Addon}", addonName);
            return false;
        }
    }

    private void SetupWatcher()
    {
        var cs2Path = Cs2Locator.ResolvedCs2Path;
        if (string.IsNullOrWhiteSpace(cs2Path))
        {
            return;
        }

        var contentAddons = Cs2Paths.GetContentAddonsPath(cs2Path);
        if (!Directory.Exists(contentAddons))
        {
            return;
        }

        try
        {
            ContentWatcher = new FileSystemWatcher(contentAddons)
            {
                NotifyFilter = NotifyFilters.DirectoryName,
                IncludeSubdirectories = false,
                EnableRaisingEvents = true,
            };

            ContentWatcher.Created += OnDirectoryChanged;
            ContentWatcher.Deleted += OnDirectoryChanged;
            ContentWatcher.Renamed += OnDirectoryChanged;
        }
        catch (Exception ex)
        {
            Logger?.LogWarning(ex, "Failed to start FileSystemWatcher on {Path}", contentAddons);
        }
    }

    private void OnDirectoryChanged(object sender, FileSystemEventArgs e)
    {
        DebounceTimer?.Dispose();
        DebounceTimer = new Timer(_ => RefreshAddons(), null, 300, Timeout.Infinite);
    }

    public void Dispose()
    {
        ContentWatcher?.Dispose();
        DebounceTimer?.Dispose();
        GC.SuppressFinalize(this);
    }
}
