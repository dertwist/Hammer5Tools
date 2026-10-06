using System.Numerics;

using Clipper2Lib;

namespace Hammer5Tools.Core.Format.NavMesh;

/// <summary>
/// Grows the outline of the walkable surface outward without disturbing the areas inside it.
/// Compiled NAV areas already tile their surface almost exactly; it is offsetting each of them on
/// its own that stacks hundreds of near-coplanar rings and turns the radar into z-fighting soup.
/// Unioning per layer finds the one outline that actually has to move, and everything behind it
/// keeps the heights the NAV generator gave it.
/// </summary>
internal static class NavMeshRadarUnion
{
    /// <summary>Clipper is integer-only; 16 steps per Hammer unit is finer than NAV data resolves.</summary>
    private const double Scale = 16d;

    /// <summary>A collar quad shorter than this along the outline carries no area.</summary>
    private const float Epsilon = 0.05f;

    /// <summary>
    /// Returns the band that carries each walkable layer's outline out by <paramref name="offset"/>,
    /// as one quad per outline edge. The caller keeps its own faces and simply adds these.
    /// </summary>
    public static List<IReadOnlyList<Vector3>> Collar(
        IReadOnlyList<IReadOnlyList<Vector3>> rings,
        float offset)
    {
        ArgumentNullException.ThrowIfNull(rings);
        if (offset <= 0f)
            return [];

        var faces = new List<IReadOnlyList<Vector3>>();
        foreach (var layer in NavMeshRadarSurface.ClusterLayers(rings))
        {
            var sources = layer.Select(index => rings[index]).ToList();
            var merged = UnionLayer(sources);
            if (merged.Count == 0)
                continue;

            var heights = new NavMeshRadarHeightField(sources);
            foreach (var path in merged)
                AddCollar(path, heights, offset, faces);
        }
        return faces;
    }

    /// <summary>
    /// Flattens one layer's rings into its outline. Nothing is simplified here: the collar's inner
    /// edge has to land exactly on the boundary of the areas it wraps, or it opens a crack.
    /// </summary>
    private static Paths64 UnionLayer(IReadOnlyList<IReadOnlyList<Vector3>> rings)
    {
        var paths = new Paths64();
        foreach (var ring in rings)
        {
            if (ring.Count < 3)
                continue;
            var path = new Path64(ring.Count);
            foreach (var corner in ring)
                path.Add(new Point64((long)Math.Round(corner.X * Scale), (long)Math.Round(corner.Y * Scale)));

            // NonZero cancels a clockwise ring against a counter-clockwise one it overlaps, which
            // would punch holes wherever the NAV winding disagrees.
            if (Clipper.Area(path) < 0)
                path.Reverse();
            paths.Add(path);
        }
        return paths.Count == 0 ? [] : Clipper.Union(paths, FillRule.NonZero);
    }

    /// <summary>
    /// Lays a quad strip along one outline ring. Clipper winds an outer ring counter-clockwise and
    /// a hole clockwise, and the walkable side of a hole is outside it, so a hole's collar has to
    /// close in on itself while an outer ring's opens out.
    /// </summary>
    private static void AddCollar(
        Path64 path,
        NavMeshRadarHeightField heights,
        float offset,
        List<IReadOnlyList<Vector3>> faces)
    {
        if (path.Count < 3)
            return;

        var inner = new Vector3[path.Count];
        for (var index = 0; index < path.Count; index++)
        {
            var point = ToVector(path[index]);
            inner[index] = heights.Point(point.X, point.Y);
        }

        var outer = Expand(inner, Clipper.Area(path) > 0 ? offset : -offset);
        for (var index = 0; index < inner.Length; index++)
        {
            var next = (index + 1) % inner.Length;
            if (Vector2.Distance(Flat(inner[index]), Flat(inner[next])) <= Epsilon)
                continue;
            faces.Add([inner[index], outer[index], outer[next], inner[next]]);
        }
    }

    /// <summary>
    /// Miters every vertex along its two edge normals. A negative <paramref name="offset"/> pulls
    /// the ring in on itself instead, which is what a hole needs.
    /// </summary>
    private static Vector3[] Expand(IReadOnlyList<Vector3> ring, float offset)
    {
        var outward = new Vector3[ring.Count];
        for (var index = 0; index < ring.Count; index++)
        {
            var previous = ring[(index + ring.Count - 1) % ring.Count];
            var current = ring[index];
            var next = ring[(index + 1) % ring.Count];
            var shift = NavMeshRadarGenerator.MiterShift(
                [
                    NavMeshRadarGenerator.OutwardNormal(previous, current, offset),
                    NavMeshRadarGenerator.OutwardNormal(current, next, offset),
                ],
                MathF.Abs(offset));
            if (offset < 0f)
                shift = -shift;
            outward[index] = new Vector3(current.X + shift.X, current.Y + shift.Y, current.Z);
        }
        return outward;
    }

    private static Vector2 Flat(Vector3 point) => new(point.X, point.Y);

    private static Vector2 ToVector(Point64 point) => new((float)(point.X / Scale), (float)(point.Y / Scale));
}
