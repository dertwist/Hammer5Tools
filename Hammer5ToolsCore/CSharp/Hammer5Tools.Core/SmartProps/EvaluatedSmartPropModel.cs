namespace Hammer5Tools.Core.SmartProps;

/// <summary>
/// Describes one model produced by SmartProp evaluation.
/// </summary>
public sealed record EvaluatedSmartPropModel(
    int ElementId,
    string ModelName,
    Matrix4x4 Transform,
    string? MaterialGroup,
    Vector4? TintColor);
