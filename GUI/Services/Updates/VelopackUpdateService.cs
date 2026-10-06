namespace Hammer5Tools.App.Services.Updates;

using Hammer5Tools.Core.Settings;
using Microsoft.Extensions.Logging;
using Velopack;
using Velopack.Locators;
using Velopack.Sources;

/// <summary>
/// Update service checking for releases based on configured update channel.
/// </summary>
public sealed class VelopackUpdateService : IUpdateService
{
    public const string RepositoryUrl = "https://github.com/dertwist/Hammer5Tools";

    private readonly ILogger<VelopackUpdateService>? Logger;
    private readonly Func<string, UpdateManager> CreateManager;
    private UpdateManager? Manager;
    private UpdateInfo? Update;
    private string ChannelValue = "stable";

    public bool IsChecking { get; private set; }
    public string Channel
    {
        get => ChannelValue;
        set
        {
            var channel = value == "dev" ? "dev" : "stable";
            if (ChannelValue == channel) return;
            if (IsChecking) throw new InvalidOperationException("Wait for the current update operation before changing channels.");
            ChannelValue = channel;
            Update = null;
            IsDownloaded = false;
        }
    }
    public string Status { get; private set; } = "Check for updates to receive the latest fixes.";
    public string? AvailableVersion => Update?.TargetFullRelease.Version.ToString();
    public bool IsDownloaded { get; private set; }

    public VelopackUpdateService(ISettingsService? settingsService = null, ILogger<VelopackUpdateService>? logger = null)
        : this(channel => new UpdateManager(new GithubSource(RepositoryUrl, null, channel == "dev"),
            new UpdateOptions { ExplicitChannel = channel },
            VelopackLocator.IsCurrentSet ? VelopackLocator.Current : VelopackLocator.CreateDefaultForPlatform()),
            settingsService?.Settings.UpdateChannel ?? "stable", logger)
    {
    }

    internal VelopackUpdateService(Func<string, UpdateManager> createManager, string channel = "stable", ILogger<VelopackUpdateService>? logger = null)
    {
        CreateManager = createManager;
        Channel = channel;
        Logger = logger;
    }

    public async Task<bool> CheckForUpdatesAsync(bool silent = true, CancellationToken ct = default)
    {
        if (IsChecking)
        {
            return false;
        }

        IsChecking = true;
        Update = null;
        IsDownloaded = false;
        try
        {
            ct.ThrowIfCancellationRequested();
            Manager = CreateManager(Channel == "dev" ? "dev" : "stable");
            if (!Manager.IsInstalled)
            {
                Status = "This copy is not a Velopack installation. Download the latest installer from GitHub Releases.";
                return false;
            }

            Status = "Checking for updates...";
            var update = await Manager.CheckForUpdatesAsync().WaitAsync(ct);
            if (update is not null && (update.TargetFullRelease.PackageId != Manager.AppId
                || update.DeltasToTarget.Any(asset => asset.PackageId != Manager.AppId)))
            {
                throw new InvalidDataException("The update feed contains packages for a different application.");
            }
            Update = update;
            Status = Update is null ? "No newer update is available on this channel." : $"Version {AvailableVersion} is available.";
            return Update is not null;
        }
        catch (Exception ex)
        {
            Status = $"Could not check for updates: {ex.Message}";
            Logger?.LogWarning(ex, "Update check failed");
            throw;
        }
        finally
        {
            IsChecking = false;
        }
    }

    public async Task DownloadUpdateAsync(Action<int>? progress = null, CancellationToken ct = default)
    {
        if (IsChecking || Manager is null || Update is null)
        {
            throw new InvalidOperationException("Check for an available update before downloading.");
        }

        IsChecking = true;
        IsDownloaded = false;
        try
        {
            Status = "Downloading update...";
            await Manager.DownloadUpdatesAsync(Update, progress, ct);
            IsDownloaded = true;
            Status = $"Version {AvailableVersion} is ready. Restart to install it.";
        }
        catch (Exception ex)
        {
            Status = $"Could not download the update: {ex.Message}";
            Logger?.LogWarning(ex, "Update download failed");
            throw;
        }
        finally
        {
            IsChecking = false;
        }
    }

    public void ApplyUpdateAndRestart()
    {
        if (!IsDownloaded || Manager is null || Update is null)
        {
            throw new InvalidOperationException("Download an update before restarting.");
        }

        Manager.ApplyUpdatesAndRestart(Update.TargetFullRelease);
    }
}
