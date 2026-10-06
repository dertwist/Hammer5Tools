namespace Hammer5Tools.Core.IO.Compiler;

using System.Diagnostics;
using System.IO;
using System.Text;
using Hammer5Tools.Core.Addons;
using Hammer5Tools.Core.Compiler;
using Hammer5Tools.Core.Cs2;
using Microsoft.Extensions.Logging;

/// <summary>
/// Service executing resourcecompiler.exe for Source 2 asset compilation.
/// </summary>
public class ResourceCompiler : IResourceCompiler
{
    private readonly ICs2Locator Cs2Locator;
    private readonly IAddonService AddonService;
    private readonly ILogger<ResourceCompiler>? Logger;

    public bool IsAvailable
    {
        get
        {
            var cs2Path = Cs2Locator.ResolvedCs2Path;
            return !string.IsNullOrWhiteSpace(cs2Path) && File.Exists(Cs2Paths.GetResourceCompilerPath(cs2Path));
        }
    }

    public ResourceCompiler(
        ICs2Locator cs2Locator,
        IAddonService addonService,
        ILogger<ResourceCompiler>? logger = null)
    {
        Cs2Locator = cs2Locator;
        AddonService = addonService;
        Logger = logger;
    }

    /// <inheritdoc/>
    public Task<CompileResult> CompileAssetAsync(string assetFilePath, string? addonName = null, CancellationToken ct = default)
    {
        return CompileAssetAsync(assetFilePath, addonName, null, ct);
    }

    /// <inheritdoc/>
    public async Task<CompileResult> CompileAssetAsync(string assetFilePath, string? addonName, string? additionalArguments, CancellationToken ct = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(assetFilePath);

        var args = BuildArguments($"-i \"{Path.GetFullPath(assetFilePath)}\" {additionalArguments}".TrimEnd(), addonName);
        return await ExecuteCompilerAsync(args, ct);
    }

    /// <inheritdoc/>
    public Task<CompileResult> CompileAssetAsync(string assetFilePath, string? addonName, string? additionalArguments, Action<string> output, CancellationToken ct = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(assetFilePath);
        var args = BuildArguments($"-i \"{Path.GetFullPath(assetFilePath)}\" {additionalArguments}".TrimEnd(), addonName);
        return ExecuteCompilerAsync(args, ct, output);
    }

    /// <inheritdoc/>
    public async Task<CompileResult> CompileFolderAsync(string folderPath, string? addonName = null, CancellationToken ct = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(folderPath);

        var targetPattern = Path.Combine(Path.GetFullPath(folderPath), "*.*");
        var args = BuildArguments($"-r -i \"{targetPattern}\"", addonName);
        return await ExecuteCompilerAsync(args, ct);
    }

    /// <inheritdoc/>
    public async Task<CompileResult> QuickCreateVmdlAsync(string meshFilePath, string? addonName = null, CancellationToken ct = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(meshFilePath);

        var meshFull = Path.GetFullPath(meshFilePath);
        var dir = Path.GetDirectoryName(meshFull) ?? string.Empty;
        var nameWithoutExt = Path.GetFileNameWithoutExtension(meshFull);
        var vmdlPath = Path.Combine(dir, $"{nameWithoutExt}.vmdl");

        var relativeFilename = Path.GetFileName(meshFull);

        var vmdlContent = $$"""
            <!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
            {
                rootNode = 
                {
                    _class = "RootNode"
                    children = 
                    [
                        {
                            _class = "RenderMeshList"
                            children = 
                            [
                                {
                                    _class = "RenderMeshFile"
                                    filename = "{{relativeFilename}}"
                                }
                            ]
                        }
                    ]
                }
            }
            """;

        await File.WriteAllTextAsync(vmdlPath, vmdlContent, ct);
        Logger?.LogInformation("Created quick VMDL at {Path}", vmdlPath);

        return await CompileAssetAsync(vmdlPath, addonName, ct);
    }

    public string BuildArguments(string commandFlags, string? addonName = null)
    {
        var targetAddon = addonName ?? AddonService.ActiveAddon?.Name;
        var sb = new StringBuilder();

        if (!string.IsNullOrWhiteSpace(targetAddon))
        {
            sb.Append("-addon ").Append(targetAddon).Append(' ');
        }

        sb.Append(commandFlags);
        return sb.ToString();
    }

    private async Task<CompileResult> ExecuteCompilerAsync(string arguments, CancellationToken ct, Action<string>? output = null)
    {
        var cs2Path = Cs2Locator.ResolvedCs2Path;
        if (string.IsNullOrWhiteSpace(cs2Path))
        {
            return new CompileResult(-1, string.Empty, "CS2 path is not resolved.", TimeSpan.Zero);
        }

        var rcPath = Cs2Paths.GetResourceCompilerPath(cs2Path);
        if (!File.Exists(rcPath))
        {
            return new CompileResult(-1, string.Empty, $"resourcecompiler.exe not found at '{rcPath}'.", TimeSpan.Zero);
        }

        var workingDir = Cs2Paths.GetBinWin64Path(cs2Path);
        var stdout = new StringBuilder();
        var stderr = new StringBuilder();
        var stopwatch = Stopwatch.StartNew();

        var psi = new ProcessStartInfo
        {
            FileName = rcPath,
            Arguments = arguments,
            WorkingDirectory = workingDir,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        };

        try
        {
            using var process = new Process { StartInfo = psi };
            process.OutputDataReceived += (_, e) =>
            {
                if (e.Data is not null)
                {
                    stdout.AppendLine(e.Data);
                    output?.Invoke(e.Data);
                }
            };
            process.ErrorDataReceived += (_, e) =>
            {
                if (e.Data is not null)
                {
                    stderr.AppendLine(e.Data);
                    output?.Invoke(e.Data);
                }
            };

            process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();

            try
            {
                await process.WaitForExitAsync(ct);
            }
            catch (OperationCanceledException)
            {
                if (!process.HasExited)
                {
                    process.Kill(entireProcessTree: true);
                }

                await process.WaitForExitAsync(CancellationToken.None);
                throw;
            }

            stopwatch.Stop();

            return new CompileResult(process.ExitCode, stdout.ToString(), stderr.ToString(), stopwatch.Elapsed);
        }
        catch (OperationCanceledException)
        {
            stopwatch.Stop();
            throw;
        }
        catch (Exception ex)
        {
            stopwatch.Stop();
            Logger?.LogError(ex, "Error running resourcecompiler.exe");
            return new CompileResult(-1, stdout.ToString(), ex.Message, stopwatch.Elapsed);
        }
    }
}
