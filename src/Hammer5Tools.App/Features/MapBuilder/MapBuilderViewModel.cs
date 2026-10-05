namespace Hammer5Tools.App.Features.MapBuilder;

using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.Services;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.MapBuilder;
using Hammer5Tools.Core.Settings;

public sealed class MapBuilderViewModel : DocumentViewModel
{
    private readonly IAddonService AddonService;
    private readonly IMapBuilderService MapBuilderService;
    private readonly ISettingsService? SettingsService;
    private readonly IDialogService? DialogService;
    private MapBuildConfiguration? SelectedConfigurationValue;
    private MapBuildOptions OptionsValue = new();
    private string? SelectedMapValue;
    private MapBuildJob? SelectedJobValue;
    private string StatusValue = "Ready";
    private bool IsBuildingValue;
    private bool IsDisposed;
    private bool IsRunningMap;
    private readonly Avalonia.Threading.DispatcherTimer? UsageTimer;
    public string CpuUsage { get; private set; } = "CPU Usage — unavailable";
    public string MemoryUsage { get; private set; } = "Memory Usage — unavailable";
    public string GpuUsage { get; private set; } = "GPU Usage — unavailable";
    public double[] CpuSamples { get; private set; } = [];
    public double[] MemorySamples { get; private set; } = [];
    public double[] GpuSamples { get; private set; } = [];

    public ObservableCollection<MapBuildConfiguration> Configurations { get; } = [];
    public ObservableCollection<string> Maps { get; } = [];
    public ObservableCollection<MapBuildJob> Jobs { get; } = [];
    public ObservableCollection<BuildLogLine> Logs { get; } = [];
    public int[] Resolutions { get; } = [256, 512, 1024, 2048, 4096, 8192];
    public string[] Qualities { get; } = ["Fast", "Standard", "Final", "Ultra"];
    public string NewPresetName { get; set; } = "Custom";
    public string MapName { get; set; } = string.Empty;

    public MapBuildConfiguration? SelectedConfiguration
    {
        get => SelectedConfigurationValue;
        set
        {
            if (SetProperty(ref SelectedConfigurationValue, value) && value is not null)
            {
                Options = value.Options with { };
                if (Options.SaveMapPath)
                {
                    Maps.Clear();
                    foreach (var map in value.Maps) Maps.Add(map);
                    SelectedMap = Maps.FirstOrDefault();
                }
                Title = $"Map Builder - {value.Name}";
            }
        }
    }

    public MapBuildOptions Options
    {
        get => OptionsValue;
        private set => SetProperty(ref OptionsValue, value);
    }

    public string? SelectedMap
    {
        get => SelectedMapValue;
        set => SetProperty(ref SelectedMapValue, value);
    }

    public MapBuildJob? SelectedJob
    {
        get => SelectedJobValue;
        set
        {
            if (SetProperty(ref SelectedJobValue, value))
            {
                Logs.Clear();
                RefreshOutput();
            }
        }
    }

    public string Status
    {
        get => StatusValue;
        private set => SetProperty(ref StatusValue, value);
    }

    public bool IsBuilding
    {
        get => IsBuildingValue;
        private set
        {
            if (SetProperty(ref IsBuildingValue, value))
            {
                StartBuildCommand.NotifyCanExecuteChanged();
                CancelBuildCommand.NotifyCanExecuteChanged();
            }
        }
    }

    public IAsyncRelayCommand StartBuildCommand { get; }
    public IRelayCommand CancelBuildCommand { get; }
    public IAsyncRelayCommand RunMapCommand { get; }
    public IAsyncRelayCommand AddMapCommand { get; }
    public IRelayCommand RemoveMapCommand { get; }
    public IRelayCommand SavePresetCommand { get; }
    public IRelayCommand NewPresetCommand { get; }

    public MapBuilderViewModel(IAddonService addonService, IMapBuilderService mapBuilderService,
        ISettingsService? settingsService = null, IDialogService? dialogService = null, ISystemUsageService? systemUsageService = null)
    {
        AddonService = addonService;
        MapBuilderService = mapBuilderService;
        SettingsService = settingsService;
        DialogService = dialogService;
        StartBuildCommand = new AsyncRelayCommand(OnStartBuildAsync, () => !IsBuilding);
        CancelBuildCommand = new RelayCommand(OnCancelBuild, () => IsBuilding);
        RunMapCommand = new AsyncRelayCommand(OnRunMapAsync);
        AddMapCommand = new AsyncRelayCommand(OnAddMapAsync);
        RemoveMapCommand = new RelayCommand(() =>
        {
            if (SelectedMap is { } map) Maps.Remove(map);
            SelectedMap = Maps.FirstOrDefault();
        });
        SavePresetCommand = new RelayCommand(SavePreset);
        NewPresetCommand = new RelayCommand(CreatePreset);
        var saved = SettingsService?.Settings.MapBuildPresets;
        foreach (var configuration in saved is { Count: > 0 } ? saved.ToArray() : MapBuildConfiguration.CreateDefaults())
        {
            Configurations.Add(configuration with { Options = configuration.Options with { }, Maps = [.. configuration.Maps] });
        }
        if (AddonService.ActiveAddon is { } addon)
        {
            Maps.Add(addon.Name);
            SelectedMap = addon.Name;
        }
        SelectedConfiguration = Configurations[0];
        foreach (var job in MapBuilderService.Jobs) Jobs.Add(job);
        SelectedJob = Jobs.LastOrDefault();
        IsBuilding = Jobs.Any(IsActive);
        MapBuilderService.JobUpdated += OnJobUpdated;
        if (systemUsageService is not null)
        {
            UsageTimer = new Avalonia.Threading.DispatcherTimer { Interval = TimeSpan.FromSeconds(1) };
            UsageTimer.Tick += (_, _) => UpdateUsage(systemUsageService.Read());
            UpdateUsage(systemUsageService.Read());
            UsageTimer.Start();
        }
    }

    private async Task OnAddMapAsync()
    {
        var path = DialogService is null ? MapName : await DialogService.OpenFileAsync("Add VMAP", "*.vmap");
        if (!string.IsNullOrWhiteSpace(path) && !Maps.Contains(path))
        {
            Maps.Add(path);
            SelectedMap = path;
        }
    }

    private void SavePreset()
    {
        if (SelectedConfiguration is not { } selected) return;
        var updated = selected with { Options = Options with { }, Maps = Options.SaveMapPath ? [.. Maps] : [] };
        Configurations[Configurations.IndexOf(selected)] = updated;
        SelectedConfiguration = updated;
        PersistPresets();
    }

    private void CreatePreset()
    {
        var name = NewPresetName.Trim();
        if (string.IsNullOrEmpty(name) || Configurations.Any(configuration => configuration.Name.Equals(name, StringComparison.OrdinalIgnoreCase)))
        {
            Status = "Enter a unique preset name.";
            return;
        }
        var configuration = new MapBuildConfiguration(name, Options with { }, Options.SaveMapPath ? [.. Maps] : []);
        Configurations.Add(configuration);
        SelectedConfiguration = configuration;
        PersistPresets();
    }

    private void PersistPresets()
    {
        SettingsService?.Update(settings => settings.MapBuildPresets = Configurations.Select(configuration =>
            configuration with { Options = configuration.Options with { }, Maps = [.. configuration.Maps] }).ToList());
        Status = "Preset saved.";
    }

    private async Task OnStartBuildAsync()
    {
        if (AddonService.ActiveAddon is not { } addon || Maps.Count == 0)
        {
            Status = "Select an addon and add a VMAP before building.";
            return;
        }
        try
        {
            IsBuilding = true;
            foreach (var map in Maps.ToArray())
            {
                SelectedJob = await MapBuilderService.EnqueueBuildAsync(addon.Name, map, Options);
            }
        }
        catch (Exception ex)
        {
            Status = ex.Message;
            Logs.Add(new BuildLogLine($"Error: {ex.Message}"));
            IsBuilding = Jobs.Any(IsActive);
        }
    }

    private async Task OnRunMapAsync(CancellationToken ct)
    {
        if (AddonService.ActiveAddon is not { } addon || SelectedMap is not { } map) return;
        try
        {
            IsRunningMap = true;
            IsBuilding = true;
            await MapBuilderService.RunMapAsync(addon.Name, map, Options.BuildCubemaps, ct);
            Status = $"Run: {map}";
        }
        catch (OperationCanceledException)
        {
            Status = "Run cancelled.";
        }
        catch (Exception ex)
        {
            Status = ex.Message;
            Logs.Add(new BuildLogLine($"Error: {ex.Message}"));
        }
        finally
        {
            IsRunningMap = false;
            IsBuilding = Jobs.Any(IsActive);
        }
    }

    private void OnCancelBuild()
    {
        RunMapCommand.Cancel();
        foreach (var job in Jobs.Where(IsActive).ToArray()) MapBuilderService.CancelJob(job.Id);
    }

    private static bool IsActive(MapBuildJob job) => job.Status is "Queued" or "Building" or "Running" or "Cubemaps";

    private void OnJobUpdated(object? sender, MapBuildJob job)
    {
        Avalonia.Threading.Dispatcher.UIThread.Post(() =>
        {
            if (IsDisposed) return;
            if (!Jobs.Any(item => item.Id == job.Id)) Jobs.Add(job);
            if (SelectedJob?.Id == job.Id)
            {
                RefreshOutput();
                OnPropertyChanged(nameof(SelectedJob));
            }
            IsBuilding = IsRunningMap || Jobs.Any(IsActive);
        });
    }

    private void RefreshOutput()
    {
        if (SelectedJob is not { } job) return;
        foreach (var line in job.Output.Skip(Logs.Count)) Logs.Add(new BuildLogLine($"[{line.RecordedAt.LocalDateTime:HH:mm:ss}] {line.Text}"));
        Status = $"{job.MapName} — {job.Status}";
    }

    private void UpdateUsage(SystemUsage usage)
    {
        CpuUsage = usage.Cpu is { } cpu ? $"CPU Usage — {cpu:F1}%" : "CPU Usage — unavailable";
        MemoryUsage = usage.Memory is { } memory ? $"Memory Usage — {memory:F1}%" : "Memory Usage — unavailable";
        GpuUsage = usage.Gpu is { } gpu ? $"GPU Usage — {gpu:F1}%" : "GPU Usage — unavailable";
        CpuSamples = usage.Cpu is { } cpuValue ? [.. CpuSamples.TakeLast(59), cpuValue] : [];
        MemorySamples = usage.Memory is { } memoryValue ? [.. MemorySamples.TakeLast(59), memoryValue] : [];
        GpuSamples = usage.Gpu is { } gpuValue ? [.. GpuSamples.TakeLast(59), gpuValue] : [];
        OnPropertyChanged(nameof(CpuUsage));
        OnPropertyChanged(nameof(MemoryUsage));
        OnPropertyChanged(nameof(GpuUsage));
        OnPropertyChanged(nameof(CpuSamples));
        OnPropertyChanged(nameof(MemorySamples));
        OnPropertyChanged(nameof(GpuSamples));
    }

    public override void Dispose()
    {
        IsDisposed = true;
        RunMapCommand.Cancel();
        UsageTimer?.Stop();
        MapBuilderService.JobUpdated -= OnJobUpdated;
        base.Dispose();
    }
}

public sealed record BuildLogLine
{
    public string Text { get; }
    public bool IsError { get; }
    public bool IsWarning { get; }
    public bool IsPhase { get; }

    public BuildLogLine(string raw)
    {
        Text = System.Net.WebUtility.HtmlDecode(System.Text.RegularExpressions.Regex.Replace(raw, "</?(?:font|span|b|p|br)\\b[^>]*>", string.Empty, System.Text.RegularExpressions.RegexOptions.IgnoreCase));
        IsError = Text.Contains("error", StringComparison.OrdinalIgnoreCase) || Text.Contains("exception", StringComparison.OrdinalIgnoreCase);
        IsWarning = !IsError && (Text.Contains("warning", StringComparison.OrdinalIgnoreCase) || raw.Contains("yellow", StringComparison.OrdinalIgnoreCase) || raw.Contains("#ffff00", StringComparison.OrdinalIgnoreCase));
        IsPhase = Text.Contains("Starting compilation:", StringComparison.Ordinal) || Text.Contains("Arguments:", StringComparison.Ordinal);
    }
}
