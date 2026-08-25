namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Describes one model produced by SmartProp evaluation.
/// </summary>
/// <param name="Deformer">
/// Set when this model sits under an active deformer and hasn't opted out of mesh-level
/// deformation (see <see cref="EvaluatedSmartPropDeformer"/>); <paramref name="Transform"/> is
/// then the model's undeformed placement, and the mesh itself should be warped through the cage.
/// Null for a rigidly-deformed (or undeformed) model, where the bend is already baked into
/// <paramref name="Transform"/>.
/// </param>
public sealed record EvaluatedSmartPropModel(
    int ElementId,
    string ModelName,
    Matrix4x4 Transform,
    string? MaterialGroup,
    Vector4? TintColor,
    EvaluatedSmartPropDeformer? Deformer = null);
