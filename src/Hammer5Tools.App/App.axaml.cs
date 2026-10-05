namespace Hammer5Tools.App;

using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
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
            desktop.MainWindow = services?.GetService<MainWindow>() ?? new MainWindow();
        }

        base.OnFrameworkInitializationCompleted();
    }
}
