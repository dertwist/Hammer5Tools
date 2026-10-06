namespace Hammer5Tools.App.Features.SmartProps;

using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.Services;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Cs2;

public sealed class SmartPropEditorViewModel : DocumentViewModel
{
    private readonly ICs2Locator locator;
    private readonly IAddonService? addons;
    private SmartPropEditorView? view;
    private readonly string? initialPath;
    private readonly IDialogService dialogs;
    public override string IconUri => "avares://Hammer5Tools.App/Assets/Icons/smartprop_editor.png";
    public Task InitialLoadTask { get; private set; } = Task.CompletedTask;

    public SmartPropEditorViewModel(ICs2Locator locator, IAddonService? addons, IDialogService dialogs, string? path = null)
    {
        this.locator = locator;
        this.addons = addons;
        this.dialogs = dialogs;
        initialPath = path;
        DocumentPath = path;
        Title = path is null ? "SmartProp Editor" : Path.GetFileName(path);
        ReportSaveFailure = dialogs.ShowErrorAsync;
        UndoCommand = new AsyncRelayCommand(() => View.UndoDocumentAsync(), () => view?.CanUndo == true);
        RedoCommand = new AsyncRelayCommand(() => View.RedoDocumentAsync(), () => view?.CanRedo == true);
        SaveAsCommand = new AsyncRelayCommand(async () => await View.SaveAsAsync());
        LoadCargoVanCommand = new AsyncRelayCommand(() => View.LoadCargoVanAsync());
        LoadExampleCommand = new AsyncRelayCommand(() => View.LoadExampleAsync());
        CutCommand = new AsyncRelayCommand(() => View.HierarchyAction("cut"));
        CopyCommand = new AsyncRelayCommand(() => View.HierarchyAction("copy"));
        PasteCommand = new AsyncRelayCommand(() => View.HierarchyAction("paste"));
        PasteWithReplacementCommand = new AsyncRelayCommand(() => View.HierarchyAction("paste-replace"));
        GroupSelectedCommand = new AsyncRelayCommand(() => View.HierarchyAction("group"));
        AddGroupCommand = new AsyncRelayCommand(() => View.HierarchyAction("add", "CSmartPropElement_Group"));
        AddModelCommand = new AsyncRelayCommand(() => View.HierarchyAction("add", "CSmartPropElement_Model"));
        DuplicateCommand = new AsyncRelayCommand(() => View.HierarchyAction("duplicate"));
        DeleteCommand = new AsyncRelayCommand(() => View.HierarchyAction("remove"));
        MoveUpCommand = new AsyncRelayCommand(() => View.HierarchyAction("up"));
        MoveDownCommand = new AsyncRelayCommand(() => View.HierarchyAction("down"));
        FrameAllCommand = new RelayCommand(() => View.FrameScene());
    }

    public SmartPropEditorView View
    {
        get
        {
            if (view is null)
            {
                view = new(initialPath is null);
                var install = locator.FindCs2Path();
                view.ConfigureResources(install is null ? null : Path.Combine(install, "game"), (initialPath is not null && install is not null ? Cs2Paths.GetContentAddonName(install, initialPath) : addons?.ActiveAddon?.Name) ?? "");
                view.DocumentStateChanged += OnDocumentStateChanged;
                if (initialPath is not null)
                {
                    InitialLoadTask = OpenInitialDocumentAsync(initialPath);
                }
            }
            return view;
        }
    }

    public override IRelayCommand UndoCommand { get; }
    public override IRelayCommand RedoCommand { get; }
    public IRelayCommand SaveAsCommand { get; }
    public IRelayCommand LoadCargoVanCommand { get; }
    public IRelayCommand LoadExampleCommand { get; }
    public IRelayCommand CutCommand { get; }
    public IRelayCommand CopyCommand { get; }
    public IRelayCommand PasteCommand { get; }
    public IRelayCommand PasteWithReplacementCommand { get; }
    public IRelayCommand GroupSelectedCommand { get; }
    public IRelayCommand AddGroupCommand { get; }
    public IRelayCommand AddModelCommand { get; }
    public IRelayCommand DuplicateCommand { get; }
    public IRelayCommand DeleteCommand { get; }
    public IRelayCommand MoveUpCommand { get; }
    public IRelayCommand MoveDownCommand { get; }
    public IRelayCommand FrameAllCommand { get; }

    private async Task OpenInitialDocumentAsync(string path)
    {
        try
        {
            await View.OpenDocumentAsync(path);
        }
        catch (Exception exception)
        {
            await dialogs.ShowErrorAsync($"Could not open SmartProp: {exception.Message}");
        }
    }

    private void OnDocumentStateChanged(object? sender, EventArgs args)
    {
        Title = View.DocumentTitle;
        DocumentPath = View.DocumentPath;
        IsDirty = View.HasUnsavedChanges;
        UndoCommand.NotifyCanExecuteChanged();
        RedoCommand.NotifyCanExecuteChanged();
    }

    protected override Task<bool> SaveCoreAsync() => View.SaveDocumentAsync();

    public override void Dispose()
    {
        if (view is not null)
        {
            view.DocumentStateChanged -= OnDocumentStateChanged;
            view.Dispose();
        }
        base.Dispose();
    }
}
