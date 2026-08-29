using System.Numerics;

namespace Hammer5Tools.Core.Format.NavMesh;

/// <summary>A polygon's extent in the XY plane.</summary>
internal readonly record struct SurfaceBounds(
    float MinimumX,
    float MaximumX,
    float MinimumY,
    float MaximumY)
{
    public bool Contains(float x, float y) =>
        x >= MinimumX && x <= MaximumX && y >= MinimumY && y <= MaximumY;
}

/// <summary>One polygon's surface, as the height it reports anywhere in the XY plane.</summary>
internal readonly record struct SurfacePlane(float XGradient, float YGradient, float Offset)
{
    public float HeightAt(float x, float y) => (XGradient * x) + (YGradient * y) + Offset;
}

/// <summary>Shared geometry helpers for the NAV radar passes.</summary>
internal static class NavMeshRadarSurface
{
    /// <summary>Vertical distance that separates one walkable layer from the one stacked above it.</summary>
    public const float LayerGap = 96f;

    /// <summary>Cell size of the layer-clustering and height-lookup grids, in Hammer units.</summary>
    public const float CellSize = 128f;

    /// <summary>
    /// Groups polygons into the surfaces a player actually walks on, so a vent over a room is never
    /// merged with the room. Polygons that share a grid cell and sit within <see cref="LayerGap"/>
    /// of each other belong together; polygons far apart in XY land in separate groups, which costs
    /// nothing because treating disjoint regions separately gives the same result.
    /// </summary>
    public static List<List<int>> ClusterLayers(IReadOnlyList<IReadOnlyList<Vector3>> polygons)
    {
        ArgumentNullException.ThrowIfNull(polygons);

        var parents = new int[polygons.Count];
        for (var index = 0; index < parents.Length; index++)
            parents[index] = index;

        var cells = new Dictionary<(int X, int Y), List<int>>();
        for (var index = 0; index < polygons.Count; index++)
        {
            var bounds = BoundsOf(polygons[index]);
            for (var x = Cell(bounds.MinimumX); x <= Cell(bounds.MaximumX); x++)
            {
                for (var y = Cell(bounds.MinimumY); y <= Cell(bounds.MaximumY); y++)
                {
                    if (!cells.TryGetValue((x, y), out var bucket))
                    {
                        bucket = [];
                        cells[(x, y)] = bucket;
                    }
                    bucket.Add(index);
                }
            }
        }

        var heights = polygons.Select(AverageHeight).ToArray();
        foreach (var bucket in cells.Values)
        {
            bucket.Sort((left, right) => heights[left].CompareTo(heights[right]));
            for (var index = 1; index < bucket.Count; index++)
            {
                if (heights[bucket[index]] - heights[bucket[index - 1]] <= LayerGap)
                    Merge(parents, bucket[index - 1], bucket[index]);
            }
        }

        var groups = new Dictionary<int, List<int>>();
        for (var index = 0; index < polygons.Count; index++)
        {
            var root = Find(parents, index);
            if (!groups.TryGetValue(root, out var group))
            {
                group = [];
                groups[root] = group;
            }
            group.Add(index);
        }
        return [.. groups.Values];
    }

    public static int Cell(float value) => (int)MathF.Floor(value / CellSize);

    public static float AverageHeight(IReadOnlyList<Vector3> polygon) =>
        polygon.Average(corner => corner.Z);

    public static SurfaceBounds BoundsOf(IReadOnlyList<Vector3> polygon) => new(
        polygon.Min(corner => corner.X),
        polygon.Max(corner => corner.X),
        polygon.Min(corner => corner.Y),
        polygon.Max(corner => corner.Y));

    public static bool Contains(IReadOnlyList<Vector3> polygon, float x, float y)
    {
        var inside = false;
        for (int index = 0, previous = polygon.Count - 1; index < polygon.Count; previous = index++)
        {
            var current = polygon[index];
            var last = polygon[previous];
            if ((current.Y > y) == (last.Y > y))
                continue;
            var crossing = current.X + ((y - current.Y) / (last.Y - current.Y) * (last.X - current.X));
            if (x < crossing)
                inside = !inside;
        }
        return inside;
    }

    /// <summary>
    /// Newell's normal turned into a height function. A NAV quad has four independent corner
    /// heights and so is rarely planar; Newell averages that out instead of trusting one corner
    /// triple, and a polygon standing on edge degenerates to its mean height.
    /// </summary>
    public static SurfacePlane FitPlane(IReadOnlyList<Vector3> polygon)
    {
        var normal = Vector3.Zero;
        var centroid = Vector3.Zero;
        for (int index = 0, previous = polygon.Count - 1; index < polygon.Count; previous = index++)
        {
            var current = polygon[index];
            var last = polygon[previous];
            normal.X += (last.Y - current.Y) * (last.Z + current.Z);
            normal.Y += (last.Z - current.Z) * (last.X + current.X);
            normal.Z += (last.X - current.X) * (last.Y + current.Y);
            centroid += current;
        }
        centroid /= polygon.Count;
        if (MathF.Abs(normal.Z) < 1e-4f)
            return new SurfacePlane(0f, 0f, centroid.Z);

        var xGradient = -normal.X / normal.Z;
        var yGradient = -normal.Y / normal.Z;
        return new SurfacePlane(
            xGradient,
            yGradient,
            centroid.Z - (xGradient * centroid.X) - (yGradient * centroid.Y));
    }

    private static int Find(int[] parents, int index)
    {
        while (parents[index] != index)
        {
            parents[index] = parents[parents[index]];
            index = parents[index];
        }
        return index;
    }

    private static void Merge(int[] parents, int left, int right)
    {
        var leftRoot = Find(parents, left);
        var rightRoot = Find(parents, right);
        if (leftRoot != rightRoot)
            parents[rightRoot] = leftRoot;
    }
}

/// <summary>
/// Answers "how high is the walkable surface here" for one layer's polygons. Both radar passes
/// work in the XY plane at some point and have to put the height back afterwards.
/// </summary>
internal sealed class NavMeshRadarHeightField
{
    private readonly List<IReadOnlyList<Vector3>> _polygons;
    private readonly List<SurfacePlane> _planes = [];
    private readonly List<SurfaceBounds> _bounds = [];
    private readonly List<(float Minimum, float Maximum)> _heights = [];
    private readonly Dictionary<(int X, int Y), List<int>> _cells = [];
    private readonly float _fallback;

    public NavMeshRadarHeightField(List<IReadOnlyList<Vector3>> polygons)
    {
        ArgumentNullException.ThrowIfNull(polygons);

        _polygons = polygons;
        foreach (var polygon in polygons)
        {
            _planes.Add(NavMeshRadarSurface.FitPlane(polygon));
            _bounds.Add(NavMeshRadarSurface.BoundsOf(polygon));
            _heights.Add((polygon.Min(corner => corner.Z), polygon.Max(corner => corner.Z)));
        }

        for (var index = 0; index < polygons.Count; index++)
        {
            var bounds = _bounds[index];
            for (var x = NavMeshRadarSurface.Cell(bounds.MinimumX); x <= NavMeshRadarSurface.Cell(bounds.MaximumX); x++)
            {
                for (var y = NavMeshRadarSurface.Cell(bounds.MinimumY); y <= NavMeshRadarSurface.Cell(bounds.MaximumY); y++)
                {
                    if (!_cells.TryGetValue((x, y), out var bucket))
                    {
                        bucket = [];
                        _cells[(x, y)] = bucket;
                    }
                    bucket.Add(index);
                }
            }
        }
        _fallback = polygons.Count == 0 ? 0f : polygons.Average(NavMeshRadarSurface.AverageHeight);
    }

    public Vector3 Point(float x, float y) => new(x, y, HeightAt(x, y));

    private float HeightAt(float x, float y)
    {
        if (!_cells.TryGetValue((NavMeshRadarSurface.Cell(x), NavMeshRadarSurface.Cell(y)), out var candidates))
            return NearestHeight(x, y);

        var best = float.NegativeInfinity;
        foreach (var index in candidates)
        {
            if (!_bounds[index].Contains(x, y) || !NavMeshRadarSurface.Contains(_polygons[index], x, y))
                continue;
            best = MathF.Max(best, Sample(index, x, y));
        }

        // Outline vertices land exactly on a source boundary, where containment is a coin toss.
        return float.IsNegativeInfinity(best) ? NearestHeight(x, y) : best;
    }

    /// <summary>Falls back to the closest polygon's plane, widening the search ring by ring.</summary>
    private float NearestHeight(float x, float y)
    {
        var cellX = NavMeshRadarSurface.Cell(x);
        var cellY = NavMeshRadarSurface.Cell(y);
        for (var radius = 0; radius <= 2; radius++)
        {
            var best = -1;
            var bestDistance = float.PositiveInfinity;
            for (var offsetX = -radius; offsetX <= radius; offsetX++)
            {
                for (var offsetY = -radius; offsetY <= radius; offsetY++)
                {
                    if (!_cells.TryGetValue((cellX + offsetX, cellY + offsetY), out var candidates))
                        continue;
                    foreach (var index in candidates)
                    {
                        var distance = DistanceSquared(_bounds[index], x, y);
                        if (distance >= bestDistance)
                            continue;
                        bestDistance = distance;
                        best = index;
                    }
                }
            }
            if (best >= 0)
                return Sample(best, x, y);
        }
        return _fallback;
    }

    /// <summary>
    /// A polygon's plane, held to the heights that polygon actually spans. The fallback above asks
    /// polygons for the height at points outside themselves, and a sloped plane extrapolated far
    /// enough runs away by thousands of units.
    /// </summary>
    private float Sample(int index, float x, float y) =>
        Math.Clamp(_planes[index].HeightAt(x, y), _heights[index].Minimum, _heights[index].Maximum);

    private static float DistanceSquared(SurfaceBounds bounds, float x, float y)
    {
        var dx = MathF.Max(MathF.Max(bounds.MinimumX - x, 0f), x - bounds.MaximumX);
        var dy = MathF.Max(MathF.Max(bounds.MinimumY - y, 0f), y - bounds.MaximumY);
        return (dx * dx) + (dy * dy);
    }
}
