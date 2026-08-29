using System.Numerics;

using Datamodel;
using Hammer5Tools.Core.Format.Vmap;
using Hammer5Tools.Core.IO.Vpk;
using ValveResourceFormat;
using ValveResourceFormat.NavMesh;
using ValveResourceFormat.ResourceTypes.GenericData.CS2;
using DM = Datamodel.Datamodel;

namespace Hammer5Tools.Core.Format.NavMesh;

/// <summary>Available sources for generated radar geometry.</summary>
public enum NavMeshRadarMode
{
    /// <summary>Valve's baked bomb-damage surface samples.</summary>
    BakedBombDamage,

    /// <summary>Compiled NAV areas expanded in the XY plane.</summary>
    NavMeshOffset,
}

/// <summary>Inputs for a NAV-based radar generation pass.</summary>
public sealed record NavMeshRadarRequest(
    string VpkPath,
    string MainVmapPath,
    NavMeshRadarMode Mode,
    float Offset,
    string MaterialPath,
    bool AddPrefabReference = true,
    bool CollapseFaces = true,
    bool CollapseFacesIntoNgons = false);

/// <summary>Summary of a completed NAV-based radar generation pass.</summary>
public sealed record NavMeshRadarResult(
    string GeneratedVmapPath,
    NavMeshRadarMode Mode,
    int SourceCount,
    int FaceCount,
    int MeshCount,
    float Offset,
    bool ReferenceAdded,
    string? BackupPath);

/// <summary>What a main map already holds for the generated radar, before anything is written.</summary>
public sealed record NavMeshRadarStatus(string GeneratedVmapPath, bool PrefabPresent);

/// <summary>Generates editable radar faces from compiled CS2 navigation data.</summary>
public static class NavMeshRadarGenerator
{
    private const int FacesPerMesh = 4096;
    private const float BakedHalfSize = 12f;
    private const float BakedMergeTolerance = 0.001f;
    private const float BakedPlanarTolerance = 0.5f;
    private const float BakedMaximumSlope = 1f;
    private const float SurfaceLift = 1f;
    private const float WeldTolerance = 1f;
    private const int DampingPasses = 32;
    private const float SplitCellSize = 128f;
    private const float SplitTolerance = 1f;
    private const float TriangleMinimumArea = 0.25f;

    /// <summary>One NAV area as a ring of corners plus, per edge, whether the agent stopped there.</summary>
    internal sealed class NavFace(List<Vector3> corners, List<bool> exposedEdges)
    {
        public List<Vector3> Corners { get; } = corners;

        /// <summary>Entry <c>i</c> describes the edge running from corner <c>i</c> to corner <c>i + 1</c>.</summary>
        public List<bool> ExposedEdges { get; } = exposedEdges;
    }

    private sealed record RadarGeometry(
        int SourceCount,
        List<IReadOnlyList<Vector3>> Faces);

    private sealed record BakedPatch(
        float MinimumX,
        float MaximumX,
        float MinimumY,
        float MaximumY,
        BakedPlane Plane,
        IReadOnlyList<Vector3> Samples)
    {
        public IReadOnlyList<Vector3> ToFace() =>
        [
            new Vector3(MinimumX, MinimumY, Plane.HeightAt(MinimumX, MinimumY) + SurfaceLift),
            new Vector3(MaximumX, MinimumY, Plane.HeightAt(MaximumX, MinimumY) + SurfaceLift),
            new Vector3(MaximumX, MaximumY, Plane.HeightAt(MaximumX, MaximumY) + SurfaceLift),
            new Vector3(MinimumX, MaximumY, Plane.HeightAt(MinimumX, MaximumY) + SurfaceLift),
        ];
    }

    private readonly record struct BakedPlane(float XGradient, float YGradient, float Offset)
    {
        public float HeightAt(float x, float y) => (XGradient * x) + (YGradient * y) + Offset;
    }

    private readonly record struct BakedInterval(float Minimum, float Maximum);

    private readonly record struct BakedSweepEvent(BakedInterval Interval, bool Add);

    private readonly record struct BakedMergeEdge(int Axis, int Minimum, int Maximum, int Position);

    private sealed record BakedMergeCandidate(
        int First,
        int Second,
        BakedPatch Patch,
        float MaximumError,
        float SlopeSquared);

    private sealed class WeldCluster(Vector3 anchor)
    {
        public Vector3 Anchor { get; } = anchor;

        public Vector3 Sum { get; private set; } = anchor;

        public int Count { get; private set; } = 1;

        public Vector3 Centroid => Sum / Count;

        public void Add(Vector3 corner)
        {
            Sum += corner;
            Count++;
        }
    }

    private readonly record struct VertexKey(int X, int Y, int Z)
    {
        public static VertexKey From(Vector3 value) => new(
            (int)MathF.Round(value.X * 100f),
            (int)MathF.Round(value.Y * 100f),
            (int)MathF.Round(value.Z * 100f));

        public static VertexKey Snap(Vector3 value, float tolerance) => new(
            (int)MathF.Round(value.X / tolerance),
            (int)MathF.Round(value.Y / tolerance),
            (int)MathF.Round(value.Z / tolerance));
    }

    private readonly record struct EdgeKey(VertexKey First, VertexKey Second)
    {
        public static EdgeKey From(Vector3 start, Vector3 end)
        {
            var first = VertexKey.From(start);
            var second = VertexKey.From(end);
            return Compare(first, second) <= 0
                ? new EdgeKey(first, second)
                : new EdgeKey(second, first);
        }

        private static int Compare(VertexKey left, VertexKey right)
        {
            var x = left.X.CompareTo(right.X);
            if (x != 0)
                return x;
            var y = left.Y.CompareTo(right.Y);
            return y != 0 ? y : left.Z.CompareTo(right.Z);
        }
    }

    /// <summary>
    /// Generates a replaceable radar sub-map and adds one prefab reference to the main map.
    /// </summary>
    public static CoreResult<NavMeshRadarResult> Generate(NavMeshRadarRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);

        try
        {
            Validate(request);
            var mapName = Path.GetFileNameWithoutExtension(request.MainVmapPath);
            var geometry = request.Mode switch
            {
                NavMeshRadarMode.BakedBombDamage => ReadBakedGeometry(
                    request.VpkPath,
                    mapName,
                    request.CollapseFaces,
                    request.CollapseFacesIntoNgons),
                NavMeshRadarMode.NavMeshOffset => ReadOffsetNavGeometry(request.VpkPath, mapName, request.Offset),
                _ => throw new InvalidDataException($"Unsupported radar mode '{request.Mode}'."),
            };

            if (geometry.Faces.Count == 0)
                throw new InvalidDataException("The selected navigation source contains no usable faces.");

            var generatedPath = GeneratedPath(request.MainVmapPath);
            var meshCount = WriteGeneratedMap(
                request.MainVmapPath,
                generatedPath,
                request.MaterialPath,
                geometry.Faces);
            var targetMapPath = $"maps/{Path.GetFileName(generatedPath)}";
            var (referenceAdded, backupPath) = request.AddPrefabReference
                ? EnsurePrefabReference(request.MainVmapPath, targetMapPath)
                : (false, (string?)null);

            return CoreResult.Success(new NavMeshRadarResult(
                generatedPath,
                request.Mode,
                geometry.SourceCount,
                geometry.Faces.Count,
                meshCount,
                request.Mode == NavMeshRadarMode.NavMeshOffset ? request.Offset : 0f,
                referenceAdded,
                backupPath));
        }
        catch (Exception exception)
        {
            return CoreResult.Failure<NavMeshRadarResult>(
                "navmesh_radar_generation_failed",
                $"Could not generate radar geometry: {exception.Message}");
        }
    }

    /// <summary>
    /// Reports where the radar sub-map for <paramref name="mainVmapPath"/> would be written and
    /// whether that map already carries a prefab pointing at it, so callers can tell an offer to add
    /// the reference from one that is already there.
    /// </summary>
    public static CoreResult<NavMeshRadarStatus> Inspect(string mainVmapPath)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(mainVmapPath);

        try
        {
            if (!File.Exists(mainVmapPath))
                throw new FileNotFoundException("The addon VMAP was not found.", mainVmapPath);

            var generatedPath = GeneratedPath(mainVmapPath);
            var main = VmapDocument.LoadInMemory(mainVmapPath);
            var present = HasPrefab(main.WorldChildren, $"maps/{Path.GetFileName(generatedPath)}");
            return CoreResult.Success(new NavMeshRadarStatus(generatedPath, present));
        }
        catch (Exception exception)
        {
            return CoreResult.Failure<NavMeshRadarStatus>(
                "navmesh_radar_inspect_failed",
                $"Could not inspect the main map: {exception.Message}");
        }
    }

    /// <summary>Snaps NAV corners that sit within <see cref="WeldTolerance"/> onto one shared position.</summary>
    internal static List<IReadOnlyList<Vector3>> WeldPolygons(IReadOnlyList<IReadOnlyList<Vector3>> polygons)
    {
        ArgumentNullException.ThrowIfNull(polygons);

        var buckets = new Dictionary<VertexKey, List<int>>();
        var clusters = new List<WeldCluster>();
        var assignments = new List<int[]>(polygons.Count);
        foreach (var polygon in polygons)
        {
            var polygonAssignments = new int[polygon.Count];
            for (var index = 0; index < polygon.Count; index++)
            {
                var corner = polygon[index];
                var clusterIndex = FindWeldCluster(buckets, clusters, corner);
                if (clusterIndex < 0)
                    clusterIndex = AddWeldCluster(buckets, clusters, corner);
                else
                    clusters[clusterIndex].Add(corner);
                polygonAssignments[index] = clusterIndex;
            }
            assignments.Add(polygonAssignments);
        }

        var welded = new List<IReadOnlyList<Vector3>>(polygons.Count);
        foreach (var polygonAssignments in assignments)
            welded.Add([.. polygonAssignments.Select(index => clusters[index].Centroid)]);
        return welded;
    }

    private static int FindWeldCluster(
        Dictionary<VertexKey, List<int>> buckets,
        IReadOnlyList<WeldCluster> clusters,
        Vector3 corner)
    {
        var key = VertexKey.Snap(corner, WeldTolerance);
        var maximumDistanceSquared = WeldTolerance * WeldTolerance;
        var closestDistanceSquared = float.MaxValue;
        var closestCluster = -1;
        for (var x = -1; x <= 1; x++)
        {
            for (var y = -1; y <= 1; y++)
            {
                for (var z = -1; z <= 1; z++)
                {
                    var neighbour = new VertexKey(key.X + x, key.Y + y, key.Z + z);
                    if (!buckets.TryGetValue(neighbour, out var candidates))
                        continue;
                    foreach (var candidate in candidates)
                    {
                        var distanceSquared = Vector3.DistanceSquared(clusters[candidate].Anchor, corner);
                        if (distanceSquared <= maximumDistanceSquared
                            && distanceSquared < closestDistanceSquared)
                        {
                            closestDistanceSquared = distanceSquared;
                            closestCluster = candidate;
                        }
                    }
                }
            }
        }
        return closestCluster;
    }

    private static int AddWeldCluster(
        Dictionary<VertexKey, List<int>> buckets,
        List<WeldCluster> clusters,
        Vector3 corner)
    {
        var key = VertexKey.Snap(corner, WeldTolerance);
        if (!buckets.TryGetValue(key, out var bucket))
        {
            bucket = [];
            buckets[key] = bucket;
        }

        var index = clusters.Count;
        clusters.Add(new WeldCluster(corner));
        bucket.Add(index);
        return index;
    }

    internal static Vector3[] OffsetPolygon(IReadOnlyList<Vector3> corners, float offset)
    {
        ArgumentNullException.ThrowIfNull(corners);
        if (corners.Count < 3)
            throw new ArgumentException("A polygon needs at least three corners.", nameof(corners));
        if (offset < 0f || !float.IsFinite(offset))
            throw new ArgumentOutOfRangeException(nameof(offset), "Offset must be a finite non-negative number.");
        if (offset == 0f)
            return [.. corners];

        var signedArea = SignedArea(corners);
        if (MathF.Abs(signedArea) < 0.0001f)
            return [.. corners];

        var result = new Vector3[corners.Count];
        for (var index = 0; index < corners.Count; index++)
        {
            var previous = corners[(index + corners.Count - 1) % corners.Count];
            var current = corners[index];
            var next = corners[(index + 1) % corners.Count];
            var previousNormal = OutwardNormal(previous, current, signedArea);
            var nextNormal = OutwardNormal(current, next, signedArea);
            var shift = MiterShift([previousNormal, nextNormal], offset);
            result[index] = new Vector3(current.X + shift.X, current.Y + shift.Y, current.Z);
        }

        return result;
    }

    /// <summary>
    /// Offsets each NAV area independently so a problematic neighbour cannot damp its expansion.
    /// The expanded areas may overlap, which preserves the combined footprint while ensuring every
    /// source area has its generator offset removed.
    /// </summary>
    internal static List<IReadOnlyList<Vector3>> OffsetPolygonsIndependently(
        IReadOnlyList<IReadOnlyList<Vector3>> polygons,
        float offset)
    {
        ArgumentNullException.ThrowIfNull(polygons);
        return [.. polygons.Select(polygon => (IReadOnlyList<Vector3>)OffsetPolygon(polygon, offset))];
    }

    /// <summary>
    /// Offsets exposed NAV boundaries by a uniform distance, preserving shared welded vertices.
    /// Exposed edges are found by geometric matching, which is only reliable when the caller
    /// supplies an edge-conforming mesh; compiled NAV data goes through
    /// <see cref="BuildNavFaces"/> instead, which reads the areas' own connection lists.
    /// </summary>
    internal static List<IReadOnlyList<Vector3>> OffsetWeldedPolygons(
        IReadOnlyList<IReadOnlyList<Vector3>> polygons,
        float offset)
    {
        ArgumentNullException.ThrowIfNull(polygons);
        if (offset < 0f || !float.IsFinite(offset))
            throw new ArgumentOutOfRangeException(nameof(offset), "Offset must be a finite non-negative number.");

        var edgeCounts = new Dictionary<EdgeKey, int>();
        foreach (var polygon in polygons)
        {
            for (var index = 0; index < polygon.Count; index++)
            {
                var edge = EdgeKey.From(polygon[index], polygon[(index + 1) % polygon.Count]);
                edgeCounts[edge] = edgeCounts.GetValueOrDefault(edge) + 1;
            }
        }

        var faces = new List<NavFace>(polygons.Count);
        foreach (var polygon in polygons)
        {
            var exposed = new List<bool>(polygon.Count);
            for (var index = 0; index < polygon.Count; index++)
            {
                var edge = EdgeKey.From(polygon[index], polygon[(index + 1) % polygon.Count]);
                exposed.Add(edgeCounts[edge] == 1);
            }
            faces.Add(new NavFace([.. polygon], exposed));
        }

        return OffsetFaces(faces, offset);
    }

    /// <summary>
    /// Pushes every exposed edge out by the gap <paramref name="gapForEdge"/> reports for it, so
    /// one boundary can be moved onto a wall while the one around the corner, which nothing ever
    /// blocked, stays exactly where the NAV generator left it.
    /// </summary>
    internal static List<IReadOnlyList<Vector3>> OffsetFaces(IReadOnlyList<NavFace> faces, float offset)
    {
        var exposedNormals = new Dictionary<VertexKey, List<Vector2>>();
        foreach (var face in faces)
        {
            var signedArea = SignedArea(face.Corners);
            for (var index = 0; index < face.Corners.Count; index++)
            {
                if (!face.ExposedEdges[index])
                    continue;

                var start = face.Corners[index];
                var end = face.Corners[(index + 1) % face.Corners.Count];
                var normal = OutwardNormal(start, end, signedArea);
                if (normal == Vector2.Zero)
                    continue;

                AddBoundaryNormal(exposedNormals, VertexKey.From(start), normal);
                AddBoundaryNormal(exposedNormals, VertexKey.From(end), normal);
            }
        }

        var shifts = new Dictionary<VertexKey, Vector2>();
        foreach (var face in faces)
        {
            foreach (var point in face.Corners)
            {
                var key = VertexKey.From(point);
                if (shifts.ContainsKey(key))
                    continue;
                shifts[key] = exposedNormals.TryGetValue(key, out var normals)
                    ? MiterShift(normals, offset)
                    : Vector2.Zero;
            }
        }

        var rings = faces
            .Select(face => (IReadOnlyList<Vector3>)face.Corners)
            .ToList();
        DampShifts(rings, shifts);
        return
        [
            .. rings.Select(ring => (IReadOnlyList<Vector3>)[.. ring.Select(point => Shift(point, shifts))]),
        ];
    }

    private static Vector3 Shift(Vector3 point, Dictionary<VertexKey, Vector2> shifts)
    {
        var shift = shifts[VertexKey.From(point)];
        return new Vector3(point.X + shift.X, point.Y + shift.Y, point.Z);
    }

    /// <summary>
    /// Halves the shifts around any face the offset would shrink, turn inside out, or fold into a
    /// bowtie. The smallest areas have every vertex pushed outward at once, and a face narrower than
    /// the offset then flips through itself and vacates its own footprint, which leaves a hole.
    /// </summary>
    private static void DampShifts(
        IReadOnlyList<IReadOnlyList<Vector3>> polygons,
        Dictionary<VertexKey, Vector2> shifts)
    {
        for (var pass = 0; pass < DampingPasses; pass++)
        {
            var damped = false;
            foreach (var polygon in polygons)
            {
                // NormalizeFace has already wound every face counter-clockwise, so an
                // outward offset may only ever grow the area.
                var original = SignedArea(polygon);
                if (original <= 0f)
                    continue;

                var shifted = polygon.Select(point => Shift(point, shifts)).ToArray();
                if (SignedArea(shifted) >= original && !SelfIntersects(shifted))
                    continue;

                foreach (var point in polygon)
                    shifts[VertexKey.From(point)] *= 0.5f;
                damped = true;
            }

            if (!damped)
                return;
        }
    }

    /// <summary>
    /// Whether two non-adjacent edges of the ring cross. Per-edge gaps can drive one corner past
    /// another and fold the face into a bowtie, which keeps a healthy signed area but renders as an
    /// hourglass with half the footprint missing.
    /// </summary>
    private static bool SelfIntersects(IReadOnlyList<Vector3> ring)
    {
        for (var first = 0; first < ring.Count; first++)
        {
            for (var second = first + 2; second < ring.Count; second++)
            {
                if (first == 0 && second == ring.Count - 1)
                    continue;
                if (EdgesCross(
                        ring[first],
                        ring[first + 1],
                        ring[second],
                        ring[(second + 1) % ring.Count]))
                    return true;
            }
        }
        return false;
    }

    private static bool EdgesCross(Vector3 firstStart, Vector3 firstEnd, Vector3 secondStart, Vector3 secondEnd)
    {
        var a = Side(firstStart, firstEnd, secondStart);
        var b = Side(firstStart, firstEnd, secondEnd);
        var c = Side(secondStart, secondEnd, firstStart);
        var d = Side(secondStart, secondEnd, firstEnd);
        return ((a > 0f && b < 0f) || (a < 0f && b > 0f))
            && ((c > 0f && d < 0f) || (c < 0f && d > 0f));

        static float Side(Vector3 from, Vector3 to, Vector3 point) =>
            ((to.X - from.X) * (point.Y - from.Y)) - ((to.Y - from.Y) * (point.X - from.X));
    }

    private static void AddBoundaryNormal(
        Dictionary<VertexKey, List<Vector2>> exposedNormals,
        VertexKey vertex,
        Vector2 normal)
    {
        if (!exposedNormals.TryGetValue(vertex, out var normals))
        {
            normals = [];
            exposedNormals[vertex] = normals;
        }
        normals.Add(normal);
    }

    /// <summary>
    /// Builds one face per NAV area, marking each edge exposed when no area declares a connection
    /// across it. NAV areas are not edge-conforming — on de_dust2 over half of all edges are shared
    /// with no second area geometrically — so the areas' own connection lists are the only reliable
    /// way to tell an interior edge from the outline the agent actually stopped at.
    /// </summary>
    internal static List<NavFace> BuildNavFaces(
        IReadOnlyList<NavMeshArea> areas,
        IReadOnlyList<IReadOnlyList<Vector3>> welded)
    {
        var connected = new HashSet<EdgeKey>();
        for (var index = 0; index < areas.Count; index++)
        {
            var connections = areas[index].Connections;
            if (connections is null)
                continue;

            var corners = welded[index];
            for (var edge = 0; edge < corners.Count && edge < connections.Length; edge++)
            {
                if (connections[edge].Length == 0)
                    continue;
                connected.Add(EdgeKey.From(corners[edge], corners[(edge + 1) % corners.Count]));
            }
        }

        var faces = new List<NavFace>(welded.Count);
        foreach (var corners in welded)
        {
            var exposed = new List<bool>(corners.Count);
            for (var edge = 0; edge < corners.Count; edge++)
            {
                var key = EdgeKey.From(corners[edge], corners[(edge + 1) % corners.Count]);
                exposed.Add(!connected.Contains(key));
            }

            if (NormalizeFace(corners, exposed) is { } face)
                faces.Add(face);
        }
        return faces;
    }

    /// <summary>
    /// Drops repeated corners and winds the face counter-clockwise, carrying each edge's exposed
    /// flag with it. Returns <c>null</c> for a face that collapses below three distinct corners.
    /// </summary>
    private static NavFace? NormalizeFace(IReadOnlyList<Vector3> corners, IReadOnlyList<bool> exposedEdges)
    {
        var keptCorners = new List<Vector3>(corners.Count);
        var keptEdges = new List<bool>(corners.Count);
        for (var index = 0; index < corners.Count; index++)
        {
            if (keptCorners.Count > 0 && VertexKey.From(keptCorners[^1]) == VertexKey.From(corners[index]))
            {
                // The repeated corner's outgoing edge replaces the degenerate one leading into it.
                keptEdges[^1] = exposedEdges[index];
                continue;
            }
            keptCorners.Add(corners[index]);
            keptEdges.Add(exposedEdges[index]);
        }

        if (keptCorners.Count > 1 && VertexKey.From(keptCorners[0]) == VertexKey.From(keptCorners[^1]))
        {
            keptCorners.RemoveAt(keptCorners.Count - 1);
            keptEdges.RemoveAt(keptEdges.Count - 1);
        }

        if (keptCorners.Count < 3)
            return null;

        if (SignedArea(keptCorners) < 0f)
        {
            keptCorners.Reverse();
            // Edge k of the reversed ring is edge (count - 2 - k) of the original, walked backwards.
            var count = keptEdges.Count;
            var reversed = new List<bool>(count);
            for (var index = 0; index < count; index++)
                reversed.Add(keptEdges[(((count - 2 - index) % count) + count) % count]);
            keptEdges = reversed;
        }

        return new NavFace(keptCorners, keptEdges);
    }

    /// <summary>
    /// Inserts a neighbouring area's corner into any edge that merely passes through it. A small
    /// area's corner routinely lands part-way along a larger area's edge, and without the split the
    /// two sides offset independently and tear the wedge-shaped holes seen in the radar.
    /// </summary>
    internal static void SplitSharedEdges(IReadOnlyList<NavFace> faces)
    {
        var cells = new Dictionary<VertexKey, List<Vector3>>();
        foreach (var face in faces)
        {
            foreach (var corner in face.Corners)
            {
                var key = VertexKey.Snap(corner, SplitCellSize);
                if (!cells.TryGetValue(key, out var bucket))
                {
                    bucket = [];
                    cells[key] = bucket;
                }
                if (!bucket.Any(existing => VertexKey.From(existing) == VertexKey.From(corner)))
                    bucket.Add(corner);
            }
        }

        foreach (var face in faces)
        {
            for (var index = 0; index < face.Corners.Count; index++)
            {
                var start = face.Corners[index];
                var end = face.Corners[(index + 1) % face.Corners.Count];
                var crossings = CornersOnEdge(cells, start, end);
                if (crossings.Count == 0)
                    continue;

                face.Corners.InsertRange(index + 1, crossings);
                face.ExposedEdges.InsertRange(index + 1, Enumerable.Repeat(face.ExposedEdges[index], crossings.Count));
                index += crossings.Count;
            }
        }
    }

    private static List<Vector3> CornersOnEdge(
        Dictionary<VertexKey, List<Vector3>> cells,
        Vector3 start,
        Vector3 end)
    {
        var direction = new Vector2(end.X - start.X, end.Y - start.Y);
        var lengthSquared = direction.LengthSquared();
        if (lengthSquared < 1f)
            return [];

        var startKey = VertexKey.Snap(start, SplitCellSize);
        var endKey = VertexKey.Snap(end, SplitCellSize);
        var found = new List<(float Parameter, Vector3 Corner)>();
        for (var x = Math.Min(startKey.X, endKey.X) - 1; x <= Math.Max(startKey.X, endKey.X) + 1; x++)
        {
            for (var y = Math.Min(startKey.Y, endKey.Y) - 1; y <= Math.Max(startKey.Y, endKey.Y) + 1; y++)
            {
                for (var z = Math.Min(startKey.Z, endKey.Z) - 1; z <= Math.Max(startKey.Z, endKey.Z) + 1; z++)
                {
                    if (!cells.TryGetValue(new VertexKey(x, y, z), out var bucket))
                        continue;

                    foreach (var corner in bucket)
                    {
                        var parameter =
                            Vector2.Dot(new Vector2(corner.X - start.X, corner.Y - start.Y), direction) / lengthSquared;
                        if (parameter is <= 0.001f or >= 0.999f)
                            continue;
                        var onEdge = new Vector2(start.X, start.Y) + (direction * parameter);
                        if (Vector2.Distance(onEdge, new Vector2(corner.X, corner.Y)) > SplitTolerance)
                            continue;
                        if (MathF.Abs(start.Z + ((end.Z - start.Z) * parameter) - corner.Z) > SplitTolerance)
                            continue;
                        found.Add((parameter, corner));
                    }
                }
            }
        }

        found.Sort((left, right) => left.Parameter.CompareTo(right.Parameter));
        return [.. found.Select(crossing => crossing.Corner)];
    }

    private static void Validate(NavMeshRadarRequest request)
    {
        if (!File.Exists(request.VpkPath))
            throw new FileNotFoundException("The addon VPK was not found.", request.VpkPath);
        if (!File.Exists(request.MainVmapPath))
            throw new FileNotFoundException("The addon VMAP was not found.", request.MainVmapPath);
        if (request.Offset < 0f || !float.IsFinite(request.Offset))
            throw new ArgumentOutOfRangeException(nameof(request), "Offset must be a finite non-negative number.");
        if (string.IsNullOrWhiteSpace(request.MaterialPath))
            throw new ArgumentException("A radar material path is required.", nameof(request));
    }

    internal static List<IReadOnlyList<Vector3>> MergeBakedSamples(IReadOnlyList<Vector3> positions)
    {
        ArgumentNullException.ThrowIfNull(positions);

        var patches = new List<BakedPatch>();
        foreach (var layer in positions.Distinct().GroupBy(position => position.Z).OrderBy(layer => layer.Key))
            MergeBakedLayer(layer, patches);

        MergeSlopedBakedPatches(patches);
        return
        [
            .. patches
                .OrderBy(patch => patch.Plane.HeightAt(patch.MinimumX, patch.MinimumY))
                .ThenBy(patch => patch.MinimumX)
                .ThenBy(patch => patch.MinimumY)
                .Select(patch => patch.ToFace()),
        ];
    }

    internal static List<IReadOnlyList<Vector3>> SampleQuads(IReadOnlyList<Vector3> positions)
    {
        ArgumentNullException.ThrowIfNull(positions);

        var faces = new List<IReadOnlyList<Vector3>>(positions.Count);
        foreach (var position in positions.Distinct())
        {
            var z = position.Z + SurfaceLift;
            var minX = position.X - BakedHalfSize;
            var maxX = position.X + BakedHalfSize;
            var minY = position.Y - BakedHalfSize;
            var maxY = position.Y + BakedHalfSize;
            faces.Add(
            [
                new Vector3(minX, minY, z),
                new Vector3(maxX, minY, z),
                new Vector3(maxX, maxY, z),
                new Vector3(minX, maxY, z),
            ]);
        }
        return faces;
    }

    internal static List<IReadOnlyList<Vector3>> CollapseBakedFacesIntoNgons(
        IReadOnlyList<IReadOnlyList<Vector3>> faces) => BakedFaceNgonCollapser.Collapse(faces);

    private static RadarGeometry ReadBakedGeometry(
        string vpkPath,
        string mapName,
        bool collapseFaces,
        bool collapseFacesIntoNgons)
    {
        var entryPath = $"maps/{mapName}/baked_bomb_damage.vdata_c";
        var bytes = ReadEntry(vpkPath, entryPath);
        using var resource = new Resource { FileName = entryPath };
        using var stream = new MemoryStream(bytes, writable: false);
        resource.Read(stream);
        if (resource.DataBlock is not BombDamage bombDamage)
            throw new InvalidDataException($"'{entryPath}' is not a baked bomb-damage resource.");

        var faces = collapseFaces || collapseFacesIntoNgons
            ? MergeBakedSamples(bombDamage.Positions)
            : SampleQuads(bombDamage.Positions);
        if (collapseFacesIntoNgons)
            faces = CollapseBakedFacesIntoNgons(faces);

        return new RadarGeometry(
            bombDamage.Positions.Length,
            faces);
    }

    private static RadarGeometry ReadOffsetNavGeometry(string vpkPath, string mapName, float offset)
    {
        var entryPath = $"maps/{mapName}.nav";
        var bytes = ReadEntry(vpkPath, entryPath);
        var navMesh = new NavMeshFile();
        using var stream = new MemoryStream(bytes, writable: false);
        navMesh.Read(stream);

        if (navMesh.Areas.Count == 0)
            return new RadarGeometry(0, []);

        var hullIndex = navMesh.Areas.Values.Min(area => area.HullIndex);
        var areas = navMesh.Areas.Values
            .Where(area => area.HullIndex == hullIndex && area.Corners.Length >= 3)
            .OrderBy(area => area.AreaId)
            .ToList();
        var welded = WeldPolygons([.. areas.Select(area => (IReadOnlyList<Vector3>)area.Corners)]);
        var faces = BuildNavFaces(areas, welded);
        var normalized = faces
            .Select(face => (IReadOnlyList<Vector3>)face.Corners)
            .ToList();
        var rings = offset > 0f
            ? OffsetPolygonsIndependently(normalized, offset)
            : normalized;
        return new RadarGeometry(areas.Count, Triangulate(rings));
    }

    /// <summary>
    /// Fans every ring into triangles and drops the slivers. A NAV quad has four independent corner
    /// heights, so it is almost never planar; a triangle always is. That removes at a stroke every
    /// failure that non-planarity causes downstream — faces normalled the wrong way and flipped out
    /// of sight, and rings folded into bowties by the offset.
    /// </summary>
    internal static List<IReadOnlyList<Vector3>> Triangulate(IReadOnlyList<IReadOnlyList<Vector3>> rings)
    {
        ArgumentNullException.ThrowIfNull(rings);

        var triangles = new List<IReadOnlyList<Vector3>>(rings.Sum(ring => Math.Max(ring.Count - 2, 0)));
        foreach (var ring in rings)
        {
            // NAV areas are convex, and the corners the T-junction split adds sit on existing edges,
            // so a fan from the first corner stays inside the ring.
            for (var index = 1; index + 1 < ring.Count; index++)
            {
                IReadOnlyList<Vector3> triangle = [ring[0], ring[index], ring[index + 1]];
                if (MathF.Abs(SignedArea(triangle)) < TriangleMinimumArea)
                    continue;
                triangles.Add(triangle);
            }
        }
        return triangles;
    }

    private static byte[] ReadEntry(string vpkPath, string entryPath)
    {
        using var index = new VpkIndex();
        index.MountVpk(vpkPath);
        return index.TryReadBytes(entryPath)
            ?? throw new FileNotFoundException($"The VPK does not contain '{entryPath}'.", entryPath);
    }

    private static string GeneratedPath(string mainVmapPath)
    {
        var directory = Path.GetDirectoryName(mainVmapPath)
            ?? throw new InvalidDataException("The main VMAP has no parent directory.");
        var mapName = Path.GetFileNameWithoutExtension(mainVmapPath);
        return Path.Combine(directory, $"{mapName}_generated_radar.vmap");
    }

    private static int WriteGeneratedMap(
        string mainVmapPath,
        string generatedPath,
        string materialPath,
        IReadOnlyList<IReadOnlyList<Vector3>> faces)
    {
        var generated = VmapDocument.LoadInMemory(mainVmapPath);
        generated.ClearWorldChildren();
        generated.ClearEditorState();
        generated.Root["isprefab"] = true;
        generated.Model.PrefixAttributes["map_asset_references"] = new StringArray { materialPath };

        var meshCount = 0;
        for (var start = 0; start < faces.Count; start += FacesPerMesh)
        {
            var count = Math.Min(FacesPerMesh, faces.Count - start);
            var chunk = new List<IReadOnlyList<Vector3>>(count);
            for (var index = 0; index < count; index++)
                chunk.Add(faces[start + index]);

            meshCount++;
            generated.WorldChildren.Add(VmapPolygonMeshBuilder.Build(
                generated.Model,
                chunk,
                materialPath,
                1000 + meshCount,
                $"generated_radar_{meshCount:00}"));
        }

        var tempPath = $"{generatedPath}.{Guid.NewGuid():N}.tmp";
        try
        {
            generated.Model.Save(tempPath, "binary", 9);
            File.Move(tempPath, generatedPath, overwrite: true);
        }
        finally
        {
            if (File.Exists(tempPath))
                File.Delete(tempPath);
        }

        return meshCount;
    }

    private static (bool ReferenceAdded, string? BackupPath) EnsurePrefabReference(
        string mainVmapPath,
        string targetMapPath)
    {
        var main = VmapDocument.LoadInMemory(mainVmapPath);
        var hasPrefab = HasPrefab(main.WorldChildren, targetMapPath);
        var referenceAdded = EnsureAssetReference(main.Model, targetMapPath);
        if (hasPrefab && !referenceAdded)
            return (false, null);

        var backupPath = VmapBackup.Backup(mainVmapPath);
        if (!hasPrefab)
        {
            main.WorldChildren.Add(BuildPrefab(
                main.Model,
                NextNodeId(main.WorldChildren),
                targetMapPath));
        }
        main.Save();
        return (!hasPrefab, backupPath);
    }

    private static bool HasPrefab(ElementArray children, string targetMapPath)
    {
        foreach (var child in children)
        {
            if (!string.Equals(child.ClassName, "CMapPrefab", StringComparison.Ordinal)
                || !child.ContainsKey("targetMapPath")
                || child["targetMapPath"] is not string existing)
            {
                continue;
            }

            if (string.Equals(existing.Replace('\\', '/'), targetMapPath, StringComparison.OrdinalIgnoreCase))
                return true;
        }

        return false;
    }

    private static bool EnsureAssetReference(DM model, string targetMapPath)
    {
        if (model.PrefixAttributes.TryGetValue("map_asset_references", out var value)
            && value is StringArray references)
        {
            foreach (var reference in references)
            {
                if (string.Equals(reference.Replace('\\', '/'), targetMapPath, StringComparison.OrdinalIgnoreCase))
                    return false;
            }

            references.Add(targetMapPath);
            return true;
        }

        model.PrefixAttributes["map_asset_references"] = new StringArray { targetMapPath };
        return true;
    }

    private static Element BuildPrefab(DM model, int nodeId, string targetMapPath)
    {
        var transformPin = new Element(model, "transformPin", null, "DmElement");
        transformPin["referenceName"] = "";
        transformPin["targetReferenceID"] = 0UL;
        transformPin["offsetOrigin"] = Vector3.Zero;
        transformPin["offsetAngles"] = new QAngle(0, 0, 0);
        transformPin["pinAngles"] = true;
        transformPin["twoWay"] = false;

        var plugs = new Element(model, "", null, "DmePlugList");
        plugs["names"] = new StringArray();
        plugs["dataTypes"] = new IntArray();
        plugs["plugTypes"] = new IntArray();
        plugs["descriptions"] = new StringArray();

        var prefab = new Element(model, "Generated Radar", null, "CMapPrefab");
        prefab["nodeID"] = nodeId;
        prefab["referenceID"] = RandomReferenceId();
        prefab["children"] = new ElementArray();
        prefab["variableTargetKeys"] = new StringArray();
        prefab["variableNames"] = new StringArray();
        prefab["relayPlugData"] = plugs;
        prefab["connectionsData"] = new ElementArray();
        prefab["target"] = null;
        prefab["variableOverrideNames"] = new StringArray();
        prefab["variableOverrideValues"] = new StringArray();
        prefab["origin"] = Vector3.Zero;
        prefab["angles"] = new QAngle(0, 0, 0);
        prefab["scales"] = Vector3.One;
        prefab["transformLocked"] = false;
        prefab["transformPin"] = transformPin;
        prefab["force_hidden"] = false;
        prefab["editorOnly"] = false;
        prefab["customVisGroup"] = "";
        prefab["randomSeed"] = 0;
        prefab["tintColor"] = new Color(255, 255, 255, 255);
        prefab["visexclude"] = false;
        prefab["targetMapPath"] = targetMapPath;
        prefab["targetName"] = "";
        prefab["fixupEntityNames"] = true;
        prefab["useTargetNameAsPrefix"] = false;
        prefab["loadIfNested"] = true;
        prefab["prefabRuntimeEntity"] = false;
        prefab["loadAtRuntime"] = true;
        return prefab;
    }

    private static int NextNodeId(ElementArray children)
    {
        var max = 0;
        foreach (var child in children)
        {
            if (child.ContainsKey("nodeID") && child["nodeID"] is int nodeId)
                max = Math.Max(max, nodeId);
        }
        return max + 1;
    }

    private static ulong RandomReferenceId()
    {
        Span<byte> bytes = stackalloc byte[sizeof(ulong)];
        Random.Shared.NextBytes(bytes);
        return BitConverter.ToUInt64(bytes);
    }

    private static Vector2 OutwardNormal(Vector3 start, Vector3 end, float signedArea)
    {
        var edge = new Vector2(end.X - start.X, end.Y - start.Y);
        if (edge.LengthSquared() < 0.000001f)
            return Vector2.Zero;
        edge = Vector2.Normalize(edge);
        return signedArea > 0f
            ? new Vector2(edge.Y, -edge.X)
            : new Vector2(-edge.Y, edge.X);
    }

    private static void MergeBakedLayer(
        IEnumerable<Vector3> positions,
        List<BakedPatch> patches)
    {
        var layer = positions.ToList();
        if (layer.Count == 0)
            return;

        var events = new SortedDictionary<float, List<BakedSweepEvent>>();
        foreach (var position in layer)
        {
            var interval = new BakedInterval(
                position.Y - BakedHalfSize,
                position.Y + BakedHalfSize);
            AddBakedEvent(events, position.X - BakedHalfSize, new BakedSweepEvent(interval, Add: true));
            AddBakedEvent(events, position.X + BakedHalfSize, new BakedSweepEvent(interval, Add: false));
        }

        var eventGroups = events.ToArray();
        var activeIntervals = new Dictionary<BakedInterval, int>();
        var openRectangles = new Dictionary<BakedInterval, float>();
        var previousX = eventGroups[0].Key;
        ApplyBakedEvents(activeIntervals, eventGroups[0].Value);

        for (var index = 1; index < eventGroups.Length; index++)
        {
            var currentX = eventGroups[index].Key;
            UpdateOpenRectangles(
                openRectangles,
                UnionIntervals(activeIntervals.Keys),
                previousX,
                layer,
                patches);
            ApplyBakedEvents(activeIntervals, eventGroups[index].Value);
            previousX = currentX;
        }

        UpdateOpenRectangles(
            openRectangles,
            [],
            previousX,
            layer,
            patches);
    }

    private static void AddBakedEvent(
        SortedDictionary<float, List<BakedSweepEvent>> events,
        float x,
        BakedSweepEvent sweepEvent)
    {
        if (!events.TryGetValue(x, out var atX))
        {
            atX = [];
            events[x] = atX;
        }
        atX.Add(sweepEvent);
    }

    private static void ApplyBakedEvents(
        Dictionary<BakedInterval, int> activeIntervals,
        IEnumerable<BakedSweepEvent> events)
    {
        foreach (var sweepEvent in events)
        {
            var count = activeIntervals.GetValueOrDefault(sweepEvent.Interval);
            if (sweepEvent.Add)
            {
                activeIntervals[sweepEvent.Interval] = count + 1;
            }
            else if (count <= 1)
            {
                activeIntervals.Remove(sweepEvent.Interval);
            }
            else
            {
                activeIntervals[sweepEvent.Interval] = count - 1;
            }
        }
    }

    private static List<BakedInterval> UnionIntervals(IEnumerable<BakedInterval> intervals)
    {
        var ordered = intervals
            .OrderBy(interval => interval.Minimum)
            .ThenBy(interval => interval.Maximum)
            .ToList();
        if (ordered.Count == 0)
            return [];

        var union = new List<BakedInterval>();
        var current = ordered[0];
        foreach (var next in ordered.Skip(1))
        {
            if (next.Minimum <= current.Maximum + 0.001f)
            {
                current = current with { Maximum = MathF.Max(current.Maximum, next.Maximum) };
                continue;
            }

            union.Add(current);
            current = next;
        }
        union.Add(current);
        return union;
    }

    private static void UpdateOpenRectangles(
        Dictionary<BakedInterval, float> openRectangles,
        IReadOnlyCollection<BakedInterval> currentIntervals,
        float x,
        IReadOnlyList<Vector3> layer,
        List<BakedPatch> patches)
    {
        var current = currentIntervals.ToHashSet();
        foreach (var interval in openRectangles.Keys.Where(interval => !current.Contains(interval)).ToArray())
        {
            var startX = openRectangles[interval];
            if (x > startX + BakedMergeTolerance)
            {
                var samples = layer
                    .Where(position => SampleOverlaps(
                        position,
                        startX,
                        x,
                        interval.Minimum,
                        interval.Maximum))
                    .ToList();
                patches.Add(new BakedPatch(
                    startX,
                    x,
                    interval.Minimum,
                    interval.Maximum,
                    new BakedPlane(0f, 0f, layer[0].Z),
                    samples));
            }
            openRectangles.Remove(interval);
        }

        foreach (var interval in current)
            openRectangles.TryAdd(interval, x);
    }

    /// <summary>
    /// Joins adjacent horizontal strips when all of their source samples lie on one gentle plane.
    /// Baked bomb-damage data stores a ramp as one flat sample row per height, so merging exact Z
    /// layers alone leaves the staircase-like ribbons visible in Hammer.
    /// </summary>
    private static void MergeSlopedBakedPatches(List<BakedPatch> patches)
    {
        while (MergeSlopedBakedPatchPass(patches))
        {
        }
    }

    private static bool MergeSlopedBakedPatchPass(List<BakedPatch> patches)
    {
        var starts = new Dictionary<BakedMergeEdge, List<int>>();
        for (var index = 0; index < patches.Count; index++)
        {
            var patch = patches[index];
            AddBakedPatchStart(starts, BakedEdge(patch, axis: 0, useMaximum: false), index);
            AddBakedPatchStart(starts, BakedEdge(patch, axis: 1, useMaximum: false), index);
        }

        var candidates = new List<BakedMergeCandidate>();
        for (var first = 0; first < patches.Count; first++)
        {
            for (var axis = 0; axis < 2; axis++)
            {
                var edge = BakedEdge(patches[first], axis, useMaximum: true);
                if (!starts.TryGetValue(edge, out var continuations))
                    continue;

                foreach (var second in continuations)
                {
                    if (first == second || !TryMergeBakedPatches(patches[first], patches[second], out var merged, out var error))
                        continue;

                    var slopeSquared = (merged.Plane.XGradient * merged.Plane.XGradient)
                        + (merged.Plane.YGradient * merged.Plane.YGradient);
                    candidates.Add(new BakedMergeCandidate(first, second, merged, error, slopeSquared));
                }
            }
        }

        if (candidates.Count == 0)
            return false;

        candidates.Sort((left, right) =>
        {
            var error = left.MaximumError.CompareTo(right.MaximumError);
            if (error != 0)
                return error;
            var slope = left.SlopeSquared.CompareTo(right.SlopeSquared);
            if (slope != 0)
                return slope;
            var first = left.First.CompareTo(right.First);
            return first != 0 ? first : left.Second.CompareTo(right.Second);
        });

        var consumed = new bool[patches.Count];
        var mergedPatches = new List<BakedPatch>();
        foreach (var candidate in candidates)
        {
            if (consumed[candidate.First] || consumed[candidate.Second])
                continue;
            consumed[candidate.First] = true;
            consumed[candidate.Second] = true;
            mergedPatches.Add(candidate.Patch);
        }

        for (var index = 0; index < patches.Count; index++)
        {
            if (!consumed[index])
                mergedPatches.Add(patches[index]);
        }

        patches.Clear();
        patches.AddRange(mergedPatches);
        return true;
    }

    private static bool TryMergeBakedPatches(
        BakedPatch first,
        BakedPatch second,
        out BakedPatch merged,
        out float maximumError)
    {
        merged = null!;
        maximumError = float.PositiveInfinity;

        var samples = first.Samples.Concat(second.Samples).Distinct().ToList();
        if (!TryFitBakedPlane(samples, out var plane, out maximumError))
            return false;

        merged = new BakedPatch(
            MathF.Min(first.MinimumX, second.MinimumX),
            MathF.Max(first.MaximumX, second.MaximumX),
            MathF.Min(first.MinimumY, second.MinimumY),
            MathF.Max(first.MaximumY, second.MaximumY),
            plane,
            samples);
        return true;
    }

    private static bool TryFitBakedPlane(
        IReadOnlyList<Vector3> samples,
        out BakedPlane plane,
        out float maximumError)
    {
        var mean = samples.Aggregate(Vector3.Zero, (sum, sample) => sum + sample) / samples.Count;
        var xx = 0f;
        var xy = 0f;
        var yy = 0f;
        var xz = 0f;
        var yz = 0f;
        foreach (var sample in samples)
        {
            var x = sample.X - mean.X;
            var y = sample.Y - mean.Y;
            var z = sample.Z - mean.Z;
            xx += x * x;
            xy += x * y;
            yy += y * y;
            xz += x * z;
            yz += y * z;
        }

        float xGradient;
        float yGradient;
        var determinant = (xx * yy) - (xy * xy);
        if (MathF.Abs(determinant) > BakedMergeTolerance)
        {
            xGradient = ((xz * yy) - (yz * xy)) / determinant;
            yGradient = ((yz * xx) - (xz * xy)) / determinant;
        }
        else if (xx >= yy && xx > BakedMergeTolerance)
        {
            xGradient = xz / xx;
            yGradient = 0f;
        }
        else if (yy > BakedMergeTolerance)
        {
            xGradient = 0f;
            yGradient = yz / yy;
        }
        else
        {
            xGradient = 0f;
            yGradient = 0f;
        }

        if ((xGradient * xGradient) + (yGradient * yGradient) > BakedMaximumSlope * BakedMaximumSlope)
        {
            plane = default;
            maximumError = float.PositiveInfinity;
            return false;
        }

        var fittedPlane = new BakedPlane(
            xGradient,
            yGradient,
            mean.Z - (xGradient * mean.X) - (yGradient * mean.Y));
        maximumError = samples.Max(sample => MathF.Abs(fittedPlane.HeightAt(sample.X, sample.Y) - sample.Z));
        plane = fittedPlane;
        return maximumError <= BakedPlanarTolerance;
    }

    private static bool SampleOverlaps(
        Vector3 sample,
        float minimumX,
        float maximumX,
        float minimumY,
        float maximumY) =>
        sample.X + BakedHalfSize > minimumX + BakedMergeTolerance
        && sample.X - BakedHalfSize < maximumX - BakedMergeTolerance
        && sample.Y + BakedHalfSize > minimumY + BakedMergeTolerance
        && sample.Y - BakedHalfSize < maximumY - BakedMergeTolerance;

    private static void AddBakedPatchStart(
        Dictionary<BakedMergeEdge, List<int>> starts,
        BakedMergeEdge edge,
        int patchIndex)
    {
        if (!starts.TryGetValue(edge, out var indices))
        {
            indices = [];
            starts[edge] = indices;
        }
        indices.Add(patchIndex);
    }

    private static BakedMergeEdge BakedEdge(BakedPatch patch, int axis, bool useMaximum)
    {
        return axis == 0
            ? new BakedMergeEdge(
                axis,
                BakedCoordinate(patch.MinimumY),
                BakedCoordinate(patch.MaximumY),
                BakedCoordinate(useMaximum ? patch.MaximumX : patch.MinimumX))
            : new BakedMergeEdge(
                axis,
                BakedCoordinate(patch.MinimumX),
                BakedCoordinate(patch.MaximumX),
                BakedCoordinate(useMaximum ? patch.MaximumY : patch.MinimumY));
    }

    private static int BakedCoordinate(float value) => (int)MathF.Round(value / BakedMergeTolerance);

    private static float SignedArea(IReadOnlyList<Vector3> polygon)
    {
        var signedArea = 0f;
        for (var index = 0; index < polygon.Count; index++)
        {
            var next = polygon[(index + 1) % polygon.Count];
            signedArea += (polygon[index].X * next.Y) - (next.X * polygon[index].Y);
        }
        return signedArea;
    }

    private static Vector2 MiterShift(IReadOnlyList<Vector2> normals, float offset)
    {
        if (offset == 0f || normals.Count == 0)
            return Vector2.Zero;
        if (normals.Count == 1)
            return normals[0] * offset;

        var combined = Vector2.Zero;
        foreach (var normal in normals)
            combined += normal;
        if (combined.LengthSquared() < 0.000001f)
            return normals[0] * offset;

        var direction = Vector2.Normalize(combined);
        var denominator = normals
            .Select(normal => Vector2.Dot(direction, normal))
            .Where(dot => dot > 0.05f)
            .DefaultIfEmpty(1f)
            .Min();
        var distance = MathF.Min(offset / denominator, offset * 2f);
        return direction * distance;
    }
}
