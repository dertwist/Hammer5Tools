namespace Hammer5Tools.Core.MapBuilder;

/// <summary>A named Map Builder preset with independently editable settings.</summary>
public sealed record MapBuildConfiguration(string Name, MapBuildOptions Options, string[] Maps)
{
    /// <summary>Creates fresh copies of the four baseline presets.</summary>
    public static MapBuildConfiguration[] CreateDefaults() =>
    [
        new("Fast Compile", new(), []),
        new("Full Compile", new() { Quiet = false, BakeLighting = true, BuildPhysics = true, BuildVisibility = true, BuildNavigation = true }, []),
        new("Lighting Only", new() { BakeLighting = true, LightmapQuality = 3 }, []),
        new("Entities Only", new() { BuildWorld = false, EntitiesOnly = true }, []),
    ];
}
