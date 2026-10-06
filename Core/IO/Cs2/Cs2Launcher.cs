namespace Hammer5Tools.Core.IO.Cs2;

using System.Diagnostics;
using System.IO;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Commands;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.IO.Commands;
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
    private readonly ICommandService? CommandService;
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

    /// <inheritdoc/>
    public async Task<bool> RestartSteamAsync(CancellationToken ct = default)
    {
        ct.ThrowIfCancellationRequested();
        if (!OperatingSystem.IsWindows()) return false;
        var processes = Process.GetProcessesByName("steam");
        try
        {
            var executable = processes.FirstOrDefault()?.MainModule?.FileName;
            executable ??= IO.Cs2.Cs2Locator.GetSteamInstallPath() is { } path ? Path.Combine(path, "steam.exe") : null;
            if (executable is null || !File.Exists(executable)) return false;

            if (processes.Length > 0)
            {
                using var shutdown = Process.Start(new ProcessStartInfo(executable, "-shutdown") { UseShellExecute = true });
                if (shutdown is null) return false;
                await Task.WhenAll(processes.Select(process => process.WaitForExitAsync(ct)))
                    .WaitAsync(TimeSpan.FromSeconds(30), ct);
            }

            ct.ThrowIfCancellationRequested();
            using var restarted = Process.Start(new ProcessStartInfo(executable) { UseShellExecute = true });
            return restarted is not null;
        }
        catch (Exception ex) when (ex is System.ComponentModel.Win32Exception or InvalidOperationException or IOException or TimeoutException)
        {
            Logger?.LogWarning(ex, "Could not restart Steam.");
            return false;
        }
        finally
        {
            foreach (var process in processes) process.Dispose();
        }
    }

    public Cs2Launcher(
        ICs2Locator cs2Locator,
        IAddonService addonService,
        ISettingsService settingsService,
        ILogger<Cs2Launcher>? logger = null,
        ICommandService? commandService = null)
    {
        Cs2Locator = cs2Locator;
        CommandService = commandService;
        AddonService = addonService;
        SettingsService = settingsService;
        Logger = logger;
    }

    /// <inheritdoc/>
    public string BuildLaunchArguments(string? additionalArgs = null, bool ncmMode = false)
    {
        var editor = SettingsService.Settings.Editor;
        return editor.LaunchOptions.BuildArguments(
            AddonService.ActiveAddon?.Name ?? SettingsService.Settings.SelectedAddon,
            editor.CustomLaunchArgs, additionalArgs, ncmMode || editor.LaunchNcmMode);
    }

    /// <inheritdoc/>
    public async Task<bool> LaunchAsync(string? additionalArgs = null, bool ncmMode = false, CancellationToken ct = default)
    {
        var cs2Path = Cs2Locator.ResolvedCs2Path;
        if (string.IsNullOrWhiteSpace(cs2Path))
        {
            Logger?.LogError("Cannot launch CS2: Installation path not found.");
            return false;
        }

        var exePath = Cs2Paths.GetCs2ExePath(cs2Path);
        if (!File.Exists(exePath))
        {
            Logger?.LogError("Cannot launch CS2: Executable not found at {Path}", exePath);
            return false;
        }

        var launchArgs = BuildLaunchArguments(additionalArgs, ncmMode);
        var workingDir = Cs2Paths.GetBinWin64Path(cs2Path);

        Logger?.LogInformation("Launching CS2: {Exe} {Args}", exePath, launchArgs);

        try
        {
            if (ncmMode || SettingsService.Settings.Editor.LaunchNcmMode || SettingsService.Settings.Editor.LaunchOptions.NoCustomerMachine)
            {
                PrepareNcmFiles(cs2Path);
            }
            using var temporaryPipe = CommandService is null ? new CommandPipeClient(Logger) : null;
            var ready = CommandService is not null
                ? await CommandService.PrepareLaunchAsync(ct)
                : await temporaryPipe!.WaitUntilReadyAsync(ct);
            if (!ready)
            {
                Logger?.LogError("Cannot launch CS2: Command pipe host is unavailable.");
                return false;
            }
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
                return false;
            }

            lock (SyncLock)
            {
                MonitoredProcess?.Dispose();
                MonitoredProcess = process;
                MonitoredProcess.EnableRaisingEvents = true;
                MonitoredProcess.Exited += OnProcessExited;
            }

            ProcessStateChanged?.Invoke(this, true);
            return true;
        }
        catch (Exception ex)
        {
            Logger?.LogError(ex, "Exception while launching CS2 process.");
            return false;
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

    /// <summary>Creates missing internal tool files for no-customer-machine launches, preserving existing files.</summary>
    public static void PrepareNcmFiles(string cs2Path)
    {
        var bin = Path.Combine(cs2Path, "game", "bin");
        foreach (var (source, target) in new[] { ("assettypes_common.txt", "assettypes_internal.txt"), ("sdkenginetools.txt", "enginetools.txt") })
        {
            var destination = Path.Combine(bin, target);
            if (!File.Exists(destination)) File.Copy(Path.Combine(bin, source), destination);
        }
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
