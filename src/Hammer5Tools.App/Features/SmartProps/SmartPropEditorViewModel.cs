namespace Hammer5Tools.App.Features.SmartProps;

using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.App.Services;
using Hammer5Tools.App.ViewModels;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Cs2;

public sealed class SmartPropEditorViewModel : DocumentViewModel
{
    private readonly ICs2Locator locator;
    private readonly IAddonService addons;
    private SmartPropEditorView? view;
    private readonly string? initialPath;
    private readonly IDialogService dialogs;
    public override string IconUri => "avares://Hammer5Tools.App/Assets/Icons/smartprop_editor.png";
    public Task InitialLoadTask { get; private set; } = Task.CompletedTask;

    public SmartPropEditorViewModel(ICs2Locator locator, IAddonService addons, IDialogService dialogs, string? path = null)
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
    }

    public SmartPropEditorView View
    {
        get
        {
            if (view is null)
            {
                view = new(initialPath is null);
                var install = locator.FindCs2Path();
                view.ConfigureResources(install is null ? null : Path.Combine(install, "game"), addons.ActiveAddon?.Name ?? "");
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
