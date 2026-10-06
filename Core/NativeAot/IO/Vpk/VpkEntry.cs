namespace Hammer5Tools.Core.IO.Vpk;

/// <summary>
/// Describes one file in a mounted VPK archive.
/// </summary>
public sealed record VpkEntry(string Path, long Size);
