namespace Hammer5Tools.Cli.Commands;

using System.ComponentModel;
using System.Text.Json;
using Hammer5Tools.Core.SoundEvents;
using Spectre.Console;
using Spectre.Console.Cli;

public class SoundCommand : AsyncCommand<SoundCommand.Settings>
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    private readonly ISoundEventService SoundEventService;

    public SoundCommand(ISoundEventService soundEventService)
    {
        SoundEventService = soundEventService;
    }

    public class Settings : CommandSettings
    {
        [CommandArgument(0, "<action>")]
        [Description("Action: list, inspect, or query-vpk")]
        public string Action { get; set; } = "list";

        [CommandOption("-f|--filter <FILTER>")]
        [Description("Search filter for sound events or VPK entries")]
        public string? Filter { get; set; }

        [CommandOption("-p|--path <PATH>")]
        [Description("Path to .vsndevts file")]
        public string? Path { get; set; }

        [CommandOption("--json")]
        [Description("Output in JSON format for agent automation")]
        public bool Json { get; set; }
    }

    public override async Task<int> ExecuteAsync(CommandContext context, Settings settings, CancellationToken cancellationToken)
    {
        var action = settings.Action.ToLowerInvariant();

        if (action == "query-vpk")
        {
            var sounds = await SoundEventService.QueryVpkSoundsAsync(settings.Filter, cancellationToken);
            if (settings.Json)
            {
                var json = JsonSerializer.Serialize(sounds, JsonOptions);
                AnsiConsole.WriteLine(json);
            }
            else
            {
                AnsiConsole.MarkupLine($"[bold]Found {sounds.Count} sound(s):[/]");
                foreach (var s in sounds.Take(50))
                {
                    AnsiConsole.WriteLine(s);
                }
            }
            return 0;
        }

        if (action == "list" && !string.IsNullOrWhiteSpace(settings.Path))
        {
            var doc = await SoundEventService.LoadDocumentAsync(settings.Path, cancellationToken);
            if (settings.Json)
            {
                var json = JsonSerializer.Serialize(doc.Events.Select(e => new { e.Name, e.Type }), JsonOptions);
                AnsiConsole.WriteLine(json);
            }
            else
            {
                var table = new Table().Border(TableBorder.Rounded);
                table.AddColumn("Event Name");
                table.AddColumn("Type");
                foreach (var e in doc.Events)
                {
                    table.AddRow(e.Name, e.Type);
                }
                AnsiConsole.Write(table);
            }
            return 0;
        }

        AnsiConsole.MarkupLine("[yellow]Use 'sound query-vpk -f <term>' or 'sound list -p <file.vsndevts>'[/]");
        return 0;
    }
}
