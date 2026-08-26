namespace Hammer5Tools.Core.Format.Vmap;

/// <summary>
/// Contains a read-only projection of an uncompiled Valve map.
/// </summary>
public sealed record ValveMapDocument(
    string Path,
    ValveMapNode World,
    IReadOnlyList<ValveMapNode> Nodes,
    IReadOnlyList<ValveMapEntity> Entities,
    IReadOnlyList<string> AssetReferences,
    IReadOnlyList<byte>? Thumbnail,
    string? ThumbnailFormat);
