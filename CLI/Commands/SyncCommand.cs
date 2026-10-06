namespace Hammer5Tools.Cli.Commands;

using System.ComponentModel;
using System.Text.Json;
using Hammer5Tools.Core.GitSync;
using Spectre.Console;
using Spectre.Console.Cli;

public class SyncCommand : AsyncCommand<SyncCommand.Settings>
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    private readonly IGitSyncService GitSyncService;

    public SyncCommand(IGitSyncService gitSyncService)
    {
        GitSyncService = gitSyncService;
    }

    public class Settings : CommandSettings
    {
        [CommandArgument(0, "<action>")]
        [Description("Sync action: status, pull, or push")]
        public string Action { get; set; } = "status";

        [CommandOption("-p|--path <PATH>")]
        [Description("Repository path (defaults to current directory)")]
        public string? Path { get; set; }

        [CommandOption("--json")]
        [Description("Output in JSON format for agent automation")]
        public bool Json { get; set; }
    }

    public override async Task<int> ExecuteAsync(CommandContext context, Settings settings, CancellationToken cancellationToken)
    {
        var targetDir = settings.Path ?? Directory.GetCurrentDirectory();
        var action = settings.Action.ToLowerInvariant();

        if (action == "status")
        {
            var status = await GitSyncService.GetStatusAsync(targetDir, cancellationToken);
            if (settings.Json)
            {
                var json = JsonSerializer.Serialize(status, JsonOptions);
                AnsiConsole.WriteLine(json);
            }
            else
            {
                AnsiConsole.MarkupLine($"[bold]Git Repo:[/] {(status.IsGitRepository ? "[green]Yes[/]" : "[red]No[/]")}");
                AnsiConsole.MarkupLine($"[bold]Branch:[/] {status.Branch}");
                AnsiConsole.MarkupLine($"[bold]Modified Files:[/] {status.ModifiedFiles.Count}");
                foreach (var f in status.ModifiedFiles)
                {
                    AnsiConsole.MarkupLine($"  [yellow]M[/] {f}");
                }
                foreach (var f in status.UntrackedFiles)
                {
                    AnsiConsole.MarkupLine($"  [green]?[/] {f}");
                }
            }
            return 0;
        }

        if (action == "pull")
        {
            var success = await GitSyncService.PullAsync(targetDir, cancellationToken);
            AnsiConsole.MarkupLine(success ? "[green]Pull succeeded.[/]" : "[red]Pull failed.[/]");
            return success ? 0 : 1;
        }

        if (action == "push")
        {
            var success = await GitSyncService.PushAsync(targetDir, cancellationToken);
            AnsiConsole.MarkupLine(success ? "[green]Push succeeded.[/]" : "[red]Push failed.[/]");
            return success ? 0 : 1;
        }

        AnsiConsole.MarkupLine("[red]Unknown sync action. Use: status, pull, push[/]");
        return 1;
    }
}
