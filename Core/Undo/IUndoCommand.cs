namespace Hammer5Tools.Core.Undo;

/// <summary>
/// Represents an undoable/redoable action.
/// </summary>
public interface IUndoCommand
{
    string Description { get; }

    void Execute();

    void Undo();
}
