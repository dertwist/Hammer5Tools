using System.Numerics;

namespace Hammer5Tools.Core.Format.NavMesh;

/// <summary>Dissolves internal edges between adjacent horizontal baked-radar faces.</summary>
internal static class BakedFaceNgonCollapser
{
    private const float CoordinateTolerance = 0.001f;

    private sealed record LayerFace(int OriginalIndex, IReadOnlyList<Vector3> Source, List<PointKey> Points);

    private sealed record CollapsedFace(int OriginalIndex, IReadOnlyList<Vector3> Face);

    private readonly record struct PointKey(int X, int Y)
    {
        public static PointKey From(Vector3 point) => new(Coordinate(point.X), Coordinate(point.Y));
    }

    private readonly record struct LineKey(bool Vertical, int Coordinate);

    private readonly record struct EdgeKey(PointKey First, PointKey Second)
    {
        public static EdgeKey From(PointKey start, PointKey end) => Compare(start, end) <= 0
            ? new EdgeKey(start, end)
            : new EdgeKey(end, start);
    }

    private sealed record EdgeUse(int FaceIndex, PointKey Start, PointKey End);

    public static List<IReadOnlyList<Vector3>> Collapse(IReadOnlyList<IReadOnlyList<Vector3>> faces)
    {
        ArgumentNullException.ThrowIfNull(faces);

        var collapsed = new List<CollapsedFace>();
        var layers = new Dictionary<int, List<LayerFace>>();
        for (var index = 0; index < faces.Count; index++)
        {
            var face = faces[index];
            if (!TryCreateLayerFace(index, face, out var layerFace, out var layer))
            {
                collapsed.Add(new CollapsedFace(index, face));
                continue;
            }

            if (!layers.TryGetValue(layer, out var layerFaces))
            {
                layerFaces = [];
                layers[layer] = layerFaces;
            }
            layerFaces.Add(layerFace);
        }

        foreach (var layer in layers.Values)
            collapsed.AddRange(CollapseLayer(layer));

        return
        [
            .. collapsed
                .OrderBy(item => item.OriginalIndex)
                .Select(item => item.Face),
        ];
    }

    private static List<CollapsedFace> CollapseLayer(IReadOnlyList<LayerFace> faces)
    {
        var lineCuts = new Dictionary<LineKey, SortedSet<int>>();
        var xCoordinates = new Dictionary<int, float>();
        var yCoordinates = new Dictionary<int, float>();
        foreach (var face in faces)
        {
            for (var index = 0; index < face.Points.Count; index++)
            {
                var start = face.Points[index];
                var end = face.Points[(index + 1) % face.Points.Count];
                xCoordinates.TryAdd(start.X, face.Source[index].X);
                yCoordinates.TryAdd(start.Y, face.Source[index].Y);

                var vertical = start.X == end.X;
                var line = new LineKey(vertical, vertical ? start.X : start.Y);
                if (!lineCuts.TryGetValue(line, out var cuts))
                {
                    cuts = [];
                    lineCuts[line] = cuts;
                }
                cuts.Add(vertical ? start.Y : start.X);
                cuts.Add(vertical ? end.Y : end.X);
            }
        }

        var edges = new Dictionary<EdgeKey, List<EdgeUse>>();
        for (var faceIndex = 0; faceIndex < faces.Count; faceIndex++)
        {
            var points = faces[faceIndex].Points;
            for (var edgeIndex = 0; edgeIndex < points.Count; edgeIndex++)
            {
                var start = points[edgeIndex];
                var end = points[(edgeIndex + 1) % points.Count];
                AddSplitEdges(faceIndex, start, end, lineCuts, edges);
            }
        }

        var parents = Enumerable.Range(0, faces.Count).ToArray();
        foreach (var uses in edges.Values.Where(uses => uses.Count > 1))
        {
            foreach (var use in uses.Skip(1))
                Union(parents, uses[0].FaceIndex, use.FaceIndex);
        }

        var componentFaces = Enumerable.Range(0, faces.Count)
            .GroupBy(index => Find(parents, index))
            .ToDictionary(group => group.Key, group => group.ToList());
        var invalidComponents = new HashSet<int>();
        var componentBoundaries = new Dictionary<int, List<EdgeUse>>();
        foreach (var uses in edges.Values)
        {
            var root = Find(parents, uses[0].FaceIndex);
            if (uses.Count == 1)
            {
                if (!componentBoundaries.TryGetValue(root, out var boundary))
                {
                    boundary = [];
                    componentBoundaries[root] = boundary;
                }
                boundary.Add(uses[0]);
                continue;
            }

            if (uses.Count != 2 || uses[0].Start != uses[1].End || uses[0].End != uses[1].Start)
                invalidComponents.Add(root);
        }

        var result = new List<CollapsedFace>(componentFaces.Count);
        foreach (var (root, component) in componentFaces)
        {
            if (invalidComponents.Contains(root)
                || !componentBoundaries.TryGetValue(root, out var boundary)
                || !TryTraceSingleLoop(boundary, out var loop))
            {
                AddOriginalFaces(faces, component, result);
                continue;
            }

            RemoveCollinearPoints(loop);
            if (loop.Count < 3)
            {
                AddOriginalFaces(faces, component, result);
                continue;
            }

            var z = faces[component[0]].Source[0].Z;
            IReadOnlyList<Vector3> ngon =
            [
                .. loop.Select(point => new Vector3(xCoordinates[point.X], yCoordinates[point.Y], z)),
            ];
            var sourceArea = component.Sum(index => MathF.Abs(SignedArea(faces[index].Source)));
            var ngonArea = MathF.Abs(SignedArea(ngon));
            if (MathF.Abs(sourceArea - ngonArea) > MathF.Max(1f, sourceArea * 0.00001f))
            {
                AddOriginalFaces(faces, component, result);
                continue;
            }

            if (SignedArea(ngon) < 0f)
                ngon = ngon.Reverse().ToArray();
            result.Add(new CollapsedFace(component.Min(index => faces[index].OriginalIndex), ngon));
        }
        return result;
    }

    private static bool TryCreateLayerFace(
        int index,
        IReadOnlyList<Vector3> source,
        out LayerFace face,
        out int layer)
    {
        face = null!;
        layer = 0;
        if (source.Count < 3 || source.Any(point => MathF.Abs(point.Z - source[0].Z) > CoordinateTolerance))
            return false;

        var points = source.Select(PointKey.From).ToList();
        if (points.Distinct().Count() < 3)
            return false;
        for (var pointIndex = 0; pointIndex < points.Count; pointIndex++)
        {
            var start = points[pointIndex];
            var end = points[(pointIndex + 1) % points.Count];
            if (start.X != end.X && start.Y != end.Y)
                return false;
        }

        if (SignedArea(points) < 0L)
        {
            points.Reverse();
            source = source.Reverse().ToArray();
        }

        layer = Coordinate(source[0].Z);
        face = new LayerFace(index, source, points);
        return true;
    }

    private static void AddSplitEdges(
        int faceIndex,
        PointKey start,
        PointKey end,
        IReadOnlyDictionary<LineKey, SortedSet<int>> lineCuts,
        Dictionary<EdgeKey, List<EdgeUse>> edges)
    {
        var vertical = start.X == end.X;
        var line = new LineKey(vertical, vertical ? start.X : start.Y);
        var startValue = vertical ? start.Y : start.X;
        var endValue = vertical ? end.Y : end.X;
        var cuts = lineCuts[line]
            .Where(value => value >= Math.Min(startValue, endValue) && value <= Math.Max(startValue, endValue))
            .ToList();
        if (startValue > endValue)
            cuts.Reverse();

        for (var index = 0; index + 1 < cuts.Count; index++)
        {
            var first = vertical
                ? new PointKey(start.X, cuts[index])
                : new PointKey(cuts[index], start.Y);
            var second = vertical
                ? new PointKey(start.X, cuts[index + 1])
                : new PointKey(cuts[index + 1], start.Y);
            if (first == second)
                continue;

            var key = EdgeKey.From(first, second);
            if (!edges.TryGetValue(key, out var uses))
            {
                uses = [];
                edges[key] = uses;
            }
            uses.Add(new EdgeUse(faceIndex, first, second));
        }
    }

    private static bool TryTraceSingleLoop(IReadOnlyList<EdgeUse> boundary, out List<PointKey> loop)
    {
        loop = [];
        var outgoing = new Dictionary<PointKey, PointKey>();
        var incoming = new Dictionary<PointKey, int>();
        foreach (var edge in boundary)
        {
            if (!outgoing.TryAdd(edge.Start, edge.End))
                return false;
            incoming[edge.End] = incoming.GetValueOrDefault(edge.End) + 1;
        }

        if (incoming.Values.Any(count => count != 1) || outgoing.Keys.Any(point => !incoming.ContainsKey(point)))
            return false;

        var start = outgoing.Keys.First();
        var current = start;
        while (outgoing.Remove(current, out var next))
        {
            loop.Add(current);
            current = next;
            if (current == start)
                break;
        }
        return current == start && outgoing.Count == 0;
    }

    private static void RemoveCollinearPoints(List<PointKey> points)
    {
        var changed = true;
        while (changed && points.Count >= 3)
        {
            changed = false;
            for (var index = points.Count - 1; index >= 0; index--)
            {
                var previous = points[(index + points.Count - 1) % points.Count];
                var current = points[index];
                var next = points[(index + 1) % points.Count];
                if (Cross(previous, current, next) != 0L)
                    continue;
                points.RemoveAt(index);
                changed = true;
            }
        }
    }

    private static void AddOriginalFaces(
        IReadOnlyList<LayerFace> faces,
        IEnumerable<int> component,
        List<CollapsedFace> result)
    {
        result.AddRange(component.Select(index => new CollapsedFace(faces[index].OriginalIndex, faces[index].Source)));
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

    private static void Union(int[] parents, int first, int second)
    {
        var firstRoot = Find(parents, first);
        var secondRoot = Find(parents, second);
        if (firstRoot != secondRoot)
            parents[secondRoot] = firstRoot;
    }

    private static long SignedArea(IReadOnlyList<PointKey> points)
    {
        var area = 0L;
        for (var index = 0; index < points.Count; index++)
        {
            var next = points[(index + 1) % points.Count];
            area += ((long)points[index].X * next.Y) - ((long)next.X * points[index].Y);
        }
        return area;
    }

    private static float SignedArea(IReadOnlyList<Vector3> points)
    {
        var area = 0f;
        for (var index = 0; index < points.Count; index++)
        {
            var next = points[(index + 1) % points.Count];
            area += (points[index].X * next.Y) - (next.X * points[index].Y);
        }
        return area / 2f;
    }

    private static long Cross(PointKey first, PointKey second, PointKey third) =>
        ((long)(second.X - first.X) * (third.Y - second.Y))
        - ((long)(second.Y - first.Y) * (third.X - second.X));

    private static int Compare(PointKey first, PointKey second)
    {
        var x = first.X.CompareTo(second.X);
        return x != 0 ? x : first.Y.CompareTo(second.Y);
    }

    private static int Coordinate(float value) => (int)MathF.Round(value / CoordinateTolerance);
}
