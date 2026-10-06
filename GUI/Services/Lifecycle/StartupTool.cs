namespace Hammer5Tools.App.Services.Lifecycle;

public enum StartupTool : byte
{
    Main,
    SoundEvents,
    MapBuilder,
    Workshop,
    SmartProps,
}

public static class StartupArguments
{
    public static StartupTool Parse(string[] args, string? executablePath = null)
    {
        if (args.Length == 0)
        {
            return Path.GetFileNameWithoutExtension(executablePath ?? Environment.ProcessPath)?.ToLowerInvariant() switch
            {
                "soundeventeditor" => StartupTool.SoundEvents,
                "mapbuilder" => StartupTool.MapBuilder,
                "smartpropeditor" => StartupTool.SmartProps,
                "workshopmanager" => StartupTool.Workshop,
                _ => StartupTool.Main,
            };
        }

        if (args.Length != 2 || args[0] != "--tool")
        {
            throw new ArgumentException("Use --tool soundevents, mapbuilder, smartprops or workshop.");
        }

        return args[1].ToLowerInvariant() switch
        {
            "soundevents" => StartupTool.SoundEvents,
            "mapbuilder" => StartupTool.MapBuilder,
            "workshop" => StartupTool.Workshop,
            "smartprops" => StartupTool.SmartProps,
            _ => throw new ArgumentException($"Unknown tool '{args[1]}'. Choose soundevents, mapbuilder, smartprops or workshop."),
        };
    }
}
