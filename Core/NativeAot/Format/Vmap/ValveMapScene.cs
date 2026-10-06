using System.Collections.Immutable;

namespace Hammer5Tools.Core.Format.Vmap;

/// <summary>One contiguous index range of a <see cref="ValveMapSceneMesh"/> sharing a material.</summary>
public sealed record ValveMapSceneSubMesh(int IndexOffset, int IndexCount, string Material);

/// <summary>
/// A triangulated brush/displacement mesh, already baked into world space so the
/// viewer draws it with an identity transform.
/// </summary>
public sealed record ValveMapSceneMesh(
    string Name,
    ImmutableArray<float> Positions,
    ImmutableArray<float> Normals,
    ImmutableArray<float> TextureCoordinates,
    ImmutableArray<uint> Indices,
    ImmutableArray<ValveMapSceneSubMesh> SubMeshes);

/// <summary>A model placement (prop_static and every other entity carrying a <c>model</c> key).</summary>
public sealed record ValveMapSceneProp(
    string Name,
    string ClassName,
    string Model,
    ImmutableArray<float> Transform);

/// <summary>
/// A <c>CMapSmartProp</c> placement: the referenced <c>.vsmart</c>, its world transform, and the
/// per-placement parameter overrides Hammer stores under <c>nodeData</c>.
/// </summary>
public sealed record ValveMapSceneSmartProp(
    string Name,
    string File,
    ImmutableArray<float> Transform,
    IReadOnlyDictionary<string, object?> Variables);

/// <summary>Vmap reading experiments: the renderable projection of an uncompiled VMAP.</summary>
public sealed record ValveMapScene(
    string Path,
    ImmutableArray<ValveMapSceneMesh> Meshes,
    ImmutableArray<ValveMapSceneProp> Props,
    ImmutableArray<ValveMapSceneSmartProp> SmartProps,
    ImmutableArray<string> Diagnostics);
