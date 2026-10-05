namespace Hammer5Tools.App.ViewModels;

using System.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Hammer5Tools.Core.Undo;

public abstract class DocumentViewModel : ViewModelBase, IDisposable
{
    private string TitleValue = "Untitled";
    private bool IsDirtyValue;
    private string PreviousSnapshot = string.Empty;
    private string SavedSnapshot = string.Empty;
    private Func<string>? SerializeDocument;
    private Action<string>? RestoreDocument;
    private bool IsRestoring;
    private readonly List<INotifyPropertyChanged> ObservedModels = [];

    public virtual string IconUri => "avares://Hammer5Tools.App/Assets/Icons/hammer_icon.png";

    public string? DocumentPath { get; protected set; }

    protected Func<string, Task>? ReportSaveFailure { get; set; }

    public UndoService Undo { get; } = new();

    public IReadOnlyList<string> UndoHistory => Undo.History;

    public string Title
    {
        get => TitleValue;
        set
        {
            if (SetProperty(ref TitleValue, value))
            {
                OnPropertyChanged(nameof(DisplayTitle));
            }
        }
    }

    public bool IsDirty
    {
        get => IsDirtyValue;
        set
        {
            if (SetProperty(ref IsDirtyValue, value))
            {
                OnPropertyChanged(nameof(DisplayTitle));
            }
        }
    }

    public string DisplayTitle => IsDirty ? $"{Title}*" : Title;

    public event EventHandler? RequestClose;

    public IRelayCommand CloseCommand { get; }

    public IRelayCommand SaveCommand { get; }

    public IRelayCommand UndoCommand { get; }

    public IRelayCommand RedoCommand { get; }

    protected DocumentViewModel()
    {
        CloseCommand = new RelayCommand(() => RequestClose?.Invoke(this, EventArgs.Empty));
        SaveCommand = new AsyncRelayCommand(async () => await SaveAsync());
        UndoCommand = new RelayCommand(Undo.Undo, () => Undo.CanUndo);
        RedoCommand = new RelayCommand(Undo.Redo, () => Undo.CanRedo);
        Undo.StateChanged += (_, _) =>
        {
            OnPropertyChanged(nameof(UndoHistory));
            UndoCommand.NotifyCanExecuteChanged();
            RedoCommand.NotifyCanExecuteChanged();
        };
    }

    public async Task<bool> SaveAsync()
    {
        try
        {
            if (!await SaveCoreAsync())
            {
                return false;
            }
        }
        catch (Exception ex) when (ReportSaveFailure is not null)
        {
            await ReportSaveFailure($"Could not save {Title}: {ex.Message}");
            return false;
        }

        SavedSnapshot = SerializeDocument?.Invoke() ?? string.Empty;
        IsDirty = false;
        return true;
    }

    protected virtual Task<bool> SaveCoreAsync()
    {
        return Task.FromResult(!IsDirty);
    }

    protected void InitializeHistory(Func<string> serialize, Action<string> restore)
    {
        SerializeDocument = serialize;
        RestoreDocument = restore;
        PreviousSnapshot = SavedSnapshot = serialize();
        Undo.Clear();
        IsDirty = false;
    }

    protected void ObserveModels(IEnumerable<INotifyPropertyChanged> models)
    {
        foreach (var model in ObservedModels)
        {
            model.PropertyChanged -= OnModelChanged;
        }

        ObservedModels.Clear();
        foreach (var model in models)
        {
            model.PropertyChanged += OnModelChanged;
            ObservedModels.Add(model);
        }
    }

    private void OnModelChanged(object? sender, PropertyChangedEventArgs e)
    {
        MarkDirty();
    }

    protected void MarkDirty()
    {
        if (IsRestoring)
        {
            return;
        }

        if (SerializeDocument is null)
        {
            IsDirty = true;
            return;
        }

        var current = SerializeDocument();
        if (current == PreviousSnapshot)
        {
            return;
        }

        Undo.Execute(new SnapshotCommand(this, PreviousSnapshot, current));
    }

    private void RestoreSnapshot(string snapshot)
    {
        IsRestoring = true;
        try
        {
            RestoreDocument!(snapshot);
            PreviousSnapshot = snapshot;
            IsDirty = snapshot != SavedSnapshot;
        }
        finally
        {
            IsRestoring = false;
        }
    }

    private sealed class SnapshotCommand : IUndoCommand
    {
        private bool FirstExecution = true;
        private readonly DocumentViewModel Document;
        private readonly string Before;
        private readonly string After;

        public SnapshotCommand(DocumentViewModel document, string before, string after)
        {
            Document = document;
            Before = before;
            After = after;
        }

        public string Description => "Edit document";

        public void Execute()
        {
            if (FirstExecution)
            {
                FirstExecution = false;
                Document.PreviousSnapshot = After;
                Document.IsDirty = After != Document.SavedSnapshot;
                return;
            }

            Document.RestoreSnapshot(After);
        }

        public void Undo()
        {
            Document.RestoreSnapshot(Before);
        }
    }

    public virtual void Dispose()
    {
        ObserveModels([]);
        GC.SuppressFinalize(this);
    }
}
