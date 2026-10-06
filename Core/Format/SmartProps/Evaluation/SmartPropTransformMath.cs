namespace Hammer5Tools.Core.Format.SmartProps.Evaluation;

internal static class SmartPropTransformMath
{
    public static Matrix4x4 EulerAnglesToRotationMatrix(Vector3 pitchYawRoll)
        => EulerAnglesToRotationMatrixRadians(Vector3.DegreesToRadians(pitchYawRoll));

    public static Matrix4x4 EulerAnglesToRotationMatrixRadians(Vector3 pitchYawRoll)
    {
        var rollMatrix = Matrix4x4.CreateRotationX(pitchYawRoll.Z);
        var pitchMatrix = Matrix4x4.CreateRotationY(pitchYawRoll.X);
        var yawMatrix = Matrix4x4.CreateRotationZ(pitchYawRoll.Y);

        return rollMatrix * pitchMatrix * yawMatrix;
    }

    public static Vector3 ToEulerAngles(Quaternion rotation)
    {
        var forwardX = 1 - 2 * (rotation.Y * rotation.Y + rotation.Z * rotation.Z);
        var forwardY = 2 * (rotation.X * rotation.Y + rotation.W * rotation.Z);
        var forwardZ = 2 * (rotation.X * rotation.Z - rotation.W * rotation.Y);

        var xyDist = MathF.Sqrt(forwardX * forwardX + forwardY * forwardY);

        Vector3 angles = new();
        angles.X = MathF.Atan2(-forwardZ, xyDist);

        if (xyDist > 0.001f)
        {
            var leftZ = 2 * (rotation.Y * rotation.Z + rotation.W * rotation.X);
            var upZ = 1 - 2 * (rotation.X * rotation.X + rotation.Y * rotation.Y);
            angles.Y = MathF.Atan2(forwardY, forwardX);
            angles.Z = MathF.Atan2(leftZ, upZ);
        }
        else
        {
            var leftX = 2 * (rotation.X * rotation.Y - rotation.W * rotation.Z);
            var leftY = 1 - 2 * (rotation.X * rotation.X + rotation.Z * rotation.Z);
            angles.Y = MathF.Atan2(-leftX, leftY);
            angles.Z = 0;
        }

        return Vector3.RadiansToDegrees(angles);
    }

    internal static (Vector3 Position, Vector3 PitchYawRoll, Vector3 Scale) DecomposeTransformationMatrix(Matrix4x4 matrix)
    {
        if (!Matrix4x4.Decompose(matrix, out var scale, out var rotation, out var position))
        {
            return (matrix.Translation, Vector3.Zero, Vector3.One);
        }

        return (position, ToEulerAngles(rotation), scale);
    }

    public static Vector3 CubicBezier(Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3, float t)
    {
        var u = 1.0f - t;
        var uu = u * u;
        var tt = t * t;
        return (uu * u * p0) + (3.0f * uu * t * p1) + (3.0f * u * tt * p2) + (tt * t * p3);
    }
}
