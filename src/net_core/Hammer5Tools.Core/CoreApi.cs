namespace Hammer5Tools.Core;

/// <summary>
/// Identifies the versioned public contract exposed by Hammer5Tools Core.
/// </summary>
public static class CoreApi
{
    /// <summary>
    /// Gets the version understood by GUI bridge clients.
    /// </summary>
    public static Version Version { get; } = new(1, 0);
}
