namespace SourcePorter.Core.Domain;

/// <summary>
/// A single map-porting project. Captures the four paths and two names that
/// Valve's <c>import_map_community</c> needs, plus the options that drive the
/// rest of the pipeline. Serialised to <c>sourceporter.json</c> next to the addon.
/// </summary>
public sealed class PortProject
{
    /// <summary>Folder containing CS:GO's <c>gameinfo.txt</c> (compiled S1 content root).</summary>
    public string S1GameInfoDir { get; set; } = "";

    /// <summary>CS:GO uncompiled source content (<c>sdk_content</c>: .smd/.dmx/.qc/.tga/.psd).</summary>
    public string S1ContentDir { get; set; } = "";

    /// <summary>Folder containing CS2's <c>gameinfo.gi</c> (usually <c>game/csgo</c>).</summary>
    public string S2GameInfoDir { get; set; } = "";

    /// <summary>Target CS2 Workshop addon name (under <c>csgo_addons</c>).</summary>
    public string AddonName { get; set; } = "";

    /// <summary>Map name relative to <c>maps\</c>, without extension (e.g. <c>ze_example</c>).</summary>
    public string MapName { get; set; } = "";

    public ImportOptions Import { get; set; } = new();
}
