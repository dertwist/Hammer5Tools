namespace Hammer5Tools.App;

using Avalonia;
using Hammer5Tools.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

public static class Program
{
    public static IServiceProvider? Services { get; private set; }

    [STAThread]
    public static void Main(string[] args)
    {
        var builder = Host.CreateApplicationBuilder(args);

        builder.Services.AddHammer5ToolsCore();
        builder.Services.AddSingleton<Services.Lifecycle.SingleInstanceGuard>();
        builder.Services.AddSingleton<Services.Updates.IUpdateService, Services.Updates.VelopackUpdateService>();
        builder.Services.AddSingleton<Services.IDialogService, Services.DialogService>();
        builder.Services.AddSingleton<Features.Shell.ShellViewModel>();
        builder.Services.AddSingleton<MainWindow>();

        using var host = builder.Build();
        Services = host.Services;
        var singleInstance = Services.GetRequiredService<Services.Lifecycle.SingleInstanceGuard>();
        if (!singleInstance.IsFirstInstance)
        {
            return;
        }

        BuildAvaloniaApp()
            .StartWithClassicDesktopLifetime(args);
    }

    public static AppBuilder BuildAvaloniaApp() =>
        AppBuilder.Configure<App>()
            .UsePlatformDetect()
            .WithInterFont()
            .LogToTrace();
}
