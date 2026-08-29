using System.Numerics;

using Datamodel;

namespace Hammer5Tools.Core.Format.Vmap;

/// <summary>Compact binary transport for the VMAP viewer's flattened scene projection.</summary>
internal static class ValveMapSceneBinarySerializer
{
    private enum ScalarType : byte
    {
        Null,
        Boolean,
        String,
        Single,
        Int32,
        Vector2,
        Vector3,
    }

    public static void Write(NativeBinaryWriter writer, ValveMapScene scene)
    {
        ArgumentNullException.ThrowIfNull(writer);
        ArgumentNullException.ThrowIfNull(scene);

        writer.WriteString(scene.Path);
        writer.WriteInt32(scene.Meshes.Length);
        foreach (var mesh in scene.Meshes)
        {
            writer.WriteString(mesh.Name);
            writer.WriteSingles(mesh.Positions.AsSpan());
            writer.WriteSingles(mesh.Normals.AsSpan());
            writer.WriteSingles(mesh.TextureCoordinates.AsSpan());
            writer.WriteUInt32s(mesh.Indices.AsSpan());
            writer.WriteInt32(mesh.SubMeshes.Length);
            foreach (var subMesh in mesh.SubMeshes)
            {
                writer.WriteInt32(subMesh.IndexOffset);
                writer.WriteInt32(subMesh.IndexCount);
                writer.WriteString(subMesh.Material);
            }
        }

        writer.WriteInt32(scene.Props.Length);
        foreach (var prop in scene.Props)
        {
            writer.WriteString(prop.Name);
            writer.WriteString(prop.ClassName);
            writer.WriteString(prop.Model);
            writer.WriteSingles(prop.Transform.AsSpan());
        }

        writer.WriteInt32(scene.SmartProps.Length);
        foreach (var smartProp in scene.SmartProps)
        {
            writer.WriteString(smartProp.Name);
            writer.WriteString(smartProp.File);
            writer.WriteSingles(smartProp.Transform.AsSpan());
            writer.WriteInt32(smartProp.Variables.Count);
            foreach (var (name, value) in smartProp.Variables)
            {
                writer.WriteString(name);
                WriteScalar(writer, value);
            }
        }

        writer.WriteInt32(scene.Diagnostics.Length);
        foreach (var diagnostic in scene.Diagnostics)
        {
            writer.WriteString(diagnostic);
        }
    }

    private static void WriteScalar(NativeBinaryWriter writer, object? value)
    {
        switch (value)
        {
            case null:
                writer.WriteByte((byte)ScalarType.Null);
                return;
            case bool boolean:
                writer.WriteByte((byte)ScalarType.Boolean);
                writer.WriteBoolean(boolean);
                return;
            case string text:
                writer.WriteByte((byte)ScalarType.String);
                writer.WriteString(text);
                return;
            case float number:
                writer.WriteByte((byte)ScalarType.Single);
                writer.WriteSingle(number);
                return;
            case int number:
                writer.WriteByte((byte)ScalarType.Int32);
                writer.WriteInt32(number);
                return;
            case Vector2 vector:
                writer.WriteByte((byte)ScalarType.Vector2);
                writer.WriteSingle(vector.X);
                writer.WriteSingle(vector.Y);
                return;
            case Vector3 vector:
                writer.WriteByte((byte)ScalarType.Vector3);
                writer.WriteSingle(vector.X);
                writer.WriteSingle(vector.Y);
                writer.WriteSingle(vector.Z);
                return;
            case Color color:
                writer.WriteByte((byte)ScalarType.Vector3);
                writer.WriteSingle(color.R);
                writer.WriteSingle(color.G);
                writer.WriteSingle(color.B);
                return;
            default:
                writer.WriteByte((byte)ScalarType.String);
                writer.WriteString(value.ToString() ?? string.Empty);
                return;
        }
    }
}
