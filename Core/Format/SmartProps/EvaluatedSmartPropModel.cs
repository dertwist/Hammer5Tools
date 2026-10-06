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
/// <param name="MaterialTints">
/// Per-material tints from <c>CSmartPropOperation_MaterialTint</c>, applied on top of
/// <paramref name="TintColor"/> to matching submeshes only. Empty when the model has none.
/// </param>
/// <param name="MaterialOverrides">
/// Material substitutions from <c>CSmartPropOperation_MaterialOverride</c>, applied before
/// <paramref name="MaterialTints"/> matches. Empty when the model has none.
/// </param>
public sealed record EvaluatedSmartPropModel(
    int ElementId,
    string ModelName,
    Matrix4x4 Transform,
    string? MaterialGroup,
    Vector4? TintColor,
    EvaluatedSmartPropDeformer? Deformer = null,
    IReadOnlyList<EvaluatedSmartPropMaterialTint>? MaterialTints = null,
    IReadOnlyList<EvaluatedSmartPropMaterialReplacement>? MaterialOverrides = null);
