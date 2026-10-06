namespace Hammer5Tools.App.Services;

using Avalonia.Controls;
using Avalonia.Data;
using Avalonia.Platform;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.Features.Shell;
using Hammer5Tools.App.Services.Lifecycle;
using Hammer5Tools.App.ViewModels;

public sealed class StandaloneToolWindow : Window
{
    private readonly DialogService DialogService;
    private readonly Func<string?, DocumentViewModel> CreateDocument;
    private readonly StartupTool Tool;
    private readonly Action OpenSettings;
    private readonly Action OpenMain;
    private readonly Menu ApplicationMenu = new() { Name = "StandaloneMenu" };
    private bool CheckingClose;
    private bool CloseConfirmed;
    private bool ChangingDocument;
    private bool IsDisposed;

    public DocumentViewModel Document { get; private set; } = null!;

    public StandaloneToolWindow(StartupTool tool, DialogService dialogs,
        Func<string?, DocumentViewModel> createDocument, Action openSettings, Action openMain)
    {
        Tool = tool;
        DialogService = dialogs;
        CreateDocument = createDocument;
        OpenSettings = openSettings;
        OpenMain = openMain;
        Width = tool == StartupTool.MapBuilder ? 1282 : 1200;
        Height = tool == StartupTool.MapBuilder ? 933 : 800;
        MinWidth = 800;
        MinHeight = 500;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;

        var panel = new DockPanel();
        DockPanel.SetDock(ApplicationMenu, Dock.Top);
        panel.Children.Add(ApplicationMenu);
        var editor = new ContentControl();
        editor.Bind(ContentControl.ContentProperty, new Binding());
        panel.Children.Add(editor);
        Content = panel;
        this.Bind(TitleProperty, new Binding("DisplayTitle") { StringFormat = "{0} - Hammer 5 Tools" });

        Opened += (_, _) =>
        {
            if (Document is null) ReplaceDocument(null);
        };
        Closing += OnClosing;
        Closed += (_, _) =>
        {
            IsDisposed = true;
            if (Document is not null)
            {
                Document.RequestClose -= OnDocumentCloseRequested;
                Document.Dispose();
            }
        };
    }

    public async Task<bool> OpenDocumentAsync(string? path)
    {
        if (IsDisposed || ChangingDocument) return false;
        ChangingDocument = true;
        try
        {
            if (Document is not null && !await DialogService.ConfirmCloseAsync([Document], this)) return false;
            if (IsDisposed) return false;
            ReplaceDocument(path);
            return true;
        }
        finally
        {
            ChangingDocument = false;
        }
    }

    private void ReplaceDocument(string? path)
    {
        var document = CreateDocument(path);
        if (Document is not null)
        {
            Document.RequestClose -= OnDocumentCloseRequested;
            Document.Dispose();
        }
        Document = document;
        Document.RequestClose += OnDocumentCloseRequested;
        DataContext = Document;
        using var icon = AssetLoader.Open(new Uri(Document.IconUri));
        Icon = new WindowIcon(icon);
        UpdateMenu();
    }

    private void UpdateMenu()
    {
        var file = new List<EditorMenuAction>();
        if (Tool != StartupTool.MapBuilder)
        {
            file.Add(new("New", new AsyncRelayCommand(async () => await OpenDocumentAsync(null))));
            file.Add(new("Open...", new AsyncRelayCommand(async () =>
            {
                var path = await DialogService.OpenFileAsync("Open document", Tool == StartupTool.SmartProps ? "*.vsmart" : "*.vsndevts");
                if (path is not null) await OpenDocumentAsync(path);
            })));
            file.Add(new("Save", Document.SaveCommand));
        }
        var edit = new List<EditorMenuAction>
        {
            new("Undo", Document.UndoCommand),
            new("Redo", Document.RedoCommand),
            new("Preferences", new RelayCommand(OpenSettings)),
        };
        var view = new List<EditorMenuAction>();
        EditorMenus.AddDocumentActions(Document, file, edit, view, out var elements, out var editorMenu);
        file.Add(new("Close", new RelayCommand(Close)));
        ApplicationMenu.Items.Clear();
        AddMenu("_File", file);
        AddMenu("_Edit", edit);
        if (view.Count > 0) AddMenu("_View", view);
        if (elements is not null) AddMenu("_Element", elements);
        if (editorMenu is { } menu) AddMenu(menu.Header, menu.Items);
        AddMenu("_Tools", [new("Hammer 5 Tools", new RelayCommand(OpenMain))]);
        AddMenu("_Help", [new("Check for updates...", new RelayCommand(() => Program.OpenUpdates()))]);
    }

    private void AddMenu(string header, IEnumerable<EditorMenuAction> actions)
    {
        var menu = new MenuItem { Header = header };
        foreach (var action in actions)
        {
            var item = new MenuItem { Header = action.Header, Command = action.Command };
            item.Classes.Add("menu-popup-item");
            menu.Items.Add(item);
        }
        ApplicationMenu.Items.Add(menu);
    }

    private void OnDocumentCloseRequested(object? sender, EventArgs e) => Close();

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
