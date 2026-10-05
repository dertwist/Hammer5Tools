namespace Hammer5Tools.App;

using Avalonia;
using Hammer5Tools.Core;
using Hammer5Tools.Infrastructure;
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
        builder.Services.AddInfrastructure();
        builder.Services.AddSingleton<MainWindow>();

        var host = builder.Build();
        Services = host.Services;

        BuildAvaloniaApp()
            .StartWithClassicDesktopLifetime(args);
    }

    public static AppBuilder BuildAvaloniaApp() =>
        AppBuilder.Configure<App>()
            .UsePlatformDetect()
            .WithInterFont()
            .LogToTrace();
}
