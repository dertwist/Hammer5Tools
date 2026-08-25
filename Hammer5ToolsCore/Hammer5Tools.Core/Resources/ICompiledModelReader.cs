namespace Hammer5Tools.Core.Resources;

/// <summary>Reads compiled Source 2 model, material, and texture resources.</summary>
public interface ICompiledModelReader
{
    /// <summary>Reads a model into UI-neutral primitive buffers and metadata.</summary>
    CoreResult<CompiledModel> Read(
        string resourcePath,
        string? contextAddon = null,
        int maximumTextureDimension = 1024,
        bool baseColorOnly = false,
        int skin = 0);

    /// <summary>Gets the material-group names exposed by a model.</summary>
    CoreResult<IReadOnlyList<string>> ReadMaterialGroups(string resourcePath, string? contextAddon = null);
}
