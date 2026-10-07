namespace Hammer5Tools.App.Styles;

using Avalonia;
using Avalonia.Media;
using Avalonia.Styling;

/// <summary>
/// Applies explicit baseline palettes to the application's shared semantic resources.
/// </summary>
public static class ThemeService
{
    private static string CurrentTheme = "Standard";
    private static bool SystemThemeSubscribed;

    public static void Apply(string theme)
    {
        var app = Application.Current;
        if (app is null)
        {
            return;
        }

        CurrentTheme = theme;
        if (!SystemThemeSubscribed && app.PlatformSettings is { } platform)
        {
            platform.ColorValuesChanged += (_, _) =>
            {
                if (CurrentTheme == "System")
                {
                    Avalonia.Threading.Dispatcher.UIThread.Post(() => Apply("System"));
                }
            };
            SystemThemeSubscribed = true;
        }

        var light = theme is "Bright" or "Light" || theme == "System" && app.PlatformSettings?.GetColorValues().ThemeVariant == Avalonia.Platform.PlatformThemeVariant.Light;
        app.RequestedThemeVariant = theme == "System" ? ThemeVariant.Default : light ? ThemeVariant.Light : ThemeVariant.Dark;
        var vintage = theme == "Vintage Steam";
        // Values copied from the Python theme.py semantic tokens and explicit palettes.
        var colors = new Dictionary<string, string>
        {
            ["SoundPropertyFloat"] = light ? "#206255" : vintage ? "#84c7b7" : "#73d1bf",
            ["SoundPropertyBool"] = light ? "#a82a2b" : vintage ? "#c0625f" : "#d1494a",
            ["SoundPropertyComment"] = light ? "#415e34" : vintage ? "#71965f" : "#6a9955",
            ["SoundPropertyVector"] = light ? "#2c6416" : vintage ? "#88cb6d" : "#7dda58",
            ["SoundPropertyList"] = light ? "#774b08" : vintage ? "#e5c187" : "#f6c273",
            ["SoundPropertyCombo"] = light ? "#96109a" : vintage ? "#ebb5eb" : "#f4a9f6",
            ["SoundPropertyBase"] = light ? "#54528e" : vintage ? "#8f90b1" : "#8684b8",
            ["SoundPropertyCustom"] = light ? "#6b5417" : vintage ? "#c7ae62" : "#d9b34c",
            ["PropertyFloat"] = light ? "#00634e" : vintage ? "#c0f5e9" : "#b5ffef",
            ["PropertyBool"] = light ? "#b30003" : vintage ? "#f6c7c7" : "#ffbdbe",
            ["PropertyString"] = light ? "#854900" : vintage ? "#f1d1a8" : "#ffd199",
            ["PropertySection"] = light ? "#4c692f" : vintage ? "#b5caa0" : "#b3d096",
            ["CpuChart"] = light ? "#c84040" : vintage ? "#e97573" : "#ff5a5a",
            ["MemoryChart"] = light ? "#a87d00" : vintage ? "#ddc327" : "#ffd700",
            ["GpuChart"] = light ? "#167a88" : vintage ? "#49aeb4" : "#32b8c6",
            ["Background"] = light ? "#d1d1d1" : vintage ? "#58624c" : "#2e2e2e",
            ["Surface"] = light ? "#d8d8d8" : vintage ? "#525c47" : "#272727",
            ["SurfaceRaised"] = light ? "#ceced0" : vintage ? "#59644d" : "#2f2f31",
            ["SurfaceInput"] = light ? "#c8c8c9" : vintage ? "#4b5442" : "#363637",
            ["Text"] = light ? "#1a1a1a" : vintage ? "#e6e8e4" : "#e5e5e5",
            ["TextMuted"] = light ? "#5a5a5a" : vintage ? "#b4bdab" : "#a5a5a5",
            ["TextDisabled"] = light ? "#868686" : vintage ? "#92a181" : "#797979",
            ["Border"] = light ? "#b6b6b9" : vintage ? "#6c7a5b" : "#464649",
            ["BorderStrong"] = light ? "#a1a1a1" : vintage ? "#7e9069" : "#5e5e5e",
            ["Accent"] = light ? "#366fb5" : vintage ? "#c3c87b" : "#4a83c9",
            ["AccentHover"] = light ? "#8998a7" : vintage ? "#859770" : "#586776",
            ["AccentPressed"] = light ? "#7d8892" : vintage ? "#91a080" : "#6d7882",
            ["Selection"] = light ? "#9aa2ae" : vintage ? "#66754f" : "#515965",
            ["SelectionText"] = light ? "#000000" : vintage ? "#ffffff" : "#ffffff",
            ["Error"] = light ? "#d1494a" : vintage ? "#c0625f" : "#d1494a",
            ["Warning"] = light ? "#e5a00d" : vintage ? "#cd9c2a" : "#e5a00d",
            ["Success"] = light ? "#4aa54e" : vintage ? "#6bad6c" : "#5ab55e",
            ["ConsoleBg"] = light ? "#1e1e1e" : vintage ? "#4b5342" : "#1e1e1e",
            ["BorderSubtle"] = light ? "#bdbdc0" : vintage ? "#667357" : "#3f3f42",
            ["SuccessDark"] = light ? "#82d186" : vintage ? "#458b47" : "#2e7d32",
            ["ErrorDark"] = light ? "#d73939" : vintage ? "#b6423e" : "#c62828",
            ["DisabledBackground"] = light ? "#d6d6d6" : vintage ? "#545d49" : "#292929",
            ["ButtonDisabledText"] = light ? "#7a7a83" : vintage ? "#98a689" : "#7c7c85",
            ["RowHover"] = light ? "#c5c5c7" : vintage ? "#606c53" : "#38383a",
            ["PrimaryBorder"] = light ? "#356fb0" : vintage ? "#356fb0" : "#356fb0",
            ["SuccessBorder"] = light ? "#a1e4a6" : vintage ? "#317335" : "#1b5e20",
            ["SuccessHover"] = light ? "#388e3c" : vintage ? "#388e3c" : "#388e3c",
            ["DangerBorder"] = light ? "#b71c1c" : vintage ? "#b71c1c" : "#b71c1c",
            ["DangerHover"] = light ? "#d32f2f" : vintage ? "#d32f2f" : "#d32f2f",
        };
        foreach (var (key, color) in colors)
        {
            app.Resources[$"H5T{key}Brush"] = new SolidColorBrush(Color.Parse(color));
        }

        foreach (var (dockKey, token) in new Dictionary<string, string>
        {
            ["DockSurfaceWorkbenchBrush"] = "Background",
            ["DockSurfaceEditorBrush"] = "Background",
            ["DockSurfacePanelBrush"] = "Background",
            ["DockSurfaceHeaderBrush"] = "Background",
            ["DockSurfaceHeaderActiveBrush"] = "Background",
            ["DockTabForegroundBrush"] = "Text",
            ["DockTabActiveForegroundBrush"] = "Text",
            ["DockChromeButtonForegroundBrush"] = "Text",
            ["DockToolChromeIconBrush"] = "Text",
            ["DockChromeButtonHoverBackgroundBrush"] = "Selection",
            ["DockChromeButtonPressedBackgroundBrush"] = "Background",
            ["DockChromeButtonDangerHoverBrush"] = "Selection",
        })
        {
            app.Resources[dockKey] = app.Resources[$"H5T{token}Brush"];
        }
    }
}
