namespace Hammer5Tools.App.Services.Updates;

using System.Diagnostics;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Layout;
using Avalonia.Media;
using Avalonia.Threading;

/// <summary>Minimal update UI usable even when application services cannot start.</summary>
public sealed class UpdateWindow : Window, IDisposable
{
    private readonly IUpdateService Updates;
    private readonly Func<Task<bool>> ConfirmRestart;
    private readonly CancellationTokenSource Cancellation = new();
    private readonly TextBlock StatusText = new() { TextWrapping = TextWrapping.Wrap };
    private readonly Button Check = new() { Content = "Check for updates" };
    private readonly Button Download = new() { Content = "Download update", IsEnabled = false };
    private readonly Button Install = new() { Content = "Install and restart", IsEnabled = false };
    private readonly ComboBox Channel;
    private readonly Grid Notes = new() { Margin = new Thickness(10), RowSpacing = 10 };
    private readonly StackPanel Options = new() { Spacing = 12 };
    private readonly ProgressBar Progress = new() { Minimum = 0, Maximum = 100, Height = 18, IsVisible = false };
    private int NotesRequest;
    private bool Busy;
    private bool IsDisposed;

    public UpdateWindow(IUpdateService updates, Func<Task<bool>> confirmRestart, string? startupError = null)
    {
        Updates = updates;
        ConfirmRestart = confirmRestart;
        Title = startupError is null ? "Updater" : "Recovery - Hammer 5 Tools";
        Width = 600;
        Height = 700;
        MinWidth = 520;
        MinHeight = 300;
        Channel = new ComboBox { ItemsSource = new[] { "stable", "dev" }, SelectedItem = updates.Channel };
        Channel.SelectionChanged += (_, _) =>
        {
            Updates.Channel = Channel.SelectedItem as string ?? "stable";
            Download.IsEnabled = false;
            Install.IsEnabled = false;
            _ = LoadNotesAsync();
        };
        StatusText.Text = updates.Status;
        Download.IsEnabled = updates.AvailableVersion is not null && !updates.IsDownloaded;
        Install.IsEnabled = updates.IsDownloaded;
        Check.Click += async (_, _) => await RunAsync(async () =>
        {
            await LoadNotesAsync();
            await Updates.CheckForUpdatesAsync(false, Cancellation.Token);
        });
        Download.Click += async (_, _) => await RunAsync(() => Updates.DownloadUpdateAsync(
            percent => Dispatcher.UIThread.Post(() =>
            {
                if (Busy && !Updates.IsDownloaded)
                {
                    Progress.IsVisible = true;
                    Progress.Value = percent;
                    StatusText.Text = $"Downloading update: {percent}%";
                }
            }), Cancellation.Token));
        Install.Click += async (_, _) => await RunAsync(async () =>
        {
            if (!await ConfirmRestart())
            {
                StatusText.Text = "Restart cancelled. Your update is still ready to install.";
                return;
            }
            Updates.ApplyUpdateAndRestart();
        });
        var releases = new Button { Content = "ReleaseNotes" };
        var update = new Button { Content = updates.IsDownloaded ? "Install and restart" : "Update", Padding = new Thickness(14, 3), IsEnabled = Download.IsEnabled || Install.IsEnabled };
        update.Classes.Add("update-action");
        update.Bind(Button.BackgroundProperty, update.GetResourceObservable("H5TWarningBrush"));
        update.Bind(Button.ForegroundProperty, update.GetResourceObservable("H5TSelectionTextBrush"));
        update.Click += (_, _) => (Updates.IsDownloaded ? Install : Download).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        var ok = new Button { Content = "OK" };
        ok.Click += (_, _) => Close();
        releases.Click += (_, _) =>
        {
            try
            {
                Process.Start(new ProcessStartInfo($"{VelopackUpdateService.RepositoryUrl}/releases") { UseShellExecute = true });
            }
            catch (Exception ex)
            {
                StatusText.Text = $"Could not open releases: {ex.Message}";
            }
        };
        var panel = Options;
        if (startupError is not null)
        {
            panel.Children.Add(new TextBlock
            {
                Text = "Recovery tools are available. You can download the latest fixes here.",
                TextWrapping = TextWrapping.Wrap,
            });
            panel.Children.Add(new TextBox { Text = startupError, IsReadOnly = true, TextWrapping = TextWrapping.Wrap, MaxHeight = 90 });
        }
        panel.Children.Add(new StackPanel
        {
            Orientation = Orientation.Horizontal,
            Spacing = 12,
            Children = { new TextBlock { Text = "Update channel:", VerticalAlignment = VerticalAlignment.Center }, Channel },
        });
        var notesScroll = new ScrollViewer { Content = Notes };
        var notesBorder = new Border { BorderThickness = new Thickness(2), Child = notesScroll };
        notesBorder.Bind(Border.BorderBrushProperty, notesBorder.GetResourceObservable("H5TBorderStrongBrush"));
        notesBorder.Bind(Border.BackgroundProperty, notesBorder.GetResourceObservable("H5TSurfaceBrush"));
        notesScroll.SizeChanged += (_, _) => Notes.MinHeight = Math.Max(0, notesScroll.Bounds.Height - 20);
        StatusText.IsVisible = startupError is not null;
        panel.Children.Add(StatusText);
        panel.Children.Add(Progress);
        panel.Children.Add(new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8, Children = { Check, Download, Install } });
        panel.IsVisible = startupError is not null;
        var options = new Button { Content = "Update options" };
        options.Click += (_, _) => panel.IsVisible = !panel.IsVisible;
        var footer = new Grid { ColumnDefinitions = new ColumnDefinitions("*,Auto"), RowDefinitions = new RowDefinitions("Auto,Auto"), RowSpacing = 6 };
        Grid.SetColumnSpan(panel, 2);
        footer.Children.Add(panel);
        Grid.SetRow(options, 1);
        options.HorizontalAlignment = HorizontalAlignment.Left;
        footer.Children.Add(options);
        var actions = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 6, VerticalAlignment = VerticalAlignment.Bottom, Children = { update, releases, ok } };
        Grid.SetColumn(actions, 1);
        Grid.SetRow(actions, 1);
        footer.Children.Add(actions);
        Download.PropertyChanged += (_, _) => update.IsEnabled = Download.IsEnabled || Install.IsEnabled;
        Install.PropertyChanged += (_, _) =>
        {
            update.IsEnabled = Download.IsEnabled || Install.IsEnabled;
            update.Content = Updates.IsDownloaded ? "Install and restart" : "Update";
        };
        var layout = new Grid { RowDefinitions = new RowDefinitions("Auto,*,Auto"), Margin = new Thickness(11), RowSpacing = 8 };
        var heading = new TextBlock { Text = "Changelog", FontSize = 20, FontWeight = FontWeight.Bold, Margin = new Thickness(7, 2, 0, 0) };
        layout.Children.Add(heading);
        Grid.SetRow(notesBorder, 1);
        layout.Children.Add(notesBorder);
        Grid.SetRow(footer, 2);
        panel.Margin = default;
        layout.Children.Add(footer);
        Content = layout;
        Opened += async (_, _) => await LoadNotesAsync();
        Closed += (_, _) => Dispose();
    }

    private async Task LoadNotesAsync()
    {
        var request = ++NotesRequest;
        Notes.Children.Clear();
        Notes.RowDefinitions.Clear();
        Notes.Children.Add(new TextBlock { Text = "Loading release notes..." });
        try
        {
            var releases = await Updates.LoadReleaseNotesAsync(Cancellation.Token);
            if (IsDisposed || request != NotesRequest) return;
            Notes.Children.Clear();
            Notes.RowDefinitions.Clear();
            for (var index = 0; index < releases.Count; index++)
            {
                var release = releases[index];
                AddNotesRow(new TextBlock { Text = $"Version: {release.Version}", FontSize = 16, FontWeight = FontWeight.Bold, Margin = new Thickness(5, 5, 5, 0), VerticalAlignment = VerticalAlignment.Center }, GridLength.Star);
                AddNotesRow(new ReleaseNotesView(string.IsNullOrWhiteSpace(release.Body) ? "No release notes found." : release.Body, OpenRelease)
                {
                    Margin = new Thickness(5, 0),
                    VerticalAlignment = VerticalAlignment.Center,
                }, GridLength.Star);
                if (index < releases.Count - 1) AddNotesRow(new Separator(), GridLength.Auto);
            }
            if (releases.Count == 0) Notes.Children.Add(new TextBlock { Text = "No release notes found." });
        }
        catch (OperationCanceledException) when (Cancellation.IsCancellationRequested)
        {
        }
        catch (Exception ex)
        {
            if (IsDisposed || request != NotesRequest) return;
            Notes.Children.Clear();
            Notes.RowDefinitions.Clear();
            Notes.Children.Add(new TextBlock { Text = $"Could not load release notes: {ex.Message}. Check again to retry or open GitHub Releases.", TextWrapping = TextWrapping.Wrap });
        }
    }

    private void AddNotesRow(Control control, GridLength height)
    {
        Grid.SetRow(control, Notes.RowDefinitions.Count);
        Notes.RowDefinitions.Add(new RowDefinition(height));
        Notes.Children.Add(control);
    }

    private void OpenRelease(Uri url)
    {
        try
        {
            Process.Start(new ProcessStartInfo(url.AbsoluteUri) { UseShellExecute = true });
        }
        catch (Exception ex)
        {
            Options.IsVisible = StatusText.IsVisible = true;
            StatusText.Text = $"Could not open release: {ex.Message}";
        }
    }

    private async Task RunAsync(Func<Task> action)
    {
        if (Busy) return;
        Busy = true;
        Check.IsEnabled = Download.IsEnabled = Install.IsEnabled = Channel.IsEnabled = false;
        Options.IsVisible = true;
        StatusText.IsVisible = true;
        StatusText.Text = "Working...";
        try
        {
            await action();
            if (StatusText.Text == "Working..." || StatusText.Text?.StartsWith("Downloading update:", StringComparison.Ordinal) == true)
            {
                StatusText.Text = Updates.Status;
            }
        }
        catch (OperationCanceledException)
        {
            StatusText.Text = "Update cancelled. You can try again.";
        }
        catch (Exception ex)
        {
            StatusText.Text = $"Update failed: {ex.Message}. You can retry or download an installer from GitHub Releases.";
        }
        finally
        {
            Progress.IsVisible = false;
            Busy = false;
            Check.IsEnabled = Channel.IsEnabled = true;
            Download.IsEnabled = Updates.AvailableVersion is not null && !Updates.IsDownloaded;
            Install.IsEnabled = Updates.IsDownloaded;
        }
    }

    public void Dispose()
    {
        if (IsDisposed) return;
        IsDisposed = true;
        Cancellation.Cancel();
        Cancellation.Dispose();
        GC.SuppressFinalize(this);
    }
}
