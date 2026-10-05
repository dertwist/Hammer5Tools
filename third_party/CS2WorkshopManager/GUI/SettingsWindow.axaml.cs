using System.IO;
using System.Linq;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Platform.Storage;
using CS2WorkshopManager;

namespace GUI;

/// <summary>
/// What holds for every addon: the theme, and the packing rules that apply to all of them, changed here and saved to the settings file as they change.
/// </summary>
public partial class SettingsWindow : Window
{
    private AppSettings settings = new();

    /// <summary>Whether the accent picker is being set from the settings, which is not a pick to save.</summary>
    private bool showingAccent;

    public SettingsWindow()
    {
        InitializeComponent();

        // the path from the user's profile folder on, which is where it differs between users and systems
        FilePath.Text = $"Settings file: {Path.GetRelativePath(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), AppSettings.FilePath)}";

        try
        {
            settings = AppSettings.Load();
            ShowRules();

            // the choice is shown before its handler is wired to changes, so showing it does not save it
            ThemeBox.SelectedIndex = (int)settings.Theme;
            ShowAccent();

            if (settings.SavedByNewerApp)
            {
                Status.Text = $"Saved by version {settings.SavedBy} of the app, newer than this version {AppSettings.AppVersion}, which can not use what that version added.";
            }
        }
        catch (Exception exception)
        {
            // the settings file is hand editable too, so its parser's own errors are reported like the file system's
            Status.Text = exception.Message;
        }
    }

    private void OnThemeChanged(object? sender, SelectionChangedEventArgs e)
    {
        var theme = (AppTheme)ThemeBox.SelectedIndex;

        if (theme == settings.Theme)
        {
            return;
        }

        settings.Theme = theme;
        App.ApplyTheme(theme);
        ShowAccent();
        SaveSettings();
    }

    /// <summary>Shows the accent in force: the one set, or the theme's own.</summary>
    private void ShowAccent()
    {
        showingAccent = true;
        AccentPicker.Color = settings.Accent != null && Color.TryParse(settings.Accent, out var custom) ? custom : App.ThemeAccent(Application.Current!.ActualThemeVariant);
        AccentReset.IsEnabled = settings.Accent != null;
        showingAccent = false;
    }

    private void OnAccentChanged(object? sender, ColorChangedEventArgs e)
    {
        if (showingAccent)
        {
            return;
        }

        settings.Accent = $"#{e.NewColor.R:X2}{e.NewColor.G:X2}{e.NewColor.B:X2}";
        App.ApplyAccent(settings.Accent);
        AccentReset.IsEnabled = true;
        SaveSettings();
    }

    private void OnAccentReset(object? sender, RoutedEventArgs e)
    {
        settings.Accent = null;
        App.ApplyAccent(null);
        ShowAccent();
        SaveSettings();
    }

    /// <summary>Saves the settings, or says why it could not.</summary>
    private void SaveSettings()
    {
        try
        {
            settings.Save();
            Status.Text = string.Empty;
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            Status.Text = exception.Message;
        }
    }

    /// <summary>Opens the settings file's folder in the system's file browser, making it when nothing has been saved yet.</summary>
    private async void OnOpenFolder(object? sender, RoutedEventArgs e)
    {
        var folder = Path.GetDirectoryName(AppSettings.FilePath)!;

        try
        {
            Directory.CreateDirectory(folder);
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            Status.Text = exception.Message;
            return;
        }

        await Launcher.LaunchDirectoryInfoAsync(new DirectoryInfo(folder));
    }

    private void ShowRules()
    {
        RulesList.ItemsSource = settings.GlobalRules.Rules.Select(rule => new RuleRow(rule)).ToList();
    }

    /// <summary>Applies a change to the rules and saves them, or says why it could not save.</summary>
    private void ChangeRules(Action<AddonRules> change)
    {
        try
        {
            change(settings.GlobalRules);
            settings.Save();
            ShowRules();
            Status.Text = string.Empty;
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            Status.Text = exception.Message;
        }
    }

    private void OnExclude(object? sender, RoutedEventArgs e)
    {
        AddRule(exclude: true);
    }

    private void OnInclude(object? sender, RoutedEventArgs e)
    {
        AddRule(exclude: false);
    }

    /// <summary>Makes the path typed in a rule, first so it wins over the rules before it, in place of any earlier rule for that path.</summary>
    private void AddRule(bool exclude)
    {
        var pattern = AddonRules.Normalize(PatternBox.Text ?? string.Empty);

        if (pattern.Length == 0)
        {
            Status.Text = "Type a path under the addon first, such as materials/dev/.";
            return;
        }

        PatternBox.Text = string.Empty;

        ChangeRules(current =>
        {
            current.Rules.RemoveAll(rule => rule.Pattern.Equals(pattern, StringComparison.OrdinalIgnoreCase));
            current.Rules.Insert(0, new AddonRules.Rule(exclude, pattern));
        });
    }

    private void OnRemoveRule(object? sender, RoutedEventArgs e)
    {
        if ((sender as Button)?.DataContext is RuleRow row)
        {
            ChangeRules(current => current.Rules.Remove(row.Rule));
        }
    }
}
