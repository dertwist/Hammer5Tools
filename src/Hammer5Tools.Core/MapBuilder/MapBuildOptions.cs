namespace Hammer5Tools.Core.MapBuilder;

/// <summary>Editable map compiler settings corresponding to the legacy Map Builder.</summary>
public sealed record MapBuildOptions
{
    public int Threads { get; set; } = -1;
    public bool SaveMapPath { get; set; }
    public bool SaveBuildLogs { get; set; }
    public bool ClearVradCache { get; set; }
    public bool Quiet { get; set; } = true;
    public bool BuildWorld { get; set; } = true;
    public bool EntitiesOnly { get; set; }
    public bool NoSettle { get; set; }
    public bool BakeLighting { get; set; }
    public int LightmapResolution { get; set; } = 512;
    public int LightmapQuality { get; set; } = 2;
    public bool LightmapCompression { get; set; } = true;
    public bool NoiseRemoval { get; set; } = true;
    public bool NoLightCalculations { get; set; }
    public bool LargeBlockSize { get; set; }
    public bool BuildPhysics { get; set; }
    public bool LegacyCollisionMesh { get; set; }
    public bool BuildVisibility { get; set; }
    public bool DebugVisibility { get; set; }
    public bool BuildNavigation { get; set; }
    public bool DebugNavigation { get; set; }
    public bool GridNavigation { get; set; }
    public bool BuildReverb { get; set; }
    public bool BuildAudioPaths { get; set; }
    public bool BakeCustomAudio { get; set; }
    public int AudioThreads { get; set; } = -1;
    public bool LaunchAfterBuild { get; set; } = true;
    public bool BuildCubemaps { get; set; }

    /// <summary>Builds compiler flags without input paths or executable arguments.</summary>
    public string ToArguments(int processorCount)
    {
        if (Threads is < -1 or 0 || AudioThreads is < -1 or 0 || LightmapQuality is < 0 or > 3
            || LightmapResolution is not (256 or 512 or 1024 or 2048 or 4096 or 8192))
        {
            throw new InvalidOperationException("Invalid map build settings.");
        }

        var threads = Threads > 0 ? Threads : Math.Max(1, processorCount);
        var audioThreads = AudioThreads > 0 ? AudioThreads : threads;
        var flags = new List<string>
        {
            $"-threads {threads}", "-fshallow", "-maxtextureres 256", "-dxlevel 110", "-unbufferedio", "-noassert"
        };
        if (Quiet)
        {
            flags.Add("-quiet");
        }
        if (EntitiesOnly)
        {
            flags.Add("-entities");
        }
        else if (BuildWorld)
        {
            flags.Add("-world");
        }

        if (NoSettle)

        {

            flags.Add("-nosettle");

        }
        if (BakeLighting && !EntitiesOnly)
        {
            flags.Add($"-bakelighting -lightmapMaxResolution {LightmapResolution} -lightmapVRadQuality {LightmapQuality}");
            if (!NoiseRemoval)
            {
                flags.Add("-lightmapDisableFiltering");
            }
            if (!LightmapCompression)
            {
                flags.Add("-lightmapCompressionDisabled");
            }
            if (NoLightCalculations)
            {
                flags.Add("-disableLightingCalculations");
            }
            if (LargeBlockSize)
            {
                flags.Add("-vrad3LargeBlockSize");
            }
        }
        else
        {
            flags.Add("-nolightmaps");
        }

        if (BuildPhysics)
        {
            flags.Add("-phys");
            if (LegacyCollisionMesh)
            {
                flags.Add("-legacycompilecollisionmesh");
            }
        }
        if (BuildVisibility)
        {
            flags.Add("-vis");
        }
        if (DebugVisibility)
        {
            flags.Add("-debugvisgeo");
        }
        flags.Add("-html");
        if (BuildNavigation)
        {
            flags.Add("-nav");
            if (DebugNavigation)
            {
                flags.Add("-navdbg");
            }
            if (GridNavigation)
            {
                flags.Add("-gridnav");
            }
        }
        if (BuildReverb)
        {
            flags.Add($"-sareverb -sareverb_threads {audioThreads}");
        }
        if (BuildAudioPaths)
        {
            flags.Add($"-sapaths -sapaths_threads {audioThreads}");
        }
        if (BakeCustomAudio)
        {
            flags.Add($"-sacustomdata -sacustomdata_threads {audioThreads}");
        }
        flags.Add("-retail -breakpad -nop4");
        return string.Join(' ', flags);
    }
}
