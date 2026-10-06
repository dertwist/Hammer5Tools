namespace Hammer5Tools.Core.Tests.MapBuilder;

using Hammer5Tools.Core.MapBuilder;

public class MapBuildOptionsTests
{
    [Test]
    public async Task EntitiesOnlySuppressesWorldAndLightingAndAutoThreadsAreResolved()
    {
        var options = new MapBuildOptions { EntitiesOnly = true, BakeLighting = true };
        var arguments = options.ToArguments(12);
        await Assert.That(arguments).Contains("-threads 12");
        await Assert.That(arguments).Contains("-entities");
        await Assert.That(arguments).Contains("-nolightmaps");
        await Assert.That(arguments.Contains("-world") || arguments.Contains("-bakelighting")).IsFalse();
    }

    [Test]
    public async Task LightingAndAudioControlsReachCompilerFlags()
    {
        var options = new MapBuildOptions
        {
            BakeLighting = true,
            LightmapResolution = 2048,
            LightmapQuality = 1,
            NoiseRemoval = false,
            LightmapCompression = false,
            BuildReverb = true,
            AudioThreads = 4,
            BuildNavigation = true,
            DebugNavigation = true
        };
        var arguments = options.ToArguments(8);
        await Assert.That(arguments).Contains("-lightmapMaxResolution 2048 -lightmapVRadQuality 1");
        await Assert.That(arguments).Contains("-lightmapDisableFiltering");
        await Assert.That(arguments).Contains("-lightmapCompressionDisabled");
        await Assert.That(arguments).Contains("-sareverb -sareverb_threads 4");
        await Assert.That(arguments).Contains("-navdbg");
    }
}
