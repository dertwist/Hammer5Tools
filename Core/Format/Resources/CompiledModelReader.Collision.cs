using ValveResourceFormat;
using ValveResourceFormat.IO;
using ValveResourceFormat.ResourceTypes;

namespace Hammer5Tools.Core.Format.Resources;

public sealed partial class CompiledModelReader
{
    private static void AppendCollision(
        GameFileLoader loader, Model model, Resource resource, List<float> vertices,
        List<float> normals, List<float> uvs, List<uint> indices, List<CompiledSubMesh> subMeshes)
    {
        var embedded = model.GetEmbeddedPhys() ?? resource.GetBlockByType(BlockType.PHYS) as PhysAggregateData;
        if (embedded is not null)
            AppendPhysics(embedded, vertices, normals, uvs, indices, subMeshes);
        foreach (var path in model.GetReferencedPhysNames() ?? [])
        {
            if (string.IsNullOrWhiteSpace(path))
                continue;
            using var referenced = loader.LoadFileCompiled(path);
            if (referenced?.DataBlock is PhysAggregateData physics)
                AppendPhysics(physics, vertices, normals, uvs, indices, subMeshes);
        }
    }

    private static void AppendPhysics(
        PhysAggregateData physics, List<float> vertices, List<float> normals, List<float> uvs,
        List<uint> indices, List<CompiledSubMesh> subMeshes)
    {
        var parts = physics.Parts;
        var bindPose = physics.BindPose;
        for (var partIndex = 0; partIndex < parts.Length; partIndex++)
        {
            var shape = parts[partIndex].Shape;
            if (shape.Spheres.Length > 0 || shape.Capsules.Length > 0)
                throw new InvalidDataException("Collision fallback does not yet support spheres or capsules.");
            if (bindPose.Length > 0 && partIndex >= bindPose.Length)
                throw new InvalidDataException("Collision part has no corresponding bind pose.");
            var transform = bindPose.Length == 0 ? Matrix4x4.Identity : bindPose[partIndex];
            var start = indices.Count;
            foreach (var descriptor in shape.Hulls)
            {
                var hull = descriptor.Shape;
                var positions = hull.GetVertexPositions();
                var edges = hull.GetEdges();
                foreach (var face in hull.GetFaces())
                {
                    var ring = new List<int>();
                    var edgeIndex = (int)face.Edge;
                    do
                    {
                        if (edgeIndex >= edges.Length || ring.Count >= edges.Length)
                            throw new InvalidDataException("Invalid collision hull face ring.");
                        var edge = edges[edgeIndex];
                        if (edge.Origin >= positions.Length)
                            throw new InvalidDataException("Collision hull vertex index is out of bounds.");
                        ring.Add(edge.Origin);
                        edgeIndex = edge.Next;
                    } while (edgeIndex != face.Edge);
                    for (var index = 1; index + 1 < ring.Count; index++)
                        AppendCollisionTriangle(positions[ring[0]], positions[ring[index]], positions[ring[index + 1]],
                            transform, vertices, normals, uvs, indices);
                }
            }
            foreach (var descriptor in shape.Meshes)
            {
                var positions = descriptor.Shape.GetVertices();
                foreach (var triangle in descriptor.Shape.GetTriangles())
                {
                    if ((uint)triangle.X >= positions.Length || (uint)triangle.Y >= positions.Length || (uint)triangle.Z >= positions.Length)
                        throw new InvalidDataException("Collision mesh triangle index is out of bounds.");
                    AppendCollisionTriangle(positions[triangle.X], positions[triangle.Y], positions[triangle.Z],
                        transform, vertices, normals, uvs, indices);
                }
            }
            if (indices.Count > start)
                subMeshes.Add(new CompiledSubMesh(start, indices.Count - start,
                    DefaultMaterial with { Name = "__source2_collision__" }));
        }
    }

    private static void AppendCollisionTriangle(
        Vector3 first, Vector3 second, Vector3 third, Matrix4x4 transform,
        List<float> vertices, List<float> normals, List<float> uvs, List<uint> indices)
    {
        first = Vector3.Transform(first, transform);
        second = Vector3.Transform(second, transform);
        third = Vector3.Transform(third, transform);
        var normal = Vector3.Cross(second - first, third - first);
        if (!float.IsFinite(normal.LengthSquared()))
            throw new InvalidDataException("Collision geometry contains non-finite coordinates.");
        if (normal.LengthSquared() < 1e-12f)
            return;
        normal = Vector3.Normalize(normal);
        foreach (var position in new[] { first, second, third })
        {
            indices.Add((uint)(vertices.Count / 3));
            Append(vertices, position);
            Append(normals, normal);
            Append(uvs, Vector2.Zero);
        }
    }
}
