namespace Hammer5Tools.App;

using Avalonia;
using Avalonia.Threading;
using Hammer5Tools.App.Services;
using Hammer5Tools.App.Services.Lifecycle;
using Hammer5Tools.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Velopack;

public static class Program
{
    public static IServiceProvider? Services { get; private set; }

    public static StartupTool Startup { get; private set; }

    public static string? StartupError { get; private set; }

    [STAThread]
    public static void Main(string[] args)
    {
        VelopackApp.Build().Run();

        try
        {
            Startup = StartupArguments.Parse(args);
        }
        catch (ArgumentException ex)
        {
            ShowStartupError(ex.Message, args);
            return;
        }

        using var singleInstance = new SingleInstanceGuard();
        if (!singleInstance.IsFirstInstance)
        {
            try
            {
                singleInstance.ForwardAsync(Startup).GetAwaiter().GetResult();
            }
            catch (Exception ex) when (ex is IOException or OperationCanceledException or UnauthorizedAccessException)
            {
                ShowStartupError("Could not contact the running Hammer 5 Tools application. Close the older copy and try again.", args);
            }

            return;
        }

        var builder = Host.CreateApplicationBuilder();

        builder.Services.AddHammer5ToolsCore();
        builder.Services.AddSingleton<Services.Updates.IUpdateService, Services.Updates.VelopackUpdateService>();
        builder.Services.AddSingleton<DialogService>();
        builder.Services.AddSingleton<IDialogService>(services => services.GetRequiredService<DialogService>());
        builder.Services.AddSingleton<ToolWindowService>();
        builder.Services.AddTransient<Features.Shell.ShellViewModel>();
        builder.Services.AddTransient<MainWindow>();

        using var host = builder.Build();
        Services = host.Services;
        singleInstance.StartListening(tool => Dispatcher.UIThread.Post(() => Services.GetRequiredService<ToolWindowService>().Open(tool)));

        BuildAvaloniaApp()
            .StartWithClassicDesktopLifetime(args);
    }

    private static void ShowStartupError(string message, string[] args)
    {
        StartupError = message;
        Environment.ExitCode = 1;
        BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
    }

    public static AppBuilder BuildAvaloniaApp() =>
        AppBuilder.Configure<App>()
            .UsePlatformDetect()
            .WithInterFont()
            .LogToTrace();
}
