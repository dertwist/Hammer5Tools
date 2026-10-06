namespace Hammer5Tools.Cli.Commands;

using System.ComponentModel;
using System.Text.Json;
using Hammer5Tools.Core.Cs2;
using Spectre.Console;
using Spectre.Console.Cli;

public class Cs2Command : AsyncCommand<Cs2Command.Settings>
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    private readonly ICs2Launcher Cs2Launcher;

    public Cs2Command(ICs2Launcher cs2Launcher)
    {
        Cs2Launcher = cs2Launcher;
    }

    public class Settings : CommandSettings
    {
        [CommandArgument(0, "<action>")]
        [Description("Action: launch, kill, or status")]
        public string Action { get; set; } = "status";

        [CommandOption("--addon <ADDON>")]
        [Description("Addon name to launch with")]
        public string? Addon { get; set; }

        [CommandOption("--json")]
        [Description("Output in JSON format for agent automation")]
        public bool Json { get; set; }
    }

    public override async Task<int> ExecuteAsync(CommandContext context, Settings settings, CancellationToken cancellationToken)
    {
        var action = settings.Action.ToLowerInvariant();

        if (action == "status")
        {
            var running = Cs2Launcher.IsRunning;
            if (settings.Json)
            {
                var json = JsonSerializer.Serialize(new { IsRunning = running }, JsonOptions);
                AnsiConsole.WriteLine(json);
            }
            else
            {
                AnsiConsole.MarkupLine($"CS2 Workshop Tools running: {(running ? "[green]Yes[/]" : "[grey]No[/]")}");
            }
            return 0;
        }

        if (action == "launch")
        {
            var success = await Cs2Launcher.LaunchAsync(settings.Addon, ct: cancellationToken);
            AnsiConsole.MarkupLine(success ? "[green]Launched CS2.[/]" : "[red]Failed to launch CS2.[/]");
            return success ? 0 : 1;
        }

        if (action == "kill")
        {
            Cs2Launcher.Kill();
            AnsiConsole.MarkupLine("[yellow]CS2 killed.[/]");
            return 0;
        }

        AnsiConsole.MarkupLine("[red]Unknown action. Use: status, launch, kill[/]");
        return 1;
    }
}
