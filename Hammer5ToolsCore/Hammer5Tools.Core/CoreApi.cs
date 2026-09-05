namespace Hammer5Tools.Core;

/// <summary>
/// Identifies the versioned public contract exposed by Hammer5Tools Core.
/// </summary>
public static class CoreApi
{
    /// <summary>
    /// Gets the version understood by GUI bridge clients.
    /// </summary>
    public static Version Version { get; } = new(2, 0);

    /// <summary>
    /// Verifies that the public Core contract can be invoked by a client.
    /// </summary>
    public static CoreResult<Version> Probe() => CoreResult.Success(Version);

    /// <summary>Groups a source filename using affixes appropriate to its file type.</summary>
    public static string NormalizeAssetGroupName(string baseName, string sourceExtension = "", int algorithm = 0) =>
        Format.AssetGroup.AssetGroupTemplate.NormalizeName(baseName, sourceExtension, algorithm);

    /// <summary>Expands Assetgroup template tokens and conditionals from a JSON request.</summary>
    public static string RenderAssetGroupTemplate(string requestJson) =>
        Format.AssetGroup.AssetGroupTemplate.Render(requestJson);
}
