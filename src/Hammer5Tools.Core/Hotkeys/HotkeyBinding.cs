namespace Hammer5Tools.Core.Hotkeys;

/// <summary>
/// A keybinding mapping an input shortcut to a command within a specific context.
/// </summary>
public class HotkeyBinding
{
    public string Context { get; set; }

    public string Command { get; set; }

    public string Input { get; set; }

    public HotkeyBinding(string context, string command, string input)
    {
        Context = context;
        Command = command;
        Input = input;
    }
}
