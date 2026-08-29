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
    bool CollapseFaces = true);

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

/// <summary>Generates editable radar faces from compiled CS2 navigation data.</summary>
public static class NavMeshRadarGenerator
{
    private const int FacesPerMesh = 4096;
    private const float BakedHalfSize = 12f;
    private const float SurfaceLift = 1f;
    private const float WeldTolerance = 1f;

    private sealed record RadarGeometry(
        int SourceCount,
        List<IReadOnlyList<Vector3>> Faces);

    private readonly record struct BakedInterval(float Minimum, float Maximum);

    private readonly record struct BakedSweepEvent(BakedInterval Interval, bool Add);

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
                NavMeshRadarMode.BakedBombDamage => ReadBakedGeometry(request.VpkPath, mapName, request.CollapseFaces),
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

    /// <summary>Offsets only exposed NAV boundaries while preserving shared welded vertices.</summary>
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

        var boundaryNormals = new Dictionary<VertexKey, List<Vector2>>();
        foreach (var polygon in polygons)
        {
            var signedArea = SignedArea(polygon);
            for (var index = 0; index < polygon.Count; index++)
            {
                var start = polygon[index];
                var end = polygon[(index + 1) % polygon.Count];
                if (edgeCounts[EdgeKey.From(start, end)] != 1)
                    continue;

                var normal = OutwardNormal(start, end, signedArea);
                if (normal == Vector2.Zero)
                    continue;
                AddBoundaryNormal(boundaryNormals, VertexKey.From(start), normal);
                AddBoundaryNormal(boundaryNormals, VertexKey.From(end), normal);
            }
        }

        var shiftedVertices = new Dictionary<VertexKey, Vector3>();
        foreach (var polygon in polygons)
        {
            foreach (var point in polygon)
            {
                var key = VertexKey.From(point);
                if (shiftedVertices.ContainsKey(key))
                    continue;
                var shift = boundaryNormals.TryGetValue(key, out var normals)
                    ? MiterShift(normals, offset)
                    : Vector2.Zero;
                shiftedVertices[key] = new Vector3(point.X + shift.X, point.Y + shift.Y, point.Z);
            }
        }

        return
        [
            .. polygons.Select(polygon =>
                (IReadOnlyList<Vector3>)[.. polygon.Select(point => shiftedVertices[VertexKey.From(point)])]),
        ];
    }

    private static void AddBoundaryNormal(
        Dictionary<VertexKey, List<Vector2>> boundaryNormals,
        VertexKey vertex,
        Vector2 normal)
    {
        if (!boundaryNormals.TryGetValue(vertex, out var normals))
        {
            normals = [];
            boundaryNormals[vertex] = normals;
        }
        normals.Add(normal);
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

        var faces = new List<IReadOnlyList<Vector3>>();
        foreach (var layer in positions.Distinct().GroupBy(position => position.Z).OrderBy(layer => layer.Key))
            MergeBakedLayer(layer, faces);
        return faces;
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

    private static RadarGeometry ReadBakedGeometry(string vpkPath, string mapName, bool collapseFaces)
    {
        var entryPath = $"maps/{mapName}/baked_bomb_damage.vdata_c";
        var bytes = ReadEntry(vpkPath, entryPath);
        using var resource = new Resource { FileName = entryPath };
        using var stream = new MemoryStream(bytes, writable: false);
        resource.Read(stream);
        if (resource.DataBlock is not BombDamage bombDamage)
            throw new InvalidDataException($"'{entryPath}' is not a baked bomb-damage resource.");

        var faces = collapseFaces
            ? MergeBakedSamples(bombDamage.Positions)
            : SampleQuads(bombDamage.Positions);

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
        var normalizedFaces = new List<IReadOnlyList<Vector3>>(welded.Count);
        foreach (var polygon in welded)
        {
            var normalized = NormalizePolygon(polygon);
            if (normalized.Count >= 3)
                normalizedFaces.Add(normalized);
        }
        return new RadarGeometry(
            areas.Count,
            offset > 0f ? OffsetWeldedPolygons(normalizedFaces, offset) : normalizedFaces);
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
        return Path.Combine(directory, $"{mapName}_navmesh_radar.vmap");
    }

    private static int WriteGeneratedMap(
        string mainVmapPath,
        string generatedPath,
        string materialPath,
        IReadOnlyList<IReadOnlyList<Vector3>> faces)
    {
        var generated = VmapDocument.LoadInMemory(mainVmapPath);
        generated.ClearWorldChildren();
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
                $"navmesh_radar_{meshCount:00}"));
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

        var prefab = new Element(model, "NavMesh Radar", null, "CMapPrefab");
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
        prefab["targetName"] = "navmesh_radar";
        prefab["fixupEntityNames"] = false;
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
        List<IReadOnlyList<Vector3>> faces)
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
                layer[0].Z + SurfaceLift,
                faces);
            ApplyBakedEvents(activeIntervals, eventGroups[index].Value);
            previousX = currentX;
        }

        UpdateOpenRectangles(
            openRectangles,
            [],
            previousX,
            layer[0].Z + SurfaceLift,
            faces);
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
        float z,
        List<IReadOnlyList<Vector3>> faces)
    {
        var current = currentIntervals.ToHashSet();
        foreach (var interval in openRectangles.Keys.Where(interval => !current.Contains(interval)).ToArray())
        {
            var startX = openRectangles[interval];
            if (x > startX + 0.001f)
            {
                faces.Add(
                [
                    new Vector3(startX, interval.Minimum, z),
                    new Vector3(x, interval.Minimum, z),
                    new Vector3(x, interval.Maximum, z),
                    new Vector3(startX, interval.Maximum, z),
                ]);
            }
            openRectangles.Remove(interval);
        }

        foreach (var interval in current)
            openRectangles.TryAdd(interval, x);
    }

    private static IReadOnlyList<Vector3> NormalizePolygon(IReadOnlyList<Vector3> polygon)
    {
        var normalized = new List<Vector3>(polygon.Count);
        foreach (var corner in polygon)
        {
            if (normalized.Count == 0 || VertexKey.From(normalized[^1]) != VertexKey.From(corner))
                normalized.Add(corner);
        }
        if (normalized.Count > 1 && VertexKey.From(normalized[0]) == VertexKey.From(normalized[^1]))
            normalized.RemoveAt(normalized.Count - 1);
        if (normalized.Count < 3)
            return [];
        if (SignedArea(normalized) < 0f)
            normalized.Reverse();
        return normalized;
    }

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
