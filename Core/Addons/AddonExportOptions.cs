namespace Hammer5Tools.Core.Addons;

using System.IO.Compression;

/// <summary>File filters and compression for an addon archive.</summary>
public sealed class AddonExportOptions
{
    public bool SkipNonDefaultContentFolders { get; set; }
    public bool IncludeCompiledMaps { get; set; } = true;
    public bool IncludeCompiledMaterials { get; set; } = true;
    public bool IncludeCompiledModels { get; set; } = true;
    public bool IgnoreVersionControl { get; set; } = true;
    public bool IncludeOtherCompiledFolders { get; set; }
    public bool IncludeThumbnailCache { get; set; }
    public string IgnoredExtensions { get; set; } = ".bak, .bin, .los";
    public CompressionLevel Compression { get; set; } = CompressionLevel.Optimal;
    public IReadOnlySet<string>? SelectedFiles { get; set; }
}

/// <summary>A file eligible for export, identified by its archive-relative path.</summary>
public sealed record AddonExportFile(string SourcePath, string ArchivePath, long Size);
