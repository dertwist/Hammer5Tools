namespace Hammer5Tools.App.Services;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Layout;
using Avalonia.Platform.Storage;
using Hammer5Tools.App.ViewModels;

public interface IDialogService
{
    void ShowUtility(string title, object viewModel, double width = 960, double height = 650);

    Task<bool> ConfirmCloseAsync(IReadOnlyList<DocumentViewModel> documents);

    Task<string?> OpenFileAsync(string title, string pattern);

    Task<string?> SaveFileAsync(string title, string filename);

    Task<string?> PickFolderAsync(string title);

    Task ShowErrorAsync(string message);

    void CloseUtilities();

    void ShowWorkshopManager();
}

public class DialogService : IDialogService, IDisposable
{
    private readonly Dictionary<Type, Window> OpenWindows = [];
    private System.Diagnostics.Process? WorkshopManagerProcess;

    public void ShowWorkshopManager()
    {
        if (WorkshopManagerProcess is { HasExited: false })
        {
            return;
        }

        WorkshopManagerProcess?.Dispose();
        var start = WorkshopManagerLaunch.CreateStartInfo(AppContext.BaseDirectory);
        WorkshopManagerProcess = System.Diagnostics.Process.Start(start)
            ?? throw new InvalidOperationException("Workshop Manager could not be started.");
    }

    public void Dispose()
    {
        WorkshopManagerProcess?.Dispose();
        GC.SuppressFinalize(this);
    }

    private static Window MainWindow =>
        (Application.Current?.ApplicationLifetime as IClassicDesktopStyleApplicationLifetime)?.MainWindow
        ?? throw new InvalidOperationException("The application window is not available.");

    public void ShowUtility(string title, object viewModel, double width = 960, double height = 650)
    {
        ArgumentNullException.ThrowIfNull(viewModel);
        var type = viewModel.GetType();
        if (OpenWindows.TryGetValue(type, out var existingWindow))
        {
            if (viewModel is IDisposable disposable)
            {
                disposable.Dispose();
            }

            existingWindow.Activate();
            return;
        }

        var window = new Window
        {
            Title = $"{title} - Hammer 5 Tools",
            Width = width,
            Height = height,
            MinWidth = 450,
            MinHeight = 300,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            DataContext = viewModel,
            Content = new ContentControl { Content = viewModel },
        };
        window.Closed += (_, _) =>
        {
            OpenWindows.Remove(type);
            (viewModel as IDisposable)?.Dispose();
        };
        OpenWindows[type] = window;
        window.Show(MainWindow);
    }

    public void CloseUtilities()
    {
        foreach (var window in OpenWindows.Values.ToArray())
        {
            window.Close();
        }
    }

    public async Task<bool> ConfirmCloseAsync(IReadOnlyList<DocumentViewModel> documents)
    {
        var dirty = documents.Where(document => document.IsDirty).ToArray();
        if (dirty.Length == 0)
        {
            return true;
        }

        var window = CreateDialog("Unsaved files", 550, 320);
        var panel = new StackPanel { Margin = new Thickness(12), Spacing = 10 };
        panel.Children.Add(new TextBlock { Text = "Save changes before continuing?" });
        panel.Children.Add(new ListBox { ItemsSource = dirty.Select(document => document.DisplayTitle).ToArray(), Height = 160 });
        var buttons = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Spacing = 8 };
        var save = new Button { Content = "Save All" };
        save.Click += async (_, _) =>
        {
            save.IsEnabled = false;
            try
            {
                foreach (var document in dirty)
                {
                    if (!await document.SaveAsync())
                    {
                        return;
                    }
                }

                window.Close(true);
            }
            catch (Exception ex)
            {
                await ShowErrorAsync(ex.Message);
            }
            finally
            {
                save.IsEnabled = true;
            }
        };
        var discard = new Button { Content = "Discard" };
        discard.Click += (_, _) => window.Close(true);
        var cancel = new Button { Content = "Cancel" };
        cancel.Click += (_, _) => window.Close(false);
        buttons.Children.Add(save);
        buttons.Children.Add(discard);
        buttons.Children.Add(cancel);
        panel.Children.Add(buttons);
        window.Content = panel;
        return await window.ShowDialog<bool>(MainWindow);
    }

    public async Task<string?> OpenFileAsync(string title, string pattern)
    {
        var files = await MainWindow.StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = title,
            AllowMultiple = false,
            FileTypeFilter = [new FilePickerFileType(title) { Patterns = [pattern] }],
        });
        return files.Count > 0 ? files[0].TryGetLocalPath() : null;
    }

    public async Task<string?> SaveFileAsync(string title, string filename)
    {
        var file = await MainWindow.StorageProvider.SaveFilePickerAsync(new FilePickerSaveOptions
        {
            Title = title,
            SuggestedFileName = filename,
            ShowOverwritePrompt = true,
        });
        return file?.TryGetLocalPath();
    }

    public async Task<string?> PickFolderAsync(string title)
    {
        var folders = await MainWindow.StorageProvider.OpenFolderPickerAsync(new FolderPickerOpenOptions { Title = title });
        return folders.Count > 0 ? folders[0].TryGetLocalPath() : null;
    }

    public async Task ShowErrorAsync(string message)
    {
        var window = CreateDialog("Hammer 5 Tools", 520, 200);
        var panel = new StackPanel { Margin = new Thickness(12), Spacing = 12 };
        panel.Children.Add(new TextBlock { Text = message, TextWrapping = Avalonia.Media.TextWrapping.Wrap });
        var close = new Button { Content = "Close", HorizontalAlignment = HorizontalAlignment.Right };
        close.Click += (_, _) => window.Close();
        panel.Children.Add(close);
        window.Content = panel;
        await window.ShowDialog(MainWindow);
    }

    private static Window CreateDialog(string title, double width, double height)
    {
        return new Window { Title = title, Width = width, Height = height, CanResize = false, WindowStartupLocation = WindowStartupLocation.CenterOwner };
    }
}
