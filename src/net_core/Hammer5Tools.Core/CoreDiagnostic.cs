namespace Hammer5Tools.Core;

/// <summary>
/// Describes the severity of a Core operation diagnostic.
/// </summary>
public enum CoreDiagnosticSeverity
{
    /// <summary>An informational diagnostic.</summary>
    Information,

    /// <summary>A recoverable problem.</summary>
    Warning,

    /// <summary>A problem that prevented the operation from succeeding.</summary>
    Error,
}

/// <summary>
/// Describes a structured Core operation diagnostic.
/// </summary>
public sealed record CoreDiagnostic(CoreDiagnosticSeverity Severity, string Code, string Message);
