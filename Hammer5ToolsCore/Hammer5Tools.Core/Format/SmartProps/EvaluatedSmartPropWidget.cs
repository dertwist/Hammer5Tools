using System.Numerics;

namespace Hammer5Tools.Core.Format.SmartProps;

/// <summary>
/// Describes one editor preview widget placed by SmartProp evaluation.
/// </summary>
public sealed record EvaluatedSmartPropWidget(
    string Type,
    int ElementId,
    Matrix4x4 Transform,
    Vector3 Offset,
    Vector3 MinimumBounds,
    Vector3 MaximumBounds,
    Vector3 Axis,
    Vector3 Color,
    IReadOnlyList<bool> Handles,
    IReadOnlyList<bool> ActiveAxes,
    float Scale,
    float Radius,
    float Angle,
    float Size,
    string Shape,
    string Name);
