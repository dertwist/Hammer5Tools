namespace Hammer5Tools.Core.Hotkeys;

/// <summary>
/// An input macro defining key modifiers or special inputs.
/// </summary>
public class HotkeyMacro
{
    internal ValveKeyValue.KVObject Original { get; set; } = new();

    public string Name { get; set; }

    public string Input { get; set; }

    public HotkeyMacro(string name, string input)
    {
        Name = name;
        Input = input;
    }
}
