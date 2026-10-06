namespace Hammer5Tools.App.Services;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Layout;
using Avalonia.Platform.Storage;
using Hammer5Tools.App.ViewModels;

public interface IDialogService
{
    IReadOnlyList<DocumentViewModel> UtilityDocuments => [];

    void ShowUtility(string title, object viewModel, double width = 960, double height = 650);

    void ShowDockableUtility(string title, DocumentViewModel document, Action<DocumentViewModel> dock,
        double width = 960, double height = 650) => ShowUtility(title, document, width, height);

    Task<bool> ConfirmCloseAsync(IReadOnlyList<DocumentViewModel> documents);

    Task<bool> ConfirmContextChangeAsync(IReadOnlyList<DocumentViewModel> documents) => ConfirmCloseAsync(documents);

    Task<string?> OpenFileAsync(string title, string pattern);

    Task<string?> SaveFileAsync(string title, string filename);

    Task<string?> PickFolderAsync(string title);

    Task ShowErrorAsync(string message);

    void CloseUtilities();

    void ShowWorkshopManager();

    Task<string?> PromptAsync(string title, string label) => Task.FromResult<string?>(null);

    Task<bool> ConfirmAsync(string title, string message) => Task.FromResult(false);

    async Task<AddonCreationRequest?> ConfigureAddonAsync(string? selectedPreset)
    {
        var name = await PromptAsync("Create addon", "Addon name");
        return string.IsNullOrWhiteSpace(name) ? null : new(name, null, null);
    }

    async Task<bool> ExportAddonAsync(Core.Addons.Addon addon, string? archiveDirectory = null)
    {
        var destination = await SaveFileAsync("Export addon", $"{addon.Name}.zip");
        if (destination is null) return false;
        await Task.Run(() => Core.Addons.AddonArchive.Export(addon, destination));
        return true;
    }
}

public partial class DialogService : IDialogService, IDisposable
{
    private readonly Dictionary<Type, Window> OpenWindows = [];
    private bool CheckingContext;
    private bool IsDisposed;

    public IReadOnlyList<DocumentViewModel> UtilityDocuments => OpenWindows.Values.OfType<ToolDialogWindow>()
        .Select(window => window.Document).ToArray();

    public Func<IReadOnlyList<DocumentViewModel>>? ContextDocuments { get; set; }

    public Action? OpenWorkshop { get; set; }

    public Func<Window?>? OwnerWindow { get; set; }

    public void ShowWorkshopManager()
    {
        if (OpenWorkshop is not null)
        {
            OpenWorkshop();
            return;
        }

        var window = MainWindow;
        if (window.DataContext is not Features.Shell.ShellViewModel shell)
        {
            throw new InvalidOperationException("The Workshop Manager requires the main editor window.");
        }

        shell.OpenWorkshopManagerCommand.Execute(null);
        window.Activate();
    }

    public void Dispose()
    {
        if (IsDisposed) return;
        IsDisposed = true;
        CloseUtilities();
        CS2WorkshopManager.WorkshopManager.ShutdownSteam();
        GC.SuppressFinalize(this);
    }

    public async Task<string?> PromptAsync(string title, string label)
    {
        var window = CreateDialog(title, 440, 180);
        var input = new TextBox();
        var accept = new Button { Content = "Create", HorizontalAlignment = HorizontalAlignment.Right };
        accept.Click += (_, _) => window.Close(input.Text);
        window.Content = new StackPanel
        {
            Margin = new Thickness(12),
            Spacing = 12,
            Children = { new TextBlock { Text = label }, input, accept },
        };
        return await window.ShowDialog<string?>(MainWindow);
    }

    public async Task<bool> ConfirmAsync(string title, string message)
    {
        var window = CreateDialog(title, 520, 220);
        var accept = new Button { Content = "Remove", HorizontalAlignment = HorizontalAlignment.Right };
        accept.Click += (_, _) => window.Close(true);
        var cancel = new Button { Content = "Cancel" };
        cancel.Click += (_, _) => window.Close(false);
        window.Content = new StackPanel
        {
            Margin = new Thickness(12),
            Spacing = 12,
            Children = { new TextBlock { Text = message, TextWrapping = Avalonia.Media.TextWrapping.Wrap }, cancel, accept },
        };
        return await window.ShowDialog<bool>(MainWindow);
    }

    private Window MainWindow
    {
        get
        {
            var desktop = Application.Current?.ApplicationLifetime as IClassicDesktopStyleApplicationLifetime;
            return desktop?.Windows.FirstOrDefault(window => window.IsActive)
                ?? desktop?.Windows.FirstOrDefault(window => window.IsVisible)
                ?? desktop?.MainWindow
                ?? OwnerWindow?.Invoke()
                ?? throw new InvalidOperationException("The application window is not available.");
        }
    }

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

    public void ShowDockableUtility(string title, DocumentViewModel document, Action<DocumentViewModel> dock,
        double width = 960, double height = 650)
    {
        var type = document.GetType();
        if (OpenWindows.TryGetValue(type, out var existing))
        {
            document.Dispose();
            existing.Activate();
            return;
        }
        var window = new ToolDialogWindow(title, document, this, dock, width, height);
        window.Closed += (_, _) =>
        {
            OpenWindows.Remove(type);
            if (!window.IsDocked) document.Dispose();
        };
        OpenWindows[type] = window;
        window.Show(MainWindow);
    }

    public void CloseUtilities()
    {
        foreach (var window in OpenWindows.Values.ToArray())
        {
            if (window is ToolDialogWindow tool) tool.CloseAfterConfirmation();
            else window.Close();
        }
    }

    public Task<bool> ConfirmCloseAsync(IReadOnlyList<DocumentViewModel> documents) => ConfirmCloseAsync(documents, null);

    public async Task<bool> ConfirmCloseAsync(IReadOnlyList<DocumentViewModel> documents, Window? owner)
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
        return await window.ShowDialog<bool>(owner ?? MainWindow);
    }

    public async Task<bool> ConfirmContextChangeAsync(IReadOnlyList<DocumentViewModel> documents)
    {
        if (CheckingContext) return false;
        CheckingContext = true;
        try
        {
            return await ConfirmCloseAsync(documents.Concat(ContextDocuments?.Invoke() ?? []).Concat(UtilityDocuments).Distinct().ToArray());
        }
        finally
        {
            CheckingContext = false;
        }
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
        var provider = MainWindow.StorageProvider;
        var directory = Path.GetDirectoryName(filename);
        var file = await MainWindow.StorageProvider.SaveFilePickerAsync(new FilePickerSaveOptions
        {
            Title = title,
            SuggestedFileName = Path.GetFileName(filename),
            SuggestedStartLocation = Path.IsPathFullyQualified(filename) && Directory.Exists(directory)
                ? await provider.TryGetFolderFromPathAsync(directory) : null,
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
