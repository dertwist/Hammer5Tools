namespace Hammer5Tools.App;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using Avalonia.Themes.Fluent;
using Microsoft.Extensions.DependencyInjection;

public partial class App : Application
{
    private string? InitializationError;

    public override void Initialize()
    {
        try
        {
            AvaloniaXamlLoader.Load(this);
            Hammer5Tools.App.Styles.ThemeService.Apply("Standard");
        }
        catch (Exception ex)
        {
            InitializationError = ex.Message;
            DataTemplates.Clear();
            Resources.Clear();
            Styles.Clear();
            Styles.Add(new FluentTheme());
        }
    }

    public override void OnFrameworkInitializationCompleted()
    {
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            var services = Program.Services;
            desktop.ShutdownMode = ShutdownMode.OnLastWindowClose;
            if (InitializationError is { } error)
            {
                desktop.MainWindow = Program.OpenUpdates(error);
            }
            else
            {
                try
                {
                    Hammer5Tools.App.Styles.ThemeService.Apply(services?.GetService<Core.Settings.ISettingsService>()?.Settings.Theme ?? "Standard");
                    Program.OpenTool(Program.Startup);
                }
                catch (Exception ex)
                {
                    desktop.MainWindow = Program.OpenUpdates(ex.Message);
                }
            }
        }

        base.OnFrameworkInitializationCompleted();
    }
}
