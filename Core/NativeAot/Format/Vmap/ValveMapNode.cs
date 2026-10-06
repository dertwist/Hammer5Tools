namespace Hammer5Tools.Core.Format.Vmap;

/// <summary>
/// Describes one node in an uncompiled Valve map.
/// </summary>
public sealed record ValveMapNode(
    string Name,
    string ClassName,
    IReadOnlyDictionary<string, string> Properties,
    IReadOnlyList<ValveMapNode> Children);
