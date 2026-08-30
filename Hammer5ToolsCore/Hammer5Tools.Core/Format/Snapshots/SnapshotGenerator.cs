namespace Hammer5Tools.Core.Format.Snapshots;

/// <summary>Creates and modifies particle snapshot point streams.</summary>
public static class SnapshotGenerator
{
    private static readonly float[] DefaultRadius = [4f];
    private static readonly float[] DefaultOpacity = [1f];
    private static readonly float[] FirstRopeSegment = [0f];
    /// <summary>Generates a geometric primitive snapshot.</summary>
    public static SnapshotDocument GeneratePrimitive(string primitive, int count, float size)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(primitive);
        if (count < 1 || count > 1_000_000)
        {
            throw new ArgumentOutOfRangeException(nameof(count));
        }
        if (!float.IsFinite(size) || size <= 0f)
        {
            throw new ArgumentOutOfRangeException(nameof(size));
        }

        var positions = primitive.ToLowerInvariant() switch
        {
            "sphere" => Sphere(count, size),
            "box" => Box(count, size),
            "plane" => Plane(count, size),
            "ring" => Ring(count, size),
            _ => throw new ArgumentException($"Unknown primitive '{primitive}'.", nameof(primitive)),
        };
        return FromPositions(positions);
    }

    /// <summary>Creates a snapshot from authored positions.</summary>
    public static SnapshotDocument FromPositions(IReadOnlyList<float[]> positions)
    {
        ArgumentNullException.ThrowIfNull(positions);
        var points = positions.Select(position => position.Length == 3
            ? position.ToArray()
            : throw new ArgumentException("Every position must contain three components.", nameof(positions))).ToArray();
        var normals = points.Select(Normalize).ToArray();
        return new SnapshotDocument([
            new SnapshotChannel("position", "position_3d", points),
            new SnapshotChannel("normal", "normal_3d", normals),
            new SnapshotChannel("radius", "generic_float", points.Select(_ => DefaultRadius).ToArray()),
            new SnapshotChannel("opacity", "generic_float", points.Select(_ => DefaultOpacity).ToArray()),
            // One authored stroke is one rope, so every point shares a segment id; the index
            // along the rope is the engine's to derive.
            new SnapshotChannel("rope_segment_id", "generic_int", points.Select(_ => FirstRopeSegment).ToArray()),
        ]);
    }

    /// <summary>Writes a two-point RGB lighting gradient into the color stream.</summary>
    public static SnapshotDocument ApplyTwoPointLighting(SnapshotDocument document, int firstIndex, int secondIndex)
    {
        ArgumentNullException.ThrowIfNull(document);
        var positions = document.Streams.FirstOrDefault(stream => stream.Name == "position")?.Values
            ?? throw new InvalidDataException("Snapshot has no position stream.");
        if ((uint)firstIndex >= positions.Count || (uint)secondIndex >= positions.Count || firstIndex == secondIndex)
        {
            throw new ArgumentOutOfRangeException(nameof(firstIndex), "Choose two different valid point indices.");
        }

        var first = new Vector3(positions[firstIndex][0], positions[firstIndex][1], positions[firstIndex][2]);
        var second = new Vector3(positions[secondIndex][0], positions[secondIndex][1], positions[secondIndex][2]);
        var direction = second - first;
        var lengthSquared = direction.LengthSquared();
        var colors = positions.Select(position =>
        {
            var point = new Vector3(position[0], position[1], position[2]);
            var amount = Math.Clamp(Vector3.Dot(point - first, direction) / lengthSquared, 0f, 1f);
            return new[] { 1f, float.Lerp(0.72f, 0.22f, amount), float.Lerp(0.25f, 1f, amount) };
        }).ToArray();
        var streams = document.Streams.Where(stream => stream.Name != "color").ToList();
        streams.Add(new SnapshotChannel("color", "generic_vector_3d", colors));
        return new SnapshotDocument(streams);
    }

    internal static SnapshotDocument GenerateLightning(
        Vector3 start,
        Vector3 end,
        int trunkPointCount,
        float roughness,
        float branchProbability,
        int recursionDepth,
        float radius,
        int seed)
    {
        if (trunkPointCount is < 8 or > 4096)
        {
            throw new ArgumentOutOfRangeException(nameof(trunkPointCount));
        }
        if (!float.IsFinite(roughness) || roughness < 0f)
        {
            throw new ArgumentOutOfRangeException(nameof(roughness));
        }
        if (!float.IsFinite(branchProbability) || branchProbability is < 0f or > 1f)
        {
            throw new ArgumentOutOfRangeException(nameof(branchProbability));
        }
        if (recursionDepth is < 0 or > 4)
        {
            throw new ArgumentOutOfRangeException(nameof(recursionDepth));
        }
        if (!float.IsFinite(radius) || radius <= 0f || Vector3.DistanceSquared(start, end) < 1e-8f)
        {
            throw new ArgumentOutOfRangeException(nameof(radius));
        }

        const float jaggedness = 0.65f;
        const float branchLengthDecay = 0.6f;
        const float branchRadiusDecay = 0.55f;
        const float groundAttraction = 0.35f;
        var subdivisions = Math.Clamp((int)MathF.Ceiling(MathF.Log2(trunkPointCount)), 3, 10);
        var random = new Random(seed);
        var branches = new List<LightningBranch>();
        var trunk = GenerateLightningBranch(
            0, -1, 0, start, end, trunkPointCount, subdivisions, roughness, jaggedness, 3, radius, random);
        branches.Add(trunk);

        var queue = new Queue<LightningBranch>();
        queue.Enqueue(trunk);
        var nextBranchId = 1;
        while (queue.TryDequeue(out var parent) && parent.Depth < recursionDepth)
        {
            var candidates = Math.Max(1, (int)MathF.Round((10 - parent.Depth * 3) * branchProbability));
            var step = Math.Max(3, parent.Points.Count / (candidates + 1));
            for (var index = 2; index < parent.Points.Count - 2; index += step)
            {
                if (random.NextSingle() > branchProbability)
                {
                    continue;
                }

                var origin = parent.Points[index].Position;
                var localDirection = SafeNormalize(parent.Points[index + 1].Position - origin, Vector3.UnitX);
                var rotationAxis = RandomPerpendicular(localDirection, random);
                var angle = float.Lerp(18f, 45f, random.NextSingle()) * MathF.PI / 180f;
                var branchDirection = Vector3.Transform(localDirection, Quaternion.CreateFromAxisAngle(rotationAxis, angle));
                branchDirection = SafeNormalize(Vector3.Lerp(
                    branchDirection,
                    -Vector3.UnitZ,
                    groundAttraction * float.Lerp(0.4f, 1f, random.NextSingle())),
                    branchDirection);
                var depth = parent.Depth + 1;
                var depthFactor = MathF.Pow(branchLengthDecay, depth);
                var length = Vector3.Distance(start, end) * depthFactor * float.Lerp(0.35f, 0.9f, random.NextSingle());
                var pointCount = Math.Max(6, (int)MathF.Round(parent.Points.Count * 0.5f * depthFactor));
                var child = GenerateLightningBranch(
                    nextBranchId++,
                    parent.Id,
                    depth,
                    origin,
                    origin + branchDirection * length,
                    pointCount,
                    Math.Max(3, subdivisions - depth),
                    roughness * MathF.Pow(jaggedness, depth),
                    jaggedness,
                    2,
                    parent.Radius * branchRadiusDecay,
                    random);
                branches.Add(child);
                queue.Enqueue(child);
            }
        }

        var points = branches.SelectMany(branch => branch.Points).ToArray();
        var positions = points.Select(point => Components(point.Position)).ToArray();
        var normals = points.Select(point => Components(point.Tangent)).ToArray();
        var radii = points.Select(point => new[] { point.Radius }).ToArray();
        var opacity = points.Select(point => new[] { float.Lerp(1f, 0.65f, point.Progress) }).ToArray();
        var colors = points.Select(point => new[]
        {
            1f,
            float.Lerp(1f, 0.45f, point.Progress),
            float.Lerp(1f, 0.95f, point.Progress),
        }).ToArray();
        // Rope Segment ID is the identity of the rope a particle belongs to, not its index along
        // one: C_OP_RenderRopes starts a fresh strip wherever the id changes between neighbouring
        // particles. Giving every branch its own id is what stops the renderer joining the end of
        // one branch to the start of the next, which is what those long stray segments were.
        // Branch points stay contiguous in the arrays so each id forms one unbroken run.
        var ropeSegmentIds = branches.SelectMany(branch => branch.Points.Select(_ => new[] { (float)branch.Id })).ToArray();
        // Distance along the branch, 0 to 1. Valve's own lightning feeds this slot to the rope
        // renderer's m_nScalarFieldForTextureCoordinate (18), so it is the texture V coordinate.
        var arcLength = points.Select(point => new[] { point.Progress }).ToArray();
        // Valve's lightning generator also fills alpha2; deeper branches read dimmer.
        var branchBrightness = branches.SelectMany(branch => branch.Points
            .Select(_ => new[] { MathF.Pow(0.7f, branch.Depth) })).ToArray();
        return new SnapshotDocument([
            new SnapshotChannel("position", "position_3d", positions),
            new SnapshotChannel("normal", "normal_3d", normals),
            new SnapshotChannel("radius", "generic_float", radii),
            new SnapshotChannel("opacity", "generic_float", opacity),
            new SnapshotChannel("color", "generic_vector_3d", colors),
            new SnapshotChannel("scratch_float", "generic_float", arcLength),
            new SnapshotChannel("alpha2", "generic_float", branchBrightness),
            new SnapshotChannel("rope_segment_id", "generic_int", ropeSegmentIds),
        ]);
    }

    private static LightningBranch GenerateLightningBranch(
        int id,
        int parentId,
        int depth,
        Vector3 start,
        Vector3 end,
        int pointCount,
        int subdivisions,
        float roughness,
        float jaggedness,
        int octaves,
        float radius,
        Random random)
    {
        var nodes = new List<Vector3> { start, end };
        var displacement = roughness;
        for (var pass = 0; pass < subdivisions; pass++)
        {
            var next = new List<Vector3>(nodes.Count * 2 - 1) { nodes[0] };
            for (var index = 0; index < nodes.Count - 1; index++)
            {
                var first = nodes[index];
                var second = nodes[index + 1];
                var direction = SafeNormalize(second - first, Vector3.UnitX);
                var offset = RandomPerpendicular(direction, random) * ((random.NextSingle() * 2f - 1f) * displacement);
                next.Add(Vector3.Lerp(first, second, 0.5f) + offset);
                next.Add(second);
            }
            nodes = next;
            displacement *= jaggedness;
        }

        var sampled = ResamplePath(nodes, pointCount);
        var points = new List<LightningPoint>(sampled.Count);
        for (var index = 0; index < sampled.Count; index++)
        {
            var progress = index / (float)(sampled.Count - 1);
            var position = sampled[index];
            if (index > 0 && index < sampled.Count - 1)
            {
                for (var octave = 1; octave < octaves; octave++)
                {
                    var amplitude = roughness * 0.15f / (octave + 1);
                    position += new Vector3(
                        random.NextSingle() * 2f - 1f,
                        random.NextSingle() * 2f - 1f,
                        random.NextSingle() * 2f - 1f) * amplitude;
                }
            }
            var previous = sampled[Math.Max(0, index - 1)];
            var following = sampled[Math.Min(sampled.Count - 1, index + 1)];
            var tangent = SafeNormalize(following - previous, Vector3.UnitZ);
            points.Add(new LightningPoint(position, tangent, radius * float.Lerp(1f, 0.25f, progress), progress));
        }
        return new LightningBranch(id, parentId, depth, radius, points);
    }

    private static List<Vector3> ResamplePath(IReadOnlyList<Vector3> nodes, int pointCount)
    {
        var lengths = new float[nodes.Count - 1];
        var totalLength = 0f;
        for (var index = 0; index < lengths.Length; index++)
        {
            lengths[index] = Vector3.Distance(nodes[index], nodes[index + 1]);
            totalLength += lengths[index];
        }
        if (totalLength < 1e-8f)
        {
            return [.. Enumerable.Repeat(nodes[0], pointCount)];
        }

        var result = new List<Vector3>(pointCount) { nodes[0] };
        var segment = 0;
        var accumulated = 0f;
        for (var point = 1; point < pointCount - 1; point++)
        {
            var target = totalLength * point / (pointCount - 1);
            while (segment < lengths.Length - 1 && accumulated + lengths[segment] < target)
            {
                accumulated += lengths[segment++];
            }
            var amount = (target - accumulated) / MathF.Max(lengths[segment], 1e-8f);
            result.Add(Vector3.Lerp(nodes[segment], nodes[segment + 1], amount));
        }
        result.Add(nodes[^1]);
        return result;
    }

    private static Vector3 RandomPerpendicular(Vector3 direction, Random random)
    {
        var reference = MathF.Abs(direction.Z) < 0.9f ? Vector3.UnitZ : Vector3.UnitX;
        var first = SafeNormalize(Vector3.Cross(direction, reference), Vector3.UnitY);
        var second = SafeNormalize(Vector3.Cross(direction, first), Vector3.UnitZ);
        var angle = random.NextSingle() * MathF.Tau;
        return first * MathF.Cos(angle) + second * MathF.Sin(angle);
    }

    private static Vector3 SafeNormalize(Vector3 value, Vector3 fallback) =>
        value.LengthSquared() < 1e-8f ? fallback : Vector3.Normalize(value);

    private static float[] Components(Vector3 value) => [value.X, value.Y, value.Z];

    private sealed record LightningPoint(Vector3 Position, Vector3 Tangent, float Radius, float Progress);
    private sealed record LightningBranch(int Id, int ParentId, int Depth, float Radius, List<LightningPoint> Points);

    private static float[][] Sphere(int count, float radius)
    {
        const float goldenAngle = MathF.PI * (3f - 2.2360679775f);
        return Enumerable.Range(0, count).Select(index =>
        {
            var y = 1f - (2f * (index + 0.5f) / count);
            var radial = MathF.Sqrt(MathF.Max(0f, 1f - (y * y)));
            var angle = index * goldenAngle;
            return new[] { MathF.Cos(angle) * radial * radius, MathF.Sin(angle) * radial * radius, y * radius };
        }).ToArray();
    }

    private static float[][] Ring(int count, float radius) => Enumerable.Range(0, count)
        .Select(index => 2f * MathF.PI * index / count)
        .Select(angle => new[] { MathF.Cos(angle) * radius, MathF.Sin(angle) * radius, 0f })
        .ToArray();

    private static float[][] Plane(int count, float size)
    {
        var width = (int)MathF.Ceiling(MathF.Sqrt(count));
        return Enumerable.Range(0, count).Select(index =>
        {
            var x = index % width;
            var y = index / width;
            var divisor = Math.Max(1, width - 1);
            return new[] { ((x / (float)divisor) - 0.5f) * size, ((y / (float)divisor) - 0.5f) * size, 0f };
        }).ToArray();
    }

    private static float[][] Box(int count, float size)
    {
        var random = new Random(5);
        var half = size * 0.5f;
        return Enumerable.Range(0, count).Select(index =>
        {
            var point = new[] { (random.NextSingle() - 0.5f) * size, (random.NextSingle() - 0.5f) * size, (random.NextSingle() - 0.5f) * size };
            var axis = index % 3;
            point[axis] = (index / 3) % 2 == 0 ? -half : half;
            return point;
        }).ToArray();
    }

    private static float[] Normalize(float[] position)
    {
        var value = new Vector3(position[0], position[1], position[2]);
        if (value.LengthSquared() < 1e-8f)
        {
            return [0f, 0f, 1f];
        }
        value = Vector3.Normalize(value);
        return [value.X, value.Y, value.Z];
    }

}
