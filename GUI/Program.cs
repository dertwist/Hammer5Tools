namespace Hammer5Tools.App;

using Avalonia;
using Avalonia.Threading;
using Hammer5Tools.App.Services;
using Hammer5Tools.App.Services.Lifecycle;
using Hammer5Tools.App.Services.Updates;
using Hammer5Tools.Core;
using Hammer5Tools.Core.IO.Commands;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Velopack;

public static class Program
{
    public static IServiceProvider? Services { get; private set; }

    public static StartupTool Startup { get; private set; }

    public static string? StartupError { get; private set; }

    private static ToolWindowService? Tools;
    private static UpdateWindow? UpdatesWindow;
    private static bool OwnsInstance;

    [STAThread]
    public static void Main(string[] args)
    {
        try
        {
            VelopackApp.Build().Run();
            if (args.Length == 1 && args[0] == CommandPipeHost.StartupArgument)
            {
                try
                {
                    CommandPipeHost.Run();
                }
                catch (IOException)
                {
                    Environment.ExitCode = 1;
                }
                return;
            }
            Startup = StartupArguments.Parse(args);
        }
        catch (Exception ex)
        {
            ShowStartupError(ex.Message, args);
            return;
        }

        using var singleInstance = new SingleInstanceGuard();
        OwnsInstance = singleInstance.IsFirstInstance;
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

        IHost? host = null;
        try
        {
            host = CreateHost();
            Services = host.Services;
        }
        catch (Exception ex)
        {
            StartupError = ex.Message;
        }

        using (host)
        {
            singleInstance.StartListening(tool => Dispatcher.UIThread.Post(() => OpenTool(tool)));
            BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
        }
    }

    private static IHost CreateHost()
    {
        var builder = Host.CreateApplicationBuilder();

        builder.Services.AddHammer5ToolsCore();
        builder.Services.AddSingleton<Services.Updates.IUpdateService, Services.Updates.VelopackUpdateService>();
        builder.Services.AddSingleton<DialogService>();
        builder.Services.AddSingleton<IDialogService>(services => services.GetRequiredService<DialogService>());
        builder.Services.AddSingleton<ToolWindowService>();
        builder.Services.AddTransient<Features.Shell.ShellViewModel>();
        builder.Services.AddTransient<MainWindow>();

        return builder.Build();
    }

    public static void OpenTool(StartupTool tool)
    {
        if (StartupError is not null || Services is null)
        {
            OpenUpdates(StartupError ?? "Application services could not start. Check for an update or download a fresh installer.");
            return;
        }
        OpenToolOrRecovery(() =>
        {
            Tools ??= Services.GetRequiredService<ToolWindowService>();
            return Tools.Open(tool);
        });
    }

    internal static Avalonia.Controls.Window OpenToolOrRecovery(Func<Avalonia.Controls.Window> openTool)
    {
        try
        {
            return openTool();
        }
        catch (Exception ex)
        {
            return OpenUpdates(ex.Message);
        }
    }

    public static UpdateWindow OpenUpdates(string? error = null)
    {
        if (UpdatesWindow is { } existing)
        {
            existing.Show();
            existing.Activate();
            return existing;
        }

        IUpdateService updates;
        try
        {
            updates = Services?.GetService<IUpdateService>() ?? new VelopackUpdateService();
            if (Services?.GetService<Core.Settings.ISettingsService>() is { } settings)
            {
                updates.Channel = settings.Settings.UpdateChannel;
            }
        }
        catch
        {
            updates = new VelopackUpdateService();
        }
        var window = new UpdateWindow(updates, ConfirmUpdateRestartAsync, error);
        UpdatesWindow = window;
        window.Closed += (_, _) => UpdatesWindow = null;
        if (Application.Current?.ApplicationLifetime is Avalonia.Controls.ApplicationLifetimes.IClassicDesktopStyleApplicationLifetime desktop)
        {
            desktop.MainWindow ??= window;
            window.Closed += (_, _) =>
            {
                if (desktop.MainWindow == window) desktop.MainWindow = desktop.Windows.FirstOrDefault(other => other != window);
            };
        }
        window.Show();
        return window;
    }

    private static Task<bool> ConfirmUpdateRestartAsync()
    {
        if (Tools is not null) return Tools.ConfirmUpdateRestartAsync();
        if (OwnsInstance) return Task.FromResult(true);

        // A failed launch forward must not restart another instance with unsaved documents.
        using var guard = new SingleInstanceGuard();
        return Task.FromResult(guard.IsFirstInstance);
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
            .With(new Win32PlatformOptions
            {
                RenderingMode = [Win32RenderingMode.Wgl, Win32RenderingMode.AngleEgl, Win32RenderingMode.Software],
                WglProfiles = [new Avalonia.OpenGL.GlVersion(Avalonia.OpenGL.GlProfileType.OpenGL, 4, 6),
                    new Avalonia.OpenGL.GlVersion(Avalonia.OpenGL.GlProfileType.OpenGL, 3, 2)],
            })
            .WithInterFont()
            .LogToTrace();
}
