namespace Hammer5Tools.Core.Compiler;

/// <summary>
/// Output and status from a resourcecompiler execution.
/// </summary>
public class CompileResult
{
    public bool Success => ExitCode == 0;

    public int ExitCode { get; }

    public string StandardOutput { get; }

    public string StandardError { get; }

    public TimeSpan Duration { get; }

    public CompileResult(int exitCode, string standardOutput, string standardError, TimeSpan duration)
    {
        ExitCode = exitCode;
        StandardOutput = standardOutput;
        StandardError = standardError;
        Duration = duration;
    }
}
