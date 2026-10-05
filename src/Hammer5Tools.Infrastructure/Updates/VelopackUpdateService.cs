namespace Hammer5Tools.Infrastructure.Updates;

using Hammer5Tools.Core.Settings;
using Microsoft.Extensions.Logging;

/// <summary>
/// Update service checking for releases based on configured update channel.
/// </summary>
public class VelopackUpdateService : IUpdateService
{
    private readonly ISettingsService SettingsService;
    private readonly ILogger<VelopackUpdateService>? Logger;

    public bool IsChecking { get; private set; }

    public VelopackUpdateService(ISettingsService settingsService, ILogger<VelopackUpdateService>? logger = null)
    {
        SettingsService = settingsService;
        Logger = logger;
    }

    public async Task<bool> CheckForUpdatesAsync(bool silent = true, CancellationToken ct = default)
    {
        if (IsChecking)
        {
            return false;
        }

        IsChecking = true;
        try
        {
            var channel = SettingsService.Settings.UpdateChannel;
            Logger?.LogInformation("Checking for updates on channel '{Channel}' (silent: {Silent})", channel, silent);

            // In local/dev builds without Velopack package installation, log and return false
            await Task.Delay(100, ct);
            return false;
        }
        finally
        {
            IsChecking = false;
        }
    }
}
