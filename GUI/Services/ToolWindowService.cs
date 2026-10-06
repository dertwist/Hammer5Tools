namespace Hammer5Tools.App.Services;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Hammer5Tools.App.Features.MapBuilder;
using Hammer5Tools.App.Features.Preferences;
using Hammer5Tools.App.Features.Shell;
using Hammer5Tools.App.Features.SmartProps;
using Hammer5Tools.App.Features.SoundEvents;
using Hammer5Tools.App.Services.Lifecycle;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Cs2;
using Hammer5Tools.Core.MapBuilder;
using Hammer5Tools.Core.Settings;
using Hammer5Tools.Core.SoundEvents;
using Microsoft.Extensions.DependencyInjection;

public sealed class ToolWindowService
{
    private readonly IServiceProvider Services;
    private readonly DialogService Dialogs;
    private readonly Dictionary<StartupTool, Window> Windows = [];
    private bool ChangingAddon;

    public ToolWindowService(IServiceProvider services, DialogService dialogs)
    {
        Services = services;
        Dialogs = dialogs;
        Dialogs.ContextDocuments = GetDocuments;
        Dialogs.OpenWorkshop = () => Open(StartupTool.Workshop);
        Dialogs.OwnerWindow = () => Windows.Values.FirstOrDefault(window => window.IsActive)
            ?? Windows.Values.LastOrDefault(window => window.IsVisible);
    }

    public IReadOnlyList<DocumentViewModel> GetDocuments() => Windows.Values.SelectMany(window => window switch
    {
        StandaloneToolWindow standalone => new[] { standalone.Document },
        MainWindow { DataContext: ShellViewModel shell } => shell.Documents.ToArray(),
        _ => Array.Empty<DocumentViewModel>(),
    }).ToArray();

    public Window Open(StartupTool tool)
    {
        if (Windows.TryGetValue(tool, out var existing))
        {
            existing.Show();
            if (existing.WindowState == WindowState.Minimized) existing.WindowState = WindowState.Normal;
            existing.Activate();
            return existing;
        }

        var window = tool switch
        {
            StartupTool.Main => (Window)Services.GetRequiredService<MainWindow>(),
            StartupTool.Workshop => new GUI.MainWindow { Title = "Workshop Manager - Hammer 5 Tools" },
            StartupTool.SoundEvents or StartupTool.MapBuilder or StartupTool.SmartProps => new StandaloneToolWindow(tool,
                Dialogs, path => CreateDocument(tool, path),
                OpenSettings, () => Open(StartupTool.Main)),
            _ => throw new ArgumentOutOfRangeException(nameof(tool)),
        };
        Windows[tool] = window;
        if (Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            desktop.MainWindow ??= window;
            window.Closed += (_, _) =>
            {
                Windows.Remove(tool);
                if (desktop.MainWindow == window) desktop.MainWindow = Windows.Values.FirstOrDefault();
            };
        }
        else
        {
            window.Closed += (_, _) => Windows.Remove(tool);
        }

        window.Show();
        return window;
    }

    private DocumentViewModel CreateDocument(StartupTool tool, string? path)
    {
        return tool switch
        {
            StartupTool.SoundEvents => new SoundEventEditorViewModel(null, Services.GetRequiredService<ISoundEventService>(), Dialogs, path, Services.GetRequiredService<ICs2Locator>()),
            StartupTool.SmartProps => new SmartPropEditorViewModel(Services.GetRequiredService<ICs2Locator>(), null, Dialogs, path),
            StartupTool.MapBuilder => new MapBuilderViewModel(null, Services.GetRequiredService<IMapBuilderService>(),
                Services.GetRequiredService<ISettingsService>(), Dialogs, Services.GetRequiredService<ISystemUsageService>(), Services.GetRequiredService<ICs2Locator>()),
            _ => throw new ArgumentOutOfRangeException(nameof(tool)),
        };
    }

    public async Task<bool> SwitchAddonAsync(Addon addon)
    {
        if (ChangingAddon) return false;
        ChangingAddon = true;
        try
        {
            if (Windows.GetValueOrDefault(StartupTool.Main)?.DataContext is ShellViewModel shell)
            {
                return await shell.SwitchAddonAsync(addon);
            }

            return Services.GetRequiredService<IAddonService>().SetActiveAddon(addon.Name);
        }
        finally
        {
            ChangingAddon = false;
        }
    }

    private void OpenSettings()
    {
        if (Windows.GetValueOrDefault(StartupTool.Main)?.DataContext is ShellViewModel shell)
        {
            shell.OpenPreferencesCommand.Execute(null);
            return;
        }

        var settings = Services.GetRequiredService<ISettingsService>();
        var preferences = new PreferencesViewModel(settings, Dialogs);
        var pathChanged = false;
        preferences.BeforeApply = async () =>
        {
            pathChanged = preferences.Cs2Path != (settings.Settings.Cs2PathOverride ?? string.Empty);
            return !pathChanged || await Dialogs.ConfirmContextChangeAsync([]);
        };
        preferences.Applied += (_, _) =>
        {
            if (!pathChanged) return;
            Services.GetRequiredService<ICs2Locator>().FindCs2Path();
            Services.GetRequiredService<IAddonService>().RefreshAddons();
        };
        Dialogs.ShowUtility("Settings", preferences, 830, 600);
    }
}
