namespace Hammer5Tools.Core.Undo;

/// <summary>
/// Service managing undo and redo history.
/// </summary>
public interface IUndoService
{
    bool CanUndo { get; }

    bool CanRedo { get; }

    string? UndoDescription { get; }

    string? RedoDescription { get; }

    event EventHandler? StateChanged;

    void Execute(IUndoCommand command);

    void Undo();

    void Redo();

    void Clear();
}
