namespace Hammer5Tools.Cli.Commands;

using System.ComponentModel;
using System.Text.Json;
using Hammer5Tools.Core.Compiler;
using Spectre.Console;
using Spectre.Console.Cli;

public class CompileCommand : AsyncCommand<CompileCommand.Settings>
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    private readonly IResourceCompiler ResourceCompiler;

    public CompileCommand(IResourceCompiler resourceCompiler)
    {
        ResourceCompiler = resourceCompiler;
    }

    public class Settings : CommandSettings
    {
        [CommandArgument(0, "<target>")]
        [Description("Asset or map file path to compile")]
        public string TargetPath { get; set; } = string.Empty;

        [CommandOption("-a|--addon <ADDON>")]
        [Description("Addon name context")]
        public string? Addon { get; set; }

        [CommandOption("--json")]
        [Description("Output in JSON format for agent automation")]
        public bool Json { get; set; }
    }

    public override async Task<int> ExecuteAsync(CommandContext context, Settings settings, CancellationToken cancellationToken)
    {
        var result = await ResourceCompiler.CompileAssetAsync(settings.TargetPath, settings.Addon, cancellationToken);

        if (settings.Json)
        {
            var json = JsonSerializer.Serialize(new
            {
                result.Success,
                result.ExitCode,
                result.StandardOutput,
                result.StandardError,
                DurationMs = result.Duration.TotalMilliseconds,
            }, JsonOptions);
            AnsiConsole.WriteLine(json);
        }
        else
        {
            if (result.Success)
            {
                AnsiConsole.MarkupLine($"[green]Compilation succeeded for '{settings.TargetPath}' in {result.Duration.TotalSeconds:F2}s.[/]");
            }
            else
            {
                AnsiConsole.MarkupLine($"[red]Compilation failed with exit code {result.ExitCode}.[/]");
                if (!string.IsNullOrWhiteSpace(result.StandardError))
                {
                    AnsiConsole.WriteLine(result.StandardError);
                }
            }
        }

        return result.Success ? 0 : 1;
    }
}
