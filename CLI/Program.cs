namespace Hammer5Tools.Cli;

using Hammer5Tools.Cli.Commands;
using Hammer5Tools.Core;
using Hammer5Tools.Core.IO.Commands;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Spectre.Console.Cli;

public static class Program
{
    public static int Main(string[] args)
    {
        if (args.Length == 1 && args[0] == CommandPipeHost.StartupArgument)
        {
            CommandPipeHost.Run();
            return 0;
        }

        var services = new ServiceCollection();
        services.AddLogging(builder => builder.AddConsole().SetMinimumLevel(LogLevel.Warning));
        services.AddHammer5ToolsCore();

        var registrar = new TypeRegistrar(services);
        var app = new CommandApp(registrar);

        app.Configure(config =>
        {
            config.SetApplicationName("h5t");
            config.AddCommand<AddonCommand>("addon")
                .WithDescription("Query and manage Counter-Strike 2 addons");
            config.AddCommand<CompileCommand>("compile")
                .WithDescription("Compile assets or maps headlessly");
            config.AddCommand<SyncCommand>("sync")
                .WithDescription("Git sync operations for addons");
            config.AddCommand<SoundCommand>("sound")
                .WithDescription("Query VPK sound assets or soundevent documents");
            config.AddCommand<Cs2Command>("cs2")
                .WithDescription("Control Counter-Strike 2 Workshop Tools process");
        });

        return app.Run(args);
    }
}
