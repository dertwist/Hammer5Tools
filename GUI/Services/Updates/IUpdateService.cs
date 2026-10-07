namespace Hammer5Tools.App.Services.Updates;

/// <summary>
/// Service managing application update checks and installations.
/// </summary>
public interface IUpdateService
{
    bool IsChecking { get; }

    string Channel { get; set; }

    string Status { get; }

    string? AvailableVersion { get; }

    bool IsDownloaded { get; }

    Task<IReadOnlyList<ReleaseNotes>> LoadReleaseNotesAsync(CancellationToken ct = default)
        => Task.FromResult<IReadOnlyList<ReleaseNotes>>([]);

    Task<bool> CheckForUpdatesAsync(bool silent = true, CancellationToken ct = default);

    Task DownloadUpdateAsync(Action<int>? progress = null, CancellationToken ct = default);

    void ApplyUpdateAndRestart();
}
