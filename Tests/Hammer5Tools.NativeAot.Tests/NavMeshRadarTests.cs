using System.Numerics;

using Datamodel;
using Hammer5Tools.Core.Format.NavMesh;
using Hammer5Tools.Core.Format.Vmap;
using DM = Datamodel.Datamodel;

namespace Hammer5Tools.Core.Tests;

public sealed class NavMeshRadarTests
{
    [Test]
    public async Task ExpandsCounterClockwisePolygonByRequestedOffset()
    {
        Vector3[] square =
        [
            new(0, 0, 12),
            new(100, 0, 12),
            new(100, 100, 12),
            new(0, 100, 12),
        ];

        var expanded = NavMeshRadarGenerator.OffsetPolygon(square, 16f);

        await Assert.That(expanded[0].X).IsEqualTo(-16f).Within(0.001f);
        await Assert.That(expanded[0].Y).IsEqualTo(-16f).Within(0.001f);
        await Assert.That(expanded[1].X).IsEqualTo(116f).Within(0.001f);
        await Assert.That(expanded[1].Y).IsEqualTo(-16f).Within(0.001f);
        await Assert.That(expanded[2].X).IsEqualTo(116f).Within(0.001f);
        await Assert.That(expanded[2].Y).IsEqualTo(116f).Within(0.001f);
        await Assert.That(expanded[3].X).IsEqualTo(-16f).Within(0.001f);
        await Assert.That(expanded[3].Y).IsEqualTo(116f).Within(0.001f);
        await Assert.That(expanded.All(point => MathF.Abs(point.Z - 12f) < 0.001f)).IsTrue();
    }

    [Test]
    public async Task ExpandsClockwisePolygonOutward()
    {
        Vector3[] square =
        [
            new(0, 0, 0),
            new(0, 100, 0),
            new(100, 100, 0),
            new(100, 0, 0),
        ];

        var expanded = NavMeshRadarGenerator.OffsetPolygon(square, 8f);

        await Assert.That(expanded.Min(point => point.X)).IsEqualTo(-8f).Within(0.001f);
        await Assert.That(expanded.Max(point => point.X)).IsEqualTo(108f).Within(0.001f);
        await Assert.That(expanded.Min(point => point.Y)).IsEqualTo(-8f).Within(0.001f);
        await Assert.That(expanded.Max(point => point.Y)).IsEqualTo(108f).Within(0.001f);
    }

    [Test]
    public async Task OffsetPreservesOriginalCornerHeights()
    {
        Vector3[] unevenPolygon =
        [
            new(0, 0, 10),
            new(100, 0, 20),
            new(100, 100, 80),
            new(0, 100, 30),
        ];

        var expanded = NavMeshRadarGenerator.OffsetPolygon(unevenPolygon, 16f);

        await Assert.That(expanded.Select(point => point.Z)).IsEquivalentTo(
            unevenPolygon.Select(point => point.Z));
    }

    [Test]
    public async Task WeldSnapsDriftedCornersOfNeighbouringAreasTogether()
    {
        IReadOnlyList<IReadOnlyList<Vector3>> areas =
        [
            new Vector3[] { new(0, 0, 4), new(10, 0, 4), new(10, 10, 4), new(0, 10, 4) },
            new Vector3[] { new(10.4f, 0.3f, 4.2f), new(20, 0, 4), new(20, 10, 4), new(9.7f, 9.6f, 3.8f) },
        ];

        var welded = NavMeshRadarGenerator.WeldPolygons(areas);

        await Assert.That(welded[1][0]).IsEqualTo(welded[0][1]);
        await Assert.That(welded[1][3]).IsEqualTo(welded[0][2]);
        await Assert.That(welded[0][1].X).IsEqualTo(10.2f).Within(0.001f);
        await Assert.That(welded[0][1].Y).IsEqualTo(0.15f).Within(0.001f);
        await Assert.That(welded[0][1].Z).IsEqualTo(4.1f).Within(0.001f);
        await Assert.That(welded[1][1]).IsEqualTo(new Vector3(20, 0, 4));
    }

    [Test]
    public async Task WeldKeepsSeparateClustersThatShareASpatialBucket()
    {
        IReadOnlyList<IReadOnlyList<Vector3>> areas =
        [
            new Vector3[] { new(-0.49f, -0.49f, -0.49f), new(10, 0, 0), new(0, 10, 0) },
            new Vector3[] { new(0.49f, 0.49f, 0.49f), new(20, 0, 0), new(0, 20, 0) },
            new Vector3[] { new(-0.4f, -0.4f, -0.4f), new(30, 0, 0), new(0, 30, 0) },
        ];

        var welded = NavMeshRadarGenerator.WeldPolygons(areas);

        await Assert.That(welded[0][0]).IsEqualTo(welded[2][0]);
        await Assert.That(welded[0][0]).IsNotEqualTo(welded[1][0]);
    }

    [Test]
    public async Task WeldDoesNotCollapseNearbyVerticalLayersOutsideTolerance()
    {
        IReadOnlyList<IReadOnlyList<Vector3>> areas =
        [
            new Vector3[] { new(0, 0, 0), new(10, 0, 0), new(0, 10, 0) },
            new Vector3[] { new(0, 0, 1.1f), new(10, 0, 1.1f), new(0, 10, 1.1f) },
        ];

        var welded = NavMeshRadarGenerator.WeldPolygons(areas);

        await Assert.That(welded[0][0]).IsNotEqualTo(welded[1][0]);
    }

    [Test]
    public async Task NavOffsetMovesOnlyBoundaryAndKeepsSharedVerticesConnected()
    {
        IReadOnlyList<IReadOnlyList<Vector3>> areas =
        [
            new Vector3[] { new(0, 0, 4), new(10, 0, 4), new(10, 10, 4), new(0, 10, 4) },
            new Vector3[] { new(10, 0, 4), new(20, 0, 4), new(20, 10, 4), new(10, 10, 4) },
        ];

        var expanded = NavMeshRadarGenerator.OffsetWeldedPolygons(areas, 2f);

        await Assert.That(expanded[0][0].X).IsEqualTo(-2f).Within(0.001f);
        await Assert.That(expanded[0][0].Y).IsEqualTo(-2f).Within(0.001f);
        await Assert.That(expanded[0][0].Z).IsEqualTo(4f);
        await Assert.That(expanded[0][1]).IsEqualTo(expanded[1][0]);
        await Assert.That(expanded[0][1].X).IsEqualTo(10f).Within(0.001f);
        await Assert.That(expanded[0][1].Y).IsEqualTo(-2f).Within(0.001f);
        await Assert.That(expanded[0][2]).IsEqualTo(expanded[1][3]);
        await Assert.That(expanded[0][2].X).IsEqualTo(10f).Within(0.001f);
        await Assert.That(expanded[0][2].Y).IsEqualTo(12f).Within(0.001f);
        await Assert.That(expanded[1][2].X).IsEqualTo(22f).Within(0.001f);
        await Assert.That(expanded[1][2].Y).IsEqualTo(12f).Within(0.001f);
    }

    [Test]
    public async Task IndependentOffsetExpandsEveryGeometryElement()
    {
        IReadOnlyList<IReadOnlyList<Vector3>> areas =
        [
            new Vector3[] { new(0, 0, 4), new(10, 0, 4), new(10, 10, 4), new(0, 10, 4) },
            new Vector3[] { new(10, 0, 4), new(20, 0, 4), new(20, 10, 4), new(10, 10, 4) },
        ];

        var expanded = NavMeshRadarGenerator.OffsetPolygonsIndependently(areas, 2f);

        await Assert.That(expanded.Count).IsEqualTo(areas.Count);
        for (var index = 0; index < areas.Count; index++)
        {
            await Assert.That(expanded[index].Zip(areas[index]).All(pair => pair.First != pair.Second)).IsTrue();
            await Assert.That(SignedArea(expanded[index])).IsGreaterThan(SignedArea(areas[index]));
        }
        await Assert.That(expanded[0].Max(point => point.X)).IsEqualTo(12f).Within(0.001f);
        await Assert.That(expanded[1].Min(point => point.X)).IsEqualTo(8f).Within(0.001f);
    }

    [Test]
    public async Task BakedSamplesOnOneLayerBecomeOneNonOverlappingRectangle()
    {
        Vector3[] samples =
        [
            new(0, 0, 15),
            new(10, 0, 15),
            new(10, 0, 15),
        ];

        var faces = NavMeshRadarGenerator.MergeBakedSamples(samples);

        await Assert.That(faces).HasSingleItem();
        await Assert.That(faces[0][0]).IsEqualTo(new Vector3(-12, -12, 16));
        await Assert.That(faces[0][1]).IsEqualTo(new Vector3(22, -12, 16));
        await Assert.That(faces[0][2]).IsEqualTo(new Vector3(22, 12, 16));
        await Assert.That(faces[0][3]).IsEqualTo(new Vector3(-12, 12, 16));
    }

    [Test]
    public async Task BakedSamplesOnDifferentHeightLayersRemainSeparate()
    {
        Vector3[] samples =
        [
            new(0, 0, 15),
            new(0, 0, 25),
        ];

        var faces = NavMeshRadarGenerator.MergeBakedSamples(samples);

        await Assert.That(faces.Count).IsEqualTo(2);
        await Assert.That(faces.Select(face => face[0].Z)).IsEquivalentTo([16f, 26f]);
    }

    [Test]
    public async Task BakedSamplesOnAPlaneCollapseAcrossHeightRows()
    {
        Vector3[] samples =
        [
            new(0, 0, 0),
            new(24, 0, 0),
            new(48, 0, 0),
            new(0, 24, 6),
            new(24, 24, 6),
            new(48, 24, 6),
            new(0, 48, 12),
            new(24, 48, 12),
            new(48, 48, 12),
        ];

        var faces = NavMeshRadarGenerator.MergeBakedSamples(samples);

        await Assert.That(faces).HasSingleItem();
        await Assert.That(faces[0][0]).IsEqualTo(new Vector3(-12, -12, -2));
        await Assert.That(faces[0][1]).IsEqualTo(new Vector3(60, -12, -2));
        await Assert.That(faces[0][2]).IsEqualTo(new Vector3(60, 60, 16));
        await Assert.That(faces[0][3]).IsEqualTo(new Vector3(-12, 60, 16));
    }

    [Test]
    public async Task BakedSamplesDoNotCollapseAcrossASteepHeightBreak()
    {
        Vector3[] samples =
        [
            new(0, 0, 0),
            new(24, 0, 0),
            new(0, 24, 40),
            new(24, 24, 40),
        ];

        var faces = NavMeshRadarGenerator.MergeBakedSamples(samples);

        await Assert.That(faces.Count).IsEqualTo(2);
        await Assert.That(faces.Select(face => face[0].Z)).IsEquivalentTo([1f, 41f]);
    }

    [Test]
    public async Task CoplanarConnectedFacesCollapseIntoOneNgon()
    {
        IReadOnlyList<IReadOnlyList<Vector3>> faces =
        [
            Rectangle(0, 0, 20, 10, 4),
            Rectangle(0, 10, 10, 20, 4),
        ];

        var collapsed = NavMeshRadarGenerator.CollapseBakedFacesIntoNgons(faces);

        await Assert.That(collapsed).HasSingleItem();
        await Assert.That(collapsed[0].Count).IsEqualTo(6);
        await Assert.That(SignedArea(collapsed[0])).IsEqualTo(300f).Within(0.001f);
        await Assert.That(collapsed[0].All(point => point.Z == 4f)).IsTrue();
    }

    [Test]
    public async Task NgonCollapseKeepsDisconnectedFacesSeparate()
    {
        IReadOnlyList<IReadOnlyList<Vector3>> faces =
        [
            Rectangle(0, 0, 10, 10, 4),
            Rectangle(20, 0, 30, 10, 4),
        ];

        var collapsed = NavMeshRadarGenerator.CollapseBakedFacesIntoNgons(faces);

        await Assert.That(collapsed.Count).IsEqualTo(2);
    }

    [Test]
    public async Task NgonCollapseKeepsAdjacentHeightLayersSeparate()
    {
        IReadOnlyList<IReadOnlyList<Vector3>> faces =
        [
            Rectangle(0, 0, 10, 10, 4),
            Rectangle(10, 0, 20, 10, 8),
        ];

        var collapsed = NavMeshRadarGenerator.CollapseBakedFacesIntoNgons(faces);

        await Assert.That(collapsed.Count).IsEqualTo(2);
        await Assert.That(collapsed.Select(face => face[0].Z)).IsEquivalentTo([4f, 8f]);
    }

    [Test]
    public async Task NgonCollapseDoesNotFillHoles()
    {
        IReadOnlyList<IReadOnlyList<Vector3>> frame =
        [
            Rectangle(0, 0, 30, 10, 4),
            Rectangle(0, 20, 30, 30, 4),
            Rectangle(0, 10, 10, 20, 4),
            Rectangle(20, 10, 30, 20, 4),
        ];

        var collapsed = NavMeshRadarGenerator.CollapseBakedFacesIntoNgons(frame);

        await Assert.That(collapsed.Count).IsEqualTo(4);
        await Assert.That(collapsed.Sum(face => MathF.Abs(SignedArea(face)))).IsEqualTo(800f).Within(0.001f);
    }

    [Test]
    public async Task PolygonMeshUsesOneInteriorAndBoundaryHalfEdgePerSide()
    {
        var document = new DM("vmap", 40);
        IReadOnlyList<IReadOnlyList<Vector3>> faces =
        [
            new Vector3[]
            {
                new(0, 0, 1),
                new(32, 0, 1),
                new(32, 32, 1),
                new(0, 32, 1),
            },
        ];

        var node = VmapPolygonMeshBuilder.Build(
            document,
            faces,
            "materials/radgen/radgen_path.vmat",
            10,
            "radar");
        var mesh = (Element)node["meshData"]!;
        var edgeFaces = (IntArray)mesh["edgeFaceIndices"]!;
        var faceEdges = (IntArray)mesh["faceEdgeIndices"]!;

        await Assert.That(node.ClassName).IsEqualTo("CMapMesh");
        await Assert.That(mesh.ClassName).IsEqualTo("CDmePolygonMesh");
        await Assert.That(edgeFaces.Count).IsEqualTo(8);
        await Assert.That(edgeFaces.Count(index => index == 0)).IsEqualTo(4);
        await Assert.That(edgeFaces.Count(index => index == -1)).IsEqualTo(4);
        await Assert.That(faceEdges.Count).IsEqualTo(1);
    }

    [Test]
    public async Task PolygonMeshOrientsWalkableFacesUpward()
    {
        var document = new DM("vmap", 40);
        IReadOnlyList<IReadOnlyList<Vector3>> clockwiseFace =
        [
            new Vector3[]
            {
                new(0, 0, 1),
                new(0, 32, 1),
                new(32, 32, 1),
                new(32, 0, 1),
            },
        ];

        var node = VmapPolygonMeshBuilder.Build(
            document,
            clockwiseFace,
            "materials/radgen/radgen_path.vmat",
            10,
            "radar");
        var mesh = (Element)node["meshData"]!;
        var faceVertexData = (Element)mesh["faceVertexData"]!;
        var streams = (ElementArray)faceVertexData["streams"]!;
        var normalStream = streams.Single(stream => stream["standardAttributeName"] as string == "normal");
        var normals = (Vector3Array)normalStream["data"]!;

        await Assert.That(normals[0].Z).IsEqualTo(1f).Within(0.001f);
    }

    [Test]
    public async Task PolygonMeshKeepsASliverCorneredFaceFacingUpward()
    {
        var document = new DM("vmap", 40);
        // Counter-clockwise, so walkable — but corners 0, 1 and 2 are nearly collinear, and fanning
        // the normal from corner 0 across just those three points aims it downward. Weighting the
        // whole ring is what keeps this face from being flipped away out of sight.
        IReadOnlyList<IReadOnlyList<Vector3>> sliverFace =
        [
            new Vector3[]
            {
                new(0, 0, 1),
                new(100, 1, 1),
                new(200, 0, 1),
                new(100, 100, 1),
            },
        ];

        var node = VmapPolygonMeshBuilder.Build(
            document,
            sliverFace,
            "materials/radgen/radgen_path.vmat",
            10,
            "radar");
        var mesh = (Element)node["meshData"]!;
        var streams = (ElementArray)((Element)mesh["faceVertexData"]!)["streams"]!;
        var normalStream = streams.Single(stream => stream["standardAttributeName"] as string == "normal");
        var normals = (Vector3Array)normalStream["data"]!;
        var positionStream = ((ElementArray)((Element)mesh["vertexData"]!)["streams"]!).Single();
        var positions = (Vector3Array)positionStream["data"]!;

        await Assert.That(normals[0].Z).IsEqualTo(1f).Within(0.001f);
        await Assert.That(positions[0]).IsEqualTo(new Vector3(0, 0, 1));
        await Assert.That(positions[1]).IsEqualTo(new Vector3(100, 1, 1));
    }

    [Test]
    public async Task PolygonMeshGeneratesValidTopologyForAdjacentFaces()
    {
        var document = new DM("vmap", 40);
        IReadOnlyList<IReadOnlyList<Vector3>> faces =
        [
            new Vector3[] { new(0, 0, 1), new(32, 0, 1), new(32, 32, 1), new(0, 32, 1) },
            new Vector3[] { new(32, 0, 1), new(64, 0, 1), new(64, 32, 1), new(32, 32, 1) },
        ];

        var node = VmapPolygonMeshBuilder.Build(
            document,
            faces,
            "materials/radgen/radgen_path.vmat",
            10,
            "radar");
        var mesh = (Element)node["meshData"]!;
        var vertexDataIndices = (IntArray)mesh["vertexDataIndices"]!;
        var edgeFaces = (IntArray)mesh["edgeFaceIndices"]!;
        var opposites = (IntArray)mesh["edgeOppositeIndices"]!;
        var edgeData = (Element)mesh["edgeData"]!;
        var faceEdges = (IntArray)mesh["faceEdgeIndices"]!;

        await Assert.That(vertexDataIndices.Count).IsEqualTo(8);
        await Assert.That(edgeFaces.Count).IsEqualTo(16);
        await Assert.That(edgeFaces.Count(face => face == -1)).IsEqualTo(8);
        await Assert.That(faceEdges.Count).IsEqualTo(2);
        await Assert.That((int)edgeData["size"]!).IsEqualTo(8);
        await Assert.That(Enumerable.Range(0, opposites.Count)
            .All(edge => opposites[edge] == (edge ^ 1))).IsTrue();
    }

    [Test]
    public async Task SampleQuadsBuildsIndividualQuadsForBombDamagePositions()
    {
        Vector3[] samples =
        [
            new(0, 0, 10),
            new(24, 0, 10),
        ];

        var quads = NavMeshRadarGenerator.SampleQuads(samples);

        await Assert.That(quads.Count).IsEqualTo(2);
        await Assert.That(quads[0].Count).IsEqualTo(4);
        await Assert.That(quads[1].Count).IsEqualTo(4);
        await Assert.That(quads[0][0]).IsEqualTo(new Vector3(-12, -12, 11));
        await Assert.That(quads[0][2]).IsEqualTo(new Vector3(12, 12, 11));
        await Assert.That(quads[1][0]).IsEqualTo(new Vector3(12, -12, 11));
        await Assert.That(quads[1][2]).IsEqualTo(new Vector3(36, 12, 11));
    }

    [Test]
    public async Task OffsetNeverTurnsAnAreaSmallerThanTheOffsetInsideOut()
    {
        // An isolated 8-unit triangle: every edge is an exposed boundary, so a 16-unit
        // offset would flip it through itself and vacate its own footprint.
        IReadOnlyList<IReadOnlyList<Vector3>> areas =
        [
            new Vector3[] { new(0, 0, 0), new(8, 0, 0), new(4, 7, 0) },
        ];

        var expanded = NavMeshRadarGenerator.OffsetWeldedPolygons(areas, 16f);

        await Assert.That(SignedArea(expanded[0])).IsGreaterThanOrEqualTo(SignedArea(areas[0]));
    }

    [Test]
    public async Task OffsetStillGrowsAreasComfortablyLargerThanTheOffset()
    {
        IReadOnlyList<IReadOnlyList<Vector3>> areas =
        [
            new Vector3[] { new(0, 0, 0), new(400, 0, 0), new(400, 400, 0), new(0, 400, 0) },
        ];

        var expanded = NavMeshRadarGenerator.OffsetWeldedPolygons(areas, 16f);

        await Assert.That(SignedArea(expanded[0])).IsEqualTo(432f * 432f).Within(0.1f);
    }

    [Test]
    public async Task SplitInsertsANeighboursCornerIntoTheEdgeItLandsOn()
    {
        // Two small areas abut the lower edge of a wide one, meeting it at (10, 0) — a corner that
        // exists on their rings but not on the wide area's. Left unsplit, the two sides offset
        // independently and tear open.
        var wide = Face([new(0, 0, 0), new(20, 0, 0), new(20, 10, 0), new(0, 10, 0)]);
        var left = Face([new(0, -10, 0), new(10, -10, 0), new(10, 0, 0), new(0, 0, 0)]);
        var right = Face([new(10, -10, 0), new(20, -10, 0), new(20, 0, 0), new(10, 0, 0)]);

        NavMeshRadarGenerator.SplitSharedEdges([wide, left, right]);

        await Assert.That(wide.Corners.Count).IsEqualTo(5);
        await Assert.That(wide.Corners[1]).IsEqualTo(new Vector3(10, 0, 0));
        await Assert.That(wide.ExposedEdges.Count).IsEqualTo(5);
        await Assert.That(left.Corners.Count).IsEqualTo(4);
    }

    [Test]
    public async Task TriangulateFansEachRingAndKeepsItsFootprint()
    {
        IReadOnlyList<IReadOnlyList<Vector3>> rings =
        [
            new Vector3[] { new(0, 0, 4), new(100, 0, 4), new(100, 100, 4), new(0, 100, 4) },
        ];

        var triangles = NavMeshRadarGenerator.Triangulate(rings);

        await Assert.That(triangles.Count).IsEqualTo(2);
        await Assert.That(triangles.All(triangle => triangle.Count == 3)).IsTrue();
        await Assert.That(triangles.Sum(SignedArea)).IsEqualTo(100f * 100f).Within(0.001f);
        await Assert.That(triangles.All(triangle => SignedArea(triangle) > 0f)).IsTrue();
    }

    [Test]
    public async Task TriangulateDropsTheSliversASplitEdgeLeavesBehind()
    {
        // (50, 0) is a corner the T-junction split inserted, so it lies on the first edge and fans
        // into a zero-area triangle that must not reach the vmap.
        IReadOnlyList<IReadOnlyList<Vector3>> rings =
        [
            new Vector3[] { new(0, 0, 0), new(50, 0, 0), new(100, 0, 0), new(100, 100, 0), new(0, 100, 0) },
        ];

        var triangles = NavMeshRadarGenerator.Triangulate(rings);

        await Assert.That(triangles.Count).IsEqualTo(2);
        await Assert.That(triangles.Sum(SignedArea)).IsEqualTo(100f * 100f).Within(0.001f);
    }

    private static NavMeshRadarGenerator.NavFace Face(List<Vector3> corners) =>
        new(corners, [.. Enumerable.Repeat(true, corners.Count)]);

    private static IReadOnlyList<Vector3> Rectangle(
        float minimumX,
        float minimumY,
        float maximumX,
        float maximumY,
        float z) =>
    [
        new(minimumX, minimumY, z),
        new(maximumX, minimumY, z),
        new(maximumX, maximumY, z),
        new(minimumX, maximumY, z),
    ];

    private static float SignedArea(IReadOnlyList<Vector3> polygon)
    {
        var area = 0f;
        for (var index = 0; index < polygon.Count; index++)
        {
            var next = polygon[(index + 1) % polygon.Count];
            area += (polygon[index].X * next.Y) - (next.X * polygon[index].Y);
        }
        return area / 2f;
    }
}
