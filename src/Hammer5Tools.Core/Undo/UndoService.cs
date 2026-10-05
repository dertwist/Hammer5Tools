namespace Hammer5Tools.Core.Undo;

/// <summary>
/// Default implementation of IUndoService using command history stacks.
/// </summary>
public class UndoService : IUndoService
{
    private readonly Stack<IUndoCommand> UndoStack = new();
    private readonly Stack<IUndoCommand> RedoStack = new();

    public bool CanUndo => UndoStack.Count > 0;

    public bool CanRedo => RedoStack.Count > 0;

    public string? UndoDescription => CanUndo ? UndoStack.Peek().Description : null;

    public string? RedoDescription => CanRedo ? RedoStack.Peek().Description : null;

    public event EventHandler? StateChanged;

    public void Execute(IUndoCommand command)
    {
        ArgumentNullException.ThrowIfNull(command);

        command.Execute();
        UndoStack.Push(command);
        RedoStack.Clear();
        StateChanged?.Invoke(this, EventArgs.Empty);
    }

    public void Undo()
    {
        if (!CanUndo)
        {
            return;
        }

        var command = UndoStack.Pop();
        command.Undo();
        RedoStack.Push(command);
        StateChanged?.Invoke(this, EventArgs.Empty);
    }

    public void Redo()
    {
        if (!CanRedo)
        {
            return;
        }

        var command = RedoStack.Pop();
        command.Execute();
        UndoStack.Push(command);
        StateChanged?.Invoke(this, EventArgs.Empty);
    }

    public void Clear()
    {
        UndoStack.Clear();
        RedoStack.Clear();
        StateChanged?.Invoke(this, EventArgs.Empty);
    }
}
