namespace Hammer5Tools.Core.Resources;

/// <summary>
/// Describes one file in a mounted VPK archive.
/// </summary>
public sealed record VpkEntry(string Path, long Size);
