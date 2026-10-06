namespace Hammer5Tools.Core.Format.SmartProps.Evaluation;

/// <summary>
/// Transform helpers for smart prop evaluation. Matrices follow the repo wide Source 2
/// convention: they are row-vector transforms stored directly in <see cref="Matrix4x4"/>,
/// so a rotation's rows are the forward, left and up basis vectors and the translation
/// is the bottom row (M41, M42, M43). Child transforms compose into world space as
/// local * parent.
/// </summary>
internal static class SmartPropTransform
{
    /// <summary>
    /// Builds a frame matrix for a position and forward tangent. The up reference
    /// picks the roll: left = up x forward, and up is re-orthogonalized as
    /// forward x left. Nearly collinear forward/up pairs fall back to a stable
    /// alternative up so the frame never degenerates.
    /// </summary>
    public static Matrix4x4 CreateFrame(Vector3 position, Vector3 forward, Vector3? up = null)
    {
        var f = forward.LengthSquared() > 1e-14f ? Vector3.Normalize(forward) : Vector3.UnitX;

        var u = up is { } upValue
            ? (upValue.LengthSquared() > 1e-14f ? Vector3.Normalize(upValue) : Vector3.UnitZ)
            : Vector3.UnitZ;

        if (MathF.Abs(Vector3.Dot(f, u)) > 0.999f)
        {
            u = MathF.Abs(f.Y) < 0.9f ? Vector3.UnitY : Vector3.UnitX;
        }

        var l = Vector3.Cross(u, f);
        l = l.LengthSquared() > 1e-14f ? Vector3.Normalize(l) : Vector3.UnitY;

        var uOrtho = Vector3.Cross(f, l);
        uOrtho = uOrtho.LengthSquared() > 1e-14f ? Vector3.Normalize(uOrtho) : Vector3.UnitZ;

        return new Matrix4x4(
            f.X, f.Y, f.Z, 0f,
            l.X, l.Y, l.Z, 0f,
            uOrtho.X, uOrtho.Y, uOrtho.Z, 0f,
            position.X, position.Y, position.Z, 1f);
    }

    /// <summary>
    /// Decomposes a row-vector TRS matrix into position, Euler angles in degrees
    /// (pitch, yaw, roll) and per-axis scale. Yaw and roll are wrapped to 0..360.
    /// Handles the gimbal lock cases where pitch is near +/-90 degrees.
    /// </summary>
    public static (Vector3 Position, Vector3 PitchYawRoll, Vector3 Scale) DecomposeTRS(Matrix4x4 matrix)
        => SmartPropTransformMath.DecomposeTransformationMatrix(matrix);

    /// <summary>
    /// Applies a path offset to a frame matrix. World space offsets shift the
    /// translation along the world axes; local space offsets shift along the frame's
    /// left axis by X and up axis by Y.
    /// </summary>
    public static Matrix4x4 ApplyPathOffset(Matrix4x4 matrix, Vector3 pathOffset, bool worldSpace)
    {
        if (pathOffset.LengthSquared() < 1e-12f)
        {
            return matrix;
        }

        if (worldSpace)
        {
            matrix.M41 += pathOffset.X;
            matrix.M42 += pathOffset.Y;
            matrix.M43 += pathOffset.Z;
            return matrix;
        }

        var left = new Vector3(matrix.M21, matrix.M22, matrix.M23);
        var up = new Vector3(matrix.M31, matrix.M32, matrix.M33);
        var shift = (left * pathOffset.X) + (up * pathOffset.Y);

        matrix.M41 += shift.X;
        matrix.M42 += shift.Y;
        matrix.M43 += shift.Z;
        return matrix;
    }

    /// <summary>
    /// Transforms a point by a row-vector matrix: point * matrix. Equivalent to
    /// <see cref="Vector3.Transform(Vector3, Matrix4x4)"/>, spelled out because the
    /// row-vector storage convention makes that equivalence non-obvious.
    /// </summary>
    public static Vector3 TransformPoint(Matrix4x4 matrix, Vector3 point) => Vector3.Transform(point, matrix);
}
