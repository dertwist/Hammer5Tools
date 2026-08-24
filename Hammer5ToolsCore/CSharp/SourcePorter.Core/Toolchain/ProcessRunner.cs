using System.Diagnostics;
using System.Text;

namespace SourcePorter.Core.Toolchain;

/// <summary>A single line of output from a child process.</summary>
/// <param name="Text">The line text (no trailing newline).</param>
/// <param name="IsError">True if the line came from stderr.</param>
public readonly record struct ProcessLine(string Text, bool IsError);

/// <summary>
/// Runs the Valve command-line tools (source1import, resourcecompiler,
/// cs_mdl_import, vbsp, vpk) and streams their output line-by-line so the UI
/// can render a live console — replacing the "tee to a log" trick from the
/// guide (§1.2.2.1) with structured, captured logging.
/// </summary>
public sealed class ProcessRunner
{
    /// <summary>Raised on the thread-pool for every stdout/stderr line.</summary>
    public event Action<ProcessLine>? OnOutput;

    /// <summary>
    /// Runs <paramref name="fileName"/> with <paramref name="arguments"/> and
    /// returns the exit code. All output is forwarded via <see cref="OnOutput"/>
    /// and also returned joined in <paramref name="captured"/>.
    /// </summary>
    public async Task<int> RunAsync(
        string fileName,
        string arguments,
        string? workingDirectory,
        IReadOnlyDictionary<string, string>? environment,
        StringBuilder? captured,
        CancellationToken ct = default,
        string? standardInput = null)
    {
        var psi = new ProcessStartInfo
        {
            FileName = fileName,
            Arguments = arguments,
            WorkingDirectory = workingDirectory ?? Path.GetDirectoryName(fileName) ?? Environment.CurrentDirectory,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            // Some tools prompt for confirmation on stdin (e.g. source1import asks "Are you
            // sure?" when the gameinfo dir isn't named csgo). When standardInput is supplied we
            // feed it that answer; otherwise the child inherits no console and would hang.
            RedirectStandardInput = standardInput is not null,
            CreateNoWindow = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
        };

        if (environment is not null)
            foreach (var (k, v) in environment)
                psi.Environment[k] = v;

        using var process = new Process { StartInfo = psi, EnableRaisingEvents = true };

        void Emit(string? line, bool isError)
        {
            if (line is null)
                return;
            captured?.AppendLine(line);
            OnOutput?.Invoke(new ProcessLine(line, isError));
        }

        process.OutputDataReceived += (_, e) => Emit(e.Data, false);
        process.ErrorDataReceived += (_, e) => Emit(e.Data, true);

        if (!process.Start())
            throw new InvalidOperationException($"Failed to start '{fileName}'.");

        process.BeginOutputReadLine();
        process.BeginErrorReadLine();

        if (standardInput is not null)
        {
            // Answer any confirmation prompt, then close stdin so the tool sees EOF.
            try
            {
                await process.StandardInput.WriteAsync(standardInput).ConfigureAwait(false);
                process.StandardInput.Close();
            }
            catch
            {
                // Process may have already exited / closed its input — nothing to do.
            }
        }

        await using (ct.Register(() => TryKill(process)))
        {
            await process.WaitForExitAsync(ct).ConfigureAwait(false);
        }

        return process.ExitCode;
    }

    private static void TryKill(Process p)
    {
        try
        {
            if (!p.HasExited)
                p.Kill(entireProcessTree: true);
        }
        catch
        {
            // Process already gone — nothing to do.
        }
    }
}
