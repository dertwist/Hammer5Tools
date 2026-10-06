namespace Hammer5Tools.Core.Hotkeys;

/// <summary>
/// A keybinding mapping an input shortcut to a command within a specific context.
/// </summary>
public class HotkeyBinding : CommunityToolkit.Mvvm.ComponentModel.ObservableObject
{
    private string ContextValue = string.Empty;

    internal ValveKeyValue.KVObject Original { get; set; } = new();

    public string Context
    {
        get => ContextValue;
        set => SetProperty(ref ContextValue, value);
    }

    private string CommandValue = string.Empty;

    public string Command
    {
        get => CommandValue;
        set => SetProperty(ref CommandValue, value);
    }

    private string InputValue = string.Empty;

    public string Input
    {
        get => InputValue;
        set => SetProperty(ref InputValue, value);
    }

    public HotkeyBinding(string context, string command, string input)
    {
        Context = context;
        Command = command;
        Input = input;
    }
}
