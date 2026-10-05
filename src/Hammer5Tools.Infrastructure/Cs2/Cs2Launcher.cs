namespace Hammer5Tools.Infrastructure.Cs2;

using System.Diagnostics;
using System.IO;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.Settings;
using Microsoft.Extensions.Logging;

/// <summary>
/// Service managing the launching, monitoring, and termination of the Counter-Strike 2 process.
/// </summary>
public class Cs2Launcher : ICs2Launcher, IDisposable
{
    public const string PipeIn = @"\\.\pipe\hammer5tools_cmd";
    public const string PipeOut = @"\\.\pipe\hammer5tools_out";
    public const string LogFileName = "hammer5tools_console.log";

    private readonly ICs2Locator Cs2Locator;
    private readonly IAddonService AddonService;
    private readonly ISettingsService SettingsService;
    private readonly ILogger<Cs2Launcher>? Logger;
    private readonly Lock SyncLock = new();

    private Process? MonitoredProcess;

    public bool IsRunning
    {
        get
        {
            lock (SyncLock)
            {
                if (MonitoredProcess is { HasExited: false })
                {
                    return true;
                }

                var existing = Process.GetProcessesByName("cs2");
                var running = existing.Length > 0;
                foreach (var p in existing)
                {
                    p.Dispose();
                }

                return running;
            }
        }
    }

    public int? ProcessId
    {
        get
        {
            lock (SyncLock)
            {
                if (MonitoredProcess is { HasExited: false })
                {
                    return MonitoredProcess.Id;
                }

                var existing = Process.GetProcessesByName("cs2");
                try
                {
                    return existing.Length > 0 ? existing[0].Id : null;
                }
                finally
                {
                    foreach (var p in existing)
                    {
                        p.Dispose();
                    }
                }
            }
        }
    }

    public event EventHandler<bool>? ProcessStateChanged;

    public Cs2Launcher(
        ICs2Locator cs2Locator,
        IAddonService addonService,
        ISettingsService settingsService,
        ILogger<Cs2Launcher>? logger = null)
    {
        Cs2Locator = cs2Locator;
        AddonService = addonService;
        SettingsService = settingsService;
        Logger = logger;
    }

    /// <inheritdoc/>
    public string BuildLaunchArguments(string? additionalArgs = null, bool ncmMode = false)
    {
        var args = new List<string>
        {
            "-tools",
            "-insecure",
            $"-concommandpipe {PipeIn},{PipeOut}",
            $"-con_logfile {LogFileName}",
            "-disable_workshop_command_filtering",
        };

        var activeAddon = AddonService.ActiveAddon?.Name ?? SettingsService.Settings.SelectedAddon;
        if (!string.IsNullOrWhiteSpace(activeAddon))
        {
            args.Add($"-addon {activeAddon}");
        }

        if (ncmMode || SettingsService.Settings.Editor.LaunchNcmMode)
        {
            args.Add("-noworkshoppreview");
        }

        var customArgs = SettingsService.Settings.Editor.CustomLaunchArgs;
        if (!string.IsNullOrWhiteSpace(customArgs))
        {
            foreach (var part in customArgs.Split(' ', StringSplitOptions.RemoveEmptyEntries))
            {
                if (!args.Contains(part, StringComparer.OrdinalIgnoreCase))
                {
                    args.Add(part);
                }
            }
        }

        if (!string.IsNullOrWhiteSpace(additionalArgs))
        {
            foreach (var part in additionalArgs.Split(' ', StringSplitOptions.RemoveEmptyEntries))
            {
                if (!args.Contains(part, StringComparer.OrdinalIgnoreCase))
                {
                    args.Add(part);
                }
            }
        }

        return string.Join(" ", args);
    }

    /// <inheritdoc/>
    public Task<bool> LaunchAsync(string? additionalArgs = null, bool ncmMode = false, CancellationToken ct = default)
    {
        var cs2Path = Cs2Locator.ResolvedCs2Path;
        if (string.IsNullOrWhiteSpace(cs2Path))
        {
            Logger?.LogError("Cannot launch CS2: Installation path not found.");
            return Task.FromResult(false);
        }

        var exePath = Cs2Paths.GetCs2ExePath(cs2Path);
        if (!File.Exists(exePath))
        {
            Logger?.LogError("Cannot launch CS2: Executable not found at {Path}", exePath);
            return Task.FromResult(false);
        }

        var launchArgs = BuildLaunchArguments(additionalArgs, ncmMode);
        var workingDir = Cs2Paths.GetBinWin64Path(cs2Path);

        Logger?.LogInformation("Launching CS2: {Exe} {Args}", exePath, launchArgs);

        try
        {
            var startInfo = new ProcessStartInfo
            {
                FileName = exePath,
                Arguments = launchArgs,
                WorkingDirectory = workingDir,
                UseShellExecute = false,
            };

            var process = Process.Start(startInfo);
            if (process is null)
            {
                Logger?.LogError("Failed to start CS2 process.");
                return Task.FromResult(false);
            }

            lock (SyncLock)
            {
                MonitoredProcess?.Dispose();
                MonitoredProcess = process;
                MonitoredProcess.EnableRaisingEvents = true;
                MonitoredProcess.Exited += OnProcessExited;
            }

            ProcessStateChanged?.Invoke(this, true);
            return Task.FromResult(true);
        }
        catch (Exception ex)
        {
            Logger?.LogError(ex, "Exception while launching CS2 process.");
            return Task.FromResult(false);
        }
    }

    /// <inheritdoc/>
    public bool Kill()
    {
        var anyKilled = false;
        lock (SyncLock)
        {
            if (MonitoredProcess is { HasExited: false })
            {
                try
                {
                    MonitoredProcess.Kill(entireProcessTree: true);
                    anyKilled = true;
                }
                catch (Exception ex)
                {
                    Logger?.LogWarning(ex, "Failed to kill monitored CS2 process");
                }
            }

            var processes = Process.GetProcessesByName("cs2");
            foreach (var p in processes)
            {
                try
                {
                    p.Kill(entireProcessTree: true);
                    anyKilled = true;
                }
                catch (Exception ex)
                {
                    Logger?.LogWarning(ex, "Failed to kill CS2 process {Id}", p.Id);
                }
                finally
                {
                    p.Dispose();
                }
            }
        }

        if (anyKilled)
        {
            ProcessStateChanged?.Invoke(this, false);
        }

        return anyKilled;
    }

    /// <inheritdoc/>
    public async Task<bool> RestartAsync(string? additionalArgs = null, bool ncmMode = false, CancellationToken ct = default)
    {
        Kill();
        await Task.Delay(500, ct);
        return await LaunchAsync(additionalArgs, ncmMode, ct);
    }

    private void OnProcessExited(object? sender, EventArgs e)
    {
        Logger?.LogInformation("CS2 process exited.");
        ProcessStateChanged?.Invoke(this, false);
    }

    public void Dispose()
    {
        lock (SyncLock)
        {
            MonitoredProcess?.Dispose();
            MonitoredProcess = null;
        }

        GC.SuppressFinalize(this);
    }
}
