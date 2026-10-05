namespace Hammer5Tools.Infrastructure.GitSync;

using System.Diagnostics;
using Hammer5Tools.Core.GitSync;
using Microsoft.Extensions.Logging;

public class GitSyncService : IGitSyncService
{
    private readonly ILogger<GitSyncService> Logger;

    public GitSyncService(ILogger<GitSyncService> logger)
    {
        Logger = logger;
    }

    public async Task<GitStatusResult> GetStatusAsync(string repositoryPath, CancellationToken cancellationToken = default)
    {
        var result = new GitStatusResult();
        if (!Directory.Exists(repositoryPath))
        {
            return result;
        }

        var gitDir = Path.Combine(repositoryPath, ".git");
        if (!Directory.Exists(gitDir) && !File.Exists(gitDir))
        {
            return result;
        }

        result.IsGitRepository = true;

        try
        {
            var branchOut = await RunGitCommandAsync(repositoryPath, "branch --show-current", cancellationToken);
            if (!string.IsNullOrWhiteSpace(branchOut.Output))
            {
                result.Branch = branchOut.Output.Trim();
            }

            var statusOut = await RunGitCommandAsync(repositoryPath, "status --porcelain", cancellationToken);
            var lines = statusOut.Output.Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries);
            foreach (var line in lines)
            {
                if (line.Length < 3)
                {
                    continue;
                }

                var status = line[..2];
                var file = line[3..].Trim();
                if (status == "??")
                {
                    result.UntrackedFiles.Add(file);
                }
                else
                {
                    result.ModifiedFiles.Add(file);
                }
            }
        }
        catch (Exception ex)
        {
            Logger.LogWarning(ex, "Failed to inspect git status for {Path}", repositoryPath);
        }

        return result;
    }

    public async Task<bool> PullAsync(string repositoryPath, CancellationToken cancellationToken = default)
    {
        var res = await RunGitCommandAsync(repositoryPath, "pull --rebase", cancellationToken);
        return res.ExitCode == 0;
    }

    public async Task<bool> PushAsync(string repositoryPath, CancellationToken cancellationToken = default)
    {
        var res = await RunGitCommandAsync(repositoryPath, "push", cancellationToken);
        return res.ExitCode == 0;
    }

    public async Task<bool> CommitAsync(string repositoryPath, string message, CancellationToken cancellationToken = default)
    {
        var addRes = await RunGitCommandAsync(repositoryPath, "add -A", cancellationToken);
        if (addRes.ExitCode != 0)
        {
            return false;
        }

        var commitRes = await RunGitCommandAsync(repositoryPath, $"commit -m \"{message.Replace("\"", "\\\"")}\"", cancellationToken);
        return commitRes.ExitCode == 0;
    }

    private static async Task<(int ExitCode, string Output)> RunGitCommandAsync(string workingDir, string arguments, CancellationToken cancellationToken)
    {
        var psi = new ProcessStartInfo
        {
            FileName = "git",
            Arguments = arguments,
            WorkingDirectory = workingDir,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        using var process = Process.Start(psi);
        if (process is null)
        {
            return (-1, string.Empty);
        }

        var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);

        await process.WaitForExitAsync(cancellationToken);

        var output = await stdoutTask;
        var error = await stderrTask;

        return (process.ExitCode, string.IsNullOrWhiteSpace(output) ? error : output);
    }
}
