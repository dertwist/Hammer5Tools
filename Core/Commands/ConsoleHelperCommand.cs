namespace Hammer5Tools.Core.Commands;

/// <summary>A command preset from a shared or user Convar Helper page.</summary>
public sealed record ConsoleHelperCommand(string Label, string Command, string Description, string Source)
{
    /// <summary>Gets the authored button column.</summary>
    public int Column { get; init; }
    /// <summary>Gets the authored button row.</summary>
    public int Row { get; init; }
    /// <summary>Gets the page column count.</summary>
    public int GridWidth { get; init; } = 2;
    /// <summary>Gets the page row count.</summary>
    public int GridHeight { get; init; } = 36;
    /// <summary>Gets whether this cell is a section heading.</summary>
    public bool IsHeading => string.IsNullOrEmpty(Command);

    /// <summary>Gets the searchable display text.</summary>
    public string Details => $"{Label} — {Command}  {Description} ({Source})";
}
