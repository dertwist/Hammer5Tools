namespace Hammer5Tools.Core;

/// <summary>
/// Contains a Core operation value and its structured diagnostics.
/// </summary>
public sealed record CoreResult<T>(T? Value, IReadOnlyList<CoreDiagnostic> Diagnostics)
{
    /// <summary>
    /// Gets whether the operation produced no error diagnostics.
    /// </summary>
    public bool IsSuccess => Diagnostics.All(diagnostic => diagnostic.Severity != CoreDiagnosticSeverity.Error);
}

/// <summary>
/// Creates typed Core operation results.
/// </summary>
public static class CoreResult
{
    /// <summary>
    /// Creates a successful result without diagnostics.
    /// </summary>
    public static CoreResult<T> Success<T>(T value) => new(value, []);

    /// <summary>
    /// Creates a failed result with one error diagnostic.
    /// </summary>
    public static CoreResult<T> Failure<T>(string code, string message) => new(
        default,
        [new CoreDiagnostic(CoreDiagnosticSeverity.Error, code, message)]);
}
