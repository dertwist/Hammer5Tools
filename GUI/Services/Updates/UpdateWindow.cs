namespace Hammer5Tools.App.Services.Updates;

using System.Diagnostics;
using Avalonia;
using Avalonia.Controls;
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
    private bool Busy;
    private bool IsDisposed;

    public UpdateWindow(IUpdateService updates, Func<Task<bool>> confirmRestart, string? startupError = null)
    {
        Updates = updates;
        ConfirmRestart = confirmRestart;
        Title = startupError is null ? "Updates - Hammer 5 Tools" : "Recovery - Hammer 5 Tools";
        Width = 640;
        Height = 360;
        MinWidth = 520;
        MinHeight = 300;
        Channel = new ComboBox { ItemsSource = new[] { "stable", "dev" }, SelectedItem = updates.Channel };
        Channel.SelectionChanged += (_, _) =>
        {
            Updates.Channel = Channel.SelectedItem as string ?? "stable";
            Download.IsEnabled = false;
            Install.IsEnabled = false;
        };
        StatusText.Text = updates.Status;
        Download.IsEnabled = updates.AvailableVersion is not null && !updates.IsDownloaded;
        Install.IsEnabled = updates.IsDownloaded;
        Check.Click += async (_, _) => await RunAsync(async () =>
        {
            await Updates.CheckForUpdatesAsync(false, Cancellation.Token);
        });
        Download.Click += async (_, _) => await RunAsync(() => Updates.DownloadUpdateAsync(
            percent => Dispatcher.UIThread.Post(() =>
            {
                if (Busy && !Updates.IsDownloaded) StatusText.Text = $"Downloading update: {percent}%";
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
        var releases = new Button { Content = "Open GitHub Releases" };
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
        var panel = new StackPanel { Margin = new Thickness(16), Spacing = 12 };
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
        panel.Children.Add(StatusText);
        panel.Children.Add(new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8, Children = { Check, Download, Install } });
        panel.Children.Add(releases);
        Content = new ScrollViewer { Content = panel };
        Closed += (_, _) => Dispose();
    }

    private async Task RunAsync(Func<Task> action)
    {
        if (Busy) return;
        Busy = true;
        Check.IsEnabled = Download.IsEnabled = Install.IsEnabled = Channel.IsEnabled = false;
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
