namespace Hammer5Tools.Core.Compiler;

/// <summary>
/// Service wrapping Valve's resourcecompiler.exe for compiling Source 2 assets.
/// </summary>
public interface IResourceCompiler
{
    /// <summary>
    /// Gets whether resourcecompiler.exe is available and found in the CS2 installation.
    /// </summary>
    bool IsAvailable { get; }

    /// <summary>
    /// Compiles a single source asset file.
    /// </summary>
    Task<CompileResult> CompileAssetAsync(string assetFilePath, string? addonName = null, CancellationToken ct = default);

    /// <summary>Compiles a source asset with additional map-build flags.</summary>
    Task<CompileResult> CompileAssetAsync(string assetFilePath, string? addonName, string? additionalArguments, CancellationToken ct = default);

    /// <summary>Compiles a map while reporting output lines as they arrive.</summary>
    async Task<CompileResult> CompileAssetAsync(string assetFilePath, string? addonName, string? additionalArguments, Action<string> output, CancellationToken ct = default)
    {
        var result = await CompileAssetAsync(assetFilePath, addonName, additionalArguments, ct);
        foreach (var line in (result.StandardOutput + "\n" + result.StandardError).Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries))
        {
            output(line);
        }
        return result;
    }

    /// <summary>
    /// Recursively compiles all assets within a directory.
    /// </summary>
    Task<CompileResult> CompileFolderAsync(string folderPath, string? addonName = null, CancellationToken ct = default);

    /// <summary>
    /// Generates a basic VMDL file wrapping a mesh (e.g. .fbx, .obj) and compiles it.
    /// </summary>
    Task<CompileResult> QuickCreateVmdlAsync(string meshFilePath, string? addonName = null, CancellationToken ct = default);
}
