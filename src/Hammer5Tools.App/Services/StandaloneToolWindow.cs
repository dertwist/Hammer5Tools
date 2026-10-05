namespace Hammer5Tools.App.Services;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Data;
using Avalonia.Layout;
using Avalonia.Threading;
using Hammer5Tools.App.Services.Lifecycle;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;

public sealed class StandaloneToolWindow : Window
{
    private readonly IAddonService AddonService;
    private readonly DialogService DialogService;
    private readonly Func<DocumentViewModel> CreateDocument;
    private readonly Func<Addon, Task<bool>> SwitchAddon;
    private readonly ComboBox AddonSelector;
    private bool UpdatingSelection;
    private bool CheckingClose;
    private bool CloseConfirmed;
    private bool IsDisposed;

    public DocumentViewModel Document { get; private set; } = null!;

    public StandaloneToolWindow(StartupTool tool, IAddonService addons, DialogService dialogs,
        Func<DocumentViewModel> createDocument, Func<Addon, Task<bool>> switchAddon,
        Action openSettings, Action openMain)
    {
        AddonService = addons;
        DialogService = dialogs;
        CreateDocument = createDocument;
        SwitchAddon = switchAddon;
        Width = tool == StartupTool.MapBuilder ? 1282 : 1200;
        Height = tool == StartupTool.MapBuilder ? 933 : 800;
        MinWidth = 800;
        MinHeight = 500;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;

        AddonSelector = new ComboBox { Name = "AddonSelector", Width = 240, DisplayMemberBinding = new Binding("Name") };
        AddonSelector.SelectionChanged += OnSelectionChanged;
        var toolbar = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8, Margin = new Thickness(8) };
        toolbar.Children.Add(new TextBlock { Text = "Addon", VerticalAlignment = VerticalAlignment.Center });
        toolbar.Children.Add(AddonSelector);
        var settings = new Button { Content = "Settings" };
        settings.Click += (_, _) => openSettings();
        toolbar.Children.Add(settings);
        var main = new Button { Content = "Hammer 5 Tools" };
        main.Click += (_, _) => openMain();
        toolbar.Children.Add(main);
        if (tool == StartupTool.SoundEvents)
        {
            foreach (var command in new[] { "Save", "Undo", "Redo" })
            {
                var button = new Button { Content = command };
                button.Bind(Button.CommandProperty, new Binding($"{command}Command"));
                toolbar.Children.Add(button);
            }
        }

        var panel = new DockPanel();
        DockPanel.SetDock(toolbar, Dock.Top);
        panel.Children.Add(toolbar);
        var editor = new ContentControl();
        editor.Bind(ContentControl.ContentProperty, new Binding());
        panel.Children.Add(editor);
        Content = panel;
        this.Bind(TitleProperty, new Binding("DisplayTitle") { StringFormat = "{0} - Hammer 5 Tools" });

        AddonService.AddonsChanged += OnAddonsChanged;
        AddonService.ActiveAddonChanged += OnActiveAddonChanged;
        Opened += (_, _) =>
        {
            if (Document is null) ReloadDocument();
        };
        Closing += OnClosing;
        Closed += (_, _) =>
        {
            IsDisposed = true;
            AddonService.AddonsChanged -= OnAddonsChanged;
            AddonService.ActiveAddonChanged -= OnActiveAddonChanged;
            if (Document is not null)
            {
                Document.RequestClose -= OnDocumentCloseRequested;
                Document.Dispose();
            }
        };
        RefreshSelection();
    }

    private void ReloadDocument()
    {
        if (IsDisposed)
        {
            return;
        }

        if (Document is not null)
        {
            Document.RequestClose -= OnDocumentCloseRequested;
            Document.Dispose();
        }

        Document = CreateDocument();
        Document.RequestClose += OnDocumentCloseRequested;
        DataContext = Document;
    }

    private void OnDocumentCloseRequested(object? sender, EventArgs e) => Close();

    private void RefreshSelection()
    {
        UpdatingSelection = true;
        AddonSelector.ItemsSource = AddonService.Addons;
        AddonSelector.SelectedItem = AddonService.ActiveAddon;
        UpdatingSelection = false;
    }

    private async void OnSelectionChanged(object? sender, SelectionChangedEventArgs e)
    {
        if (UpdatingSelection || AddonSelector.SelectedItem is not Addon addon || addon.Name == AddonService.ActiveAddon?.Name)
        {
            return;
        }

        AddonSelector.IsEnabled = false;
        try
        {
            await SwitchAddon(addon);
        }
        catch (Exception ex)
        {
            await DialogService.ShowErrorAsync(ex.Message);
        }
        finally
        {
            RefreshSelection();
            AddonSelector.IsEnabled = true;
        }
    }

    private void OnAddonsChanged(object? sender, IReadOnlyList<Addon> addons) => Dispatcher.UIThread.Post(() =>
    {
        if (!IsDisposed) RefreshSelection();
    });

    private void OnActiveAddonChanged(object? sender, Addon? addon) => Dispatcher.UIThread.Post(() =>
    {
        if (IsDisposed) return;
        RefreshSelection();
        ReloadDocument();
    });

    private async void OnClosing(object? sender, WindowClosingEventArgs e)
    {
        if (CloseConfirmed || Document is null)
        {
            return;
        }

        e.Cancel = true;
        if (CheckingClose)
        {
            return;
        }

        CheckingClose = true;
        try
        {
            if (await DialogService.ConfirmCloseAsync([Document], this))
            {
                CloseConfirmed = true;
                Close();
            }
        }
        finally
        {
            CheckingClose = false;
        }
    }
}
