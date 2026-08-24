using System.Collections.Immutable;

namespace Hammer5Tools.Core.Resources;

/// <summary>Immutable primitive mesh buffers decoded from compiled Source 2 resources.</summary>
public sealed record CompiledModel(
    ImmutableArray<float> Vertices,
    ImmutableArray<float> Normals,
    ImmutableArray<float> Uvs,
    ImmutableArray<uint> Indices,
    Vector3 BoundsMinimum,
    Vector3 BoundsMaximum,
    ImmutableArray<CompiledSubMesh> SubMeshes,
    ImmutableArray<CoreDiagnostic> Diagnostics);
