namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// A lattice cage a model's own mesh should be warped through, in place of moving its instance
/// transform, for models placed under a deformer that don't opt out via
/// <c>Model.m_bRigidDeformation</c> or an enabled <c>CSmartPropOperation_RigidDeformation</c>
/// modifier (Valve's own "only the transform changes, not the mesh" escape hatch — see
/// <see cref="SmartPropBendDeformerEvaluator"/>'s remarks). Shaped to match what CS2 itself bakes
/// into a compiled VMAP's SmartProp deformation data, so a consumer with access to the model's
/// mesh (the GUI's OpenGL viewport; Core has no mesh data of its own) can warp vertex positions
/// the same way: <c>vertex * DeformerFrame⁻¹ * VolumeFrame⁻¹</c> to reach cage-local space, a
/// trilinear blend of the four <c>ControlPoints</c>/<c>Midpoints</c> Bezier edges along X/Y/Z,
/// then back out through <c>VolumeFrame * DeformerFrame</c>.
/// </summary>
/// <param name="Size">Size of the undeformed lattice, in the deformer's own local space.</param>
/// <param name="ControlPoints">The 8 deformed lattice corner positions.</param>
/// <param name="Midpoints">The 2 Bezier curve handles for each of the 4 local-X edges.</param>
/// <param name="DeformerFrame">The deformer element's own accumulated world transform.</param>
/// <param name="VolumeFrame">Where the lattice's base volume sits within the deformer's local space.</param>
public sealed record EvaluatedSmartPropDeformer(
    Vector3 Size,
    IReadOnlyList<Vector3> ControlPoints,
    IReadOnlyList<Vector3> Midpoints,
    Matrix4x4 DeformerFrame,
    Matrix4x4 VolumeFrame);
