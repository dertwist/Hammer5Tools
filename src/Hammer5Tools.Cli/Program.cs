namespace Hammer5Tools.Cli;

using Spectre.Console.Cli;

public static class Program
{
    public static int Main(string[] args)
    {
        var app = new CommandApp();
        app.Configure(config =>
        {
            config.SetApplicationName("h5t");
        });

        return app.Run(args);
    }
}
