using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Controls;
using Avalonia.Markup.Xaml;
using Avalonia.Markup.Xaml.Styling;
using Avalonia.Media;
using Avalonia.Styling;
using CS2WorkshopManager;

namespace GUI;

public partial class App : Application
{
    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            try
            {
                var settings = AppSettings.Load();

                ApplyTheme(settings.Theme);
                ApplyAccent(settings.Accent);
            }
            catch (Exception)
            {
                // a settings file that can not be read leaves the system theme, and is reported in the settings window
                ApplyTheme(AppTheme.System);
            }

            desktop.MainWindow = new MainWindow();
            desktop.Exit += (_, _) => WorkshopManager.ShutdownSteam();
        }

        base.OnFrameworkInitializationCompleted();
    }

    /// <summary>
    /// Sets the accent colour every window's colouring is derived from, over the theme's own, or with null takes it away for the theme's.
    /// </summary>
    public static void ApplyAccent(string? accent)
    {
        if (accent != null && Color.TryParse(accent, out var color))
        {
            Current!.Resources["AccentColor"] = color;
        }
        else
        {
            Current!.Resources.Remove("AccentColor");
        }
    }

    /// <summary>The accent the theme itself has for <paramref name="variant"/>, whatever accent is set over it.</summary>
    public static Color ThemeAccent(ThemeVariant variant)
    {
        foreach (var provider in Current!.Resources.MergedDictionaries)
        {
            if ((provider is ResourceInclude include ? include.Loaded : provider) is IResourceDictionary dictionary && dictionary.TryGetResource("AccentColor", variant, out var found) && found is Color color)
            {
                return color;
            }
        }

        return Colors.Gray;
    }

    /// <summary>Gives every window the theme set, or the system's.</summary>
    public static void ApplyTheme(AppTheme theme)
    {
        Current!.RequestedThemeVariant = theme switch
        {
            AppTheme.Light => ThemeVariant.Light,
            AppTheme.Dark => ThemeVariant.Dark,
            _ => ThemeVariant.Default,
        };
    }
}
