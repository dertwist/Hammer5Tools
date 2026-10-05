namespace Hammer5Tools.App.Services.Lifecycle;

public enum StartupTool : byte
{
    Main,
    SoundEvents,
    MapBuilder,
    Workshop,
}

public static class StartupArguments
{
    public static StartupTool Parse(string[] args)
    {
        if (args.Length == 0)
        {
            return StartupTool.Main;
        }

        if (args.Length != 2 || args[0] != "--tool")
        {
            throw new ArgumentException("Use --tool soundevents, --tool mapbuilder or --tool workshop.");
        }

        return args[1].ToLowerInvariant() switch
        {
            "soundevents" => StartupTool.SoundEvents,
            "mapbuilder" => StartupTool.MapBuilder,
            "workshop" => StartupTool.Workshop,
            _ => throw new ArgumentException($"Unknown tool '{args[1]}'. Choose soundevents, mapbuilder or workshop."),
        };
    }
}
