namespace Hammer5Tools.Core.Format.Resources;

/// <summary>A contiguous model index range sharing one material.</summary>
public sealed record CompiledSubMesh(int IndexOffset, int IndexCount, CompiledMaterial Material);
