namespace Hammer5Tools.Core.Format.Vmap;

/// <summary>
/// Describes one entity projected from an uncompiled Valve map.
/// </summary>
public sealed record ValveMapEntity(
    string ClassName,
    string? Origin,
    string? Angles,
    IReadOnlyDictionary<string, string> Properties);
