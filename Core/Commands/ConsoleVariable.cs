namespace Hammer5Tools.Core.Commands;

/// <summary>A live VConsole convar definition and its last reported value.</summary>
public sealed record ConsoleVariable(string Name, uint Flags, float Minimum, float Maximum, string? Value = null)
{
    /// <summary>Gets a compact description for the convar helper.</summary>
    public string Details => $"{Name}  {Value ?? ""}  (flags: 0x{Flags:X}, range: {Minimum}–{Maximum})";
}
