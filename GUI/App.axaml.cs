namespace Hammer5Tools.App;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using Hammer5Tools.App.Services;
using Microsoft.Extensions.DependencyInjection;

public partial class App : Application
{
    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
        Hammer5Tools.App.Styles.ThemeService.Apply("Standard");
    }

    public override void OnFrameworkInitializationCompleted()
    {
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            var services = Program.Services;
            Hammer5Tools.App.Styles.ThemeService.Apply(services?.GetService<Core.Settings.ISettingsService>()?.Settings.Theme ?? "Dark");
            desktop.ShutdownMode = ShutdownMode.OnLastWindowClose;
            if (Program.StartupError is { } error)
            {
                desktop.MainWindow = new Window
                {
                    Title = "Hammer 5 Tools",
                    Width = 520,
                    Height = 180,
                    Content = new TextBlock { Text = error, TextWrapping = Avalonia.Media.TextWrapping.Wrap, Margin = new Thickness(16) },
                };
            }
            else if (services?.GetService<ToolWindowService>() is { } tools)
            {
                tools.Open(Program.Startup);
            }
            else
            {
                desktop.MainWindow = new MainWindow();
            }
        }

        base.OnFrameworkInitializationCompleted();
    }
}
