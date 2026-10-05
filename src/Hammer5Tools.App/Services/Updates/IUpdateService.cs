namespace Hammer5Tools.App.Services.Updates;

/// <summary>
/// Service managing application update checks and installations.
/// </summary>
public interface IUpdateService
{
    bool IsChecking { get; }

    Task<bool> CheckForUpdatesAsync(bool silent = true, CancellationToken ct = default);
}
