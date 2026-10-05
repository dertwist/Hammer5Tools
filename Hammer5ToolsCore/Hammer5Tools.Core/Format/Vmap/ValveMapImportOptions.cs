namespace Hammer5Tools.Core.Format.Vmap;

/// <summary>Controls DCC import work while preserving the default full scene projection.</summary>
public sealed record ValveMapImportOptions
{
    /// <summary>Expands nested VMAP prefab instances.</summary>
    public bool ExpandPrefabs { get; init; } = true;
    /// <summary>Deserializes and evaluates referenced SmartProps.</summary>
    public bool EvaluateSmartProps { get; init; } = true;
    /// <summary>Includes geometry from hidden editor nodes.</summary>
    public bool IncludeHidden { get; init; } = true;
    /// <summary>Skips VMAP mesh objects whose used faces all have tool materials.</summary>
    public bool IgnoreToolMaterialObjects { get; init; }
    /// <summary>Skips static overlay/decal objects during DCC import.</summary>
    public bool IgnoreStaticOverlays { get; init; }
    /// <summary>Returns the hierarchy and selection catalog without mesh or model evaluation.</summary>
    public bool MetadataOnly { get; init; }
    /// <summary>Selection catalog keys mapped to 0 (Hammer), 1 (enabled), or 2 (disabled).</summary>
    public IReadOnlyDictionary<string, int> SelectionSetOverrides { get; init; } = new Dictionary<string, int>();
    /// <summary>Retains full raw mesh streams and editor metadata.</summary>
    public bool IncludeEditorMetadata { get; init; } = true;
    /// <summary>Semicolon-separated selection-set names or wildcard patterns; empty imports all.</summary>
    public string SelectionSetMask { get; init; } = "";
    /// <summary>Excludes matching sets instead of keeping them.</summary>
    public bool InvertSelectionSetMask { get; init; }
    /// <summary>Source 2 game directory for compiled SmartProp and VPK dependencies.</summary>
    public string GameDirectory { get; init; } = "";
    /// <summary>Addon used to resolve compiled dependencies.</summary>
    public string ActiveAddon { get; init; } = "";
}
