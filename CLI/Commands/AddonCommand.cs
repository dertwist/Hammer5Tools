namespace Hammer5Tools.Cli.Commands;

using System.ComponentModel;
using System.Text.Json;
using Hammer5Tools.Core.Addons;
using Spectre.Console;
using Spectre.Console.Cli;

public class AddonCommand : AsyncCommand<AddonCommand.Settings>
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    private readonly IAddonService AddonService;

    public AddonCommand(IAddonService addonService)
    {
        AddonService = addonService;
    }

    public class Settings : CommandSettings
    {
        [CommandArgument(0, "[action]")]
        [Description("Action to perform: list, info, or switch")]
        public string Action { get; set; } = "list";

        [CommandArgument(1, "[name]")]
        [Description("Addon name (for info or switch)")]
        public string? Name { get; set; }

        [CommandOption("--json")]
        [Description("Output in JSON format for agent automation")]
        public bool Json { get; set; }
    }

    public override Task<int> ExecuteAsync(CommandContext context, Settings settings, CancellationToken cancellationToken)
    {
        var action = settings.Action.ToLowerInvariant();

        if (action == "list")
        {
            var addons = AddonService.Addons;
            if (settings.Json)
            {
                var json = JsonSerializer.Serialize(addons.Select(a => new { a.Name, a.ContentPath, a.GamePath, a.HasMaps }), JsonOptions);
                AnsiConsole.WriteLine(json);
            }
            else
            {
                var table = new Table().Border(TableBorder.Rounded);
                table.AddColumn("Name");
                table.AddColumn("Has Maps");
                table.AddColumn("Content Path");

                foreach (var a in addons)
                {
                    table.AddRow(a.Name, a.HasMaps ? "[green]Yes[/]" : "[grey]No[/]", a.ContentPath);
                }

                AnsiConsole.Write(table);
            }
            return Task.FromResult(0);
        }

        if (action == "info" && !string.IsNullOrWhiteSpace(settings.Name))
        {
            var addon = AddonService.Addons.FirstOrDefault(a => a.Name.Equals(settings.Name, StringComparison.OrdinalIgnoreCase));
            if (addon is null)
            {
                AnsiConsole.MarkupLine($"[red]Addon '{settings.Name}' not found.[/]");
                return Task.FromResult(1);
            }

            if (settings.Json)
            {
                var json = JsonSerializer.Serialize(new { addon.Name, addon.ContentPath, addon.GamePath, addon.HasMaps }, JsonOptions);
                AnsiConsole.WriteLine(json);
            }
            else
            {
                AnsiConsole.MarkupLine($"[bold]Addon:[/] {addon.Name}");
                AnsiConsole.MarkupLine($"[bold]Content Path:[/] {addon.ContentPath}");
                AnsiConsole.MarkupLine($"[bold]Game Path:[/] {addon.GamePath}");
                AnsiConsole.MarkupLine($"[bold]Has Maps:[/] {(addon.HasMaps ? "Yes" : "No")}");
            }
            return Task.FromResult(0);
        }

        if (action == "switch" && !string.IsNullOrWhiteSpace(settings.Name))
        {
            AddonService.SetActiveAddon(settings.Name);
            AnsiConsole.MarkupLine($"[green]Switched active addon to '{settings.Name}'.[/]");
            return Task.FromResult(0);
        }

        AnsiConsole.MarkupLine("[yellow]Unknown addon action. Valid actions: list, info <name>, switch <name>[/]");
        return Task.FromResult(1);
    }
}
