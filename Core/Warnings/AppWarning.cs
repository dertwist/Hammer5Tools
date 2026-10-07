namespace Hammer5Tools.Core.Warnings;

/// <summary>
/// Represents an active diagnostic or operational warning surfaced in the application.
/// </summary>
public sealed record AppWarning(
    string Id,
    string Title,
    string Message,
    string? ShortTitle = null,
    string? ToolTip = null,
    string? ActionTitle = null,
    Func<Task>? Action = null
);
