namespace SourcePorter.Core.Materials;

/// <summary>
/// File-level façade over <see cref="VmtFile"/> + <see cref="VmtToVmatConverter"/>: reads a
/// Source 1 <c>.vmt</c> from disk and writes the converted Source 2 <c>.vmat</c>, resolving
/// <c>include</c>/<c>patch</c> references relative to a content root. This is the non-binary
/// entry point the missing-asset repair path can call instead of shelling out to
/// <c>source1import.exe</c>.
/// </summary>
public static class MaterialConverter
{
    /// <summary>
    /// Converts <paramref name="vmtPath"/> to <c>.vmat</c> text. When <paramref name="contentRoot"/>
    /// is supplied, <c>patch</c> includes are resolved beneath it.
    /// </summary>
    public static string ConvertText(string vmtPath, string? contentRoot = null)
    {
        var resolver = contentRoot is null ? null : MakeIncludeResolver(contentRoot);
        var vmt = VmtFile.Load(vmtPath, resolver);
        var vmat = new VmtToVmatConverter().Convert(vmt);
        return vmat.ToText(Path.GetFileName(vmtPath));
    }

    /// <summary>Converts a <c>.vmt</c> on disk and writes the <c>.vmat</c> next to <paramref name="outVmatPath"/>.</summary>
    public static void ConvertFile(string vmtPath, string outVmatPath, string? contentRoot = null)
    {
        var text = ConvertText(vmtPath, contentRoot);
        var dir = Path.GetDirectoryName(outVmatPath);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);
        File.WriteAllText(outVmatPath, text);
    }

    /// <summary>
    /// Reads the pixel dimensions of a material's base texture by locating its <c>.vtf</c> under
    /// <paramref name="contentRoot"/> — the building block for correcting custom brush-material UV
    /// scale that Valve's <c>source1import</c> defaults when it can't open the file
    /// (<c>GetMappingDimensionsForVMT: can't open …</c>). Returns null if the texture can't be found.
    /// </summary>
    public static (int Width, int Height)? TryReadBaseTextureDimensions(string vmtPath, string contentRoot)
    {
        var vmt = VmtFile.Load(vmtPath, MakeIncludeResolver(contentRoot));
        var basePath = vmt["$basetexture"];
        if (string.IsNullOrWhiteSpace(basePath))
            return null;

        var vtf = Path.Combine(contentRoot, "materials",
            basePath.Replace('\\', '/').TrimStart('/').Replace('/', Path.DirectorySeparatorChar) + ".vtf");
        return VtfHeader.TryReadDimensions(vtf);
    }

    private static Func<string, string?> MakeIncludeResolver(string contentRoot)
        => includePath =>
        {
            var rel = includePath.Replace('\\', '/').TrimStart('/');
            var full = Path.Combine(contentRoot, rel.Replace('/', Path.DirectorySeparatorChar));
            return File.Exists(full) ? File.ReadAllText(full) : null;
        };
}
