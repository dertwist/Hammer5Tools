using System.Numerics;
using Avalonia;

namespace Hammer5Tools.App.Features.SmartProps;

internal sealed class ViewportCamera
{
    public static readonly Matrix4x4 SourceToGl = new(1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1);
    public Vector3 Center { get; private set; }
    public float Distance { get; private set; } = 500;
    public float Yaw { get; private set; } = 2.3f;
    public float Pitch { get; private set; } = 0.3f;
    public Vector3 Position => Center + Distance * new Vector3(MathF.Cos(Yaw) * MathF.Cos(Pitch), MathF.Sin(Pitch), MathF.Sin(Yaw) * MathF.Cos(Pitch));
    public Matrix4x4 View => Matrix4x4.CreateLookAt(Position, Center, Vector3.UnitY);

    public Matrix4x4 Projection(double aspect)
    {
        var near = Math.Max(0.1f, Distance / 1_000);
        var far = Math.Max(10_000, Distance * 10);
        var f = 1 / MathF.Tan(MathF.PI / 6);
        return new(f / (float)Math.Max(aspect, 0.001), 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) / (near - far), -1, 0, 0, 2 * far * near / (near - far), 0);
    }

    public void Frame(IReadOnlyList<ViewportInstance> instances)
    {
        var minimum = new Vector3(float.PositiveInfinity);
        var maximum = new Vector3(float.NegativeInfinity);
        foreach (var instance in instances)
        {
            var transform = instance.Transform * SourceToGl;
            if (instance.Geometry is { } mesh)
            {
                for (var corner = 0; corner < 8; corner++)
                {
                    var point = Vector3.Transform(new((corner & 1) == 0 ? mesh.BoundsMinimum.X : mesh.BoundsMaximum.X,
                        (corner & 2) == 0 ? mesh.BoundsMinimum.Y : mesh.BoundsMaximum.Y, (corner & 4) == 0 ? mesh.BoundsMinimum.Z : mesh.BoundsMaximum.Z), transform);
                    minimum = Vector3.Min(minimum, point);
                    maximum = Vector3.Max(maximum, point);
                }
            }
            else
            {
                var point = Vector3.Transform(Vector3.Zero, transform);
                minimum = Vector3.Min(minimum, point - new Vector3(8));
                maximum = Vector3.Max(maximum, point + new Vector3(8));
            }
        }
        if (instances.Count > 0)
        {
            Center = (minimum + maximum) / 2;
            Distance = Math.Max(40, (maximum - minimum).Length() * 1.4f);
        }
    }

    public void Orbit(global::Avalonia.Vector delta)
    {
        Yaw += (float)delta.X * 0.008f;
        Pitch = Math.Clamp(Pitch + (float)delta.Y * 0.008f, -1.5f, 1.5f);
    }

    public void Pan(global::Avalonia.Vector delta)
    {
        var forward = Vector3.Normalize(Center - Position);
        var right = Vector3.Normalize(Vector3.Cross(forward, Vector3.UnitY));
        var up = Vector3.Normalize(Vector3.Cross(right, forward));
        Center += (-right * (float)delta.X + up * (float)delta.Y) * Distance * 0.0015f;
    }

    public void Look(global::Avalonia.Vector delta)
    {
        var position = Position;
        Orbit(delta);
        Center += position - Position;
    }

    public void Zoom(double delta) => Distance = Math.Clamp(Distance * MathF.Pow(0.88f, (float)delta), 2, 100_000);

    public void Move(Vector3 direction, float seconds)
    {
        var forward = Vector3.Normalize(Center - Position);
        var right = Vector3.Normalize(Vector3.Cross(forward, Vector3.UnitY));
        Center += (right * direction.X + Vector3.UnitY * direction.Y + forward * direction.Z) * Math.Max(100, Distance) * seconds;
    }

    public int? Pick(Point point, Size size, IReadOnlyList<ViewportInstance> instances)
    {
        var matrix = View * Projection(size.Width / Math.Max(1, size.Height));
        if (!Matrix4x4.Invert(matrix, out var inverse))
        {
            return null;
        }
        var x = (float)(point.X / size.Width * 2 - 1);
        var y = (float)(1 - point.Y / size.Height * 2);
        var near4 = Vector4.Transform(new Vector4(x, y, -1, 1), inverse);
        var far4 = Vector4.Transform(new Vector4(x, y, 1, 1), inverse);
        var origin = new Vector3(near4.X, near4.Y, near4.Z) / near4.W;
        var direction = Vector3.Normalize(new Vector3(far4.X, far4.Y, far4.Z) / far4.W - origin);
        var nearest = float.PositiveInfinity;
        int? selected = null;
        foreach (var instance in instances)
        {
            if (!Matrix4x4.Invert(instance.Transform * SourceToGl, out var local))
            {
                continue;
            }
            var rayOrigin = Vector3.Transform(origin, local);
            var rayDirection = Vector3.TransformNormal(direction, local);
            var min = instance.Geometry?.BoundsMinimum ?? new Vector3(-8);
            var max = instance.Geometry?.BoundsMaximum ?? new Vector3(8);
            var enter = 0f;
            var exit = float.PositiveInfinity;
            for (var axis = 0; axis < 3; axis++)
            {
                if (MathF.Abs(rayDirection[axis]) < 1e-7f)
                {
                    if (rayOrigin[axis] < min[axis] || rayOrigin[axis] > max[axis])
                    {
                        exit = -1;
                        break;
                    }
                    continue;
                }
                var a = (min[axis] - rayOrigin[axis]) / rayDirection[axis];
                var b = (max[axis] - rayOrigin[axis]) / rayDirection[axis];
                enter = Math.Max(enter, Math.Min(a, b));
                exit = Math.Min(exit, Math.Max(a, b));
            }
            if (enter <= exit && enter < nearest)
            {
                nearest = enter;
                selected = instance.ElementId;
            }
        }
        return selected;
    }
}
