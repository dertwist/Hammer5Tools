using Avalonia.Controls.ApplicationLifetimes;

namespace Hammer5Tools.SmartProp.Tests;

public sealed class App : Hammer5Tools.App.App
{
    public override void OnFrameworkInitializationCompleted()
    {
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            desktop.MainWindow = new MainWindow();
        }
    }
}
