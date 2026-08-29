using Datamodel;
using Hammer5Tools.Core.Format.NavMesh;
using Hammer5Tools.Core.Format.Vmap;

namespace Hammer5Tools.Core.Tests;

public sealed class NavMeshRadarTopologyScratchTests
{
    [Test]
    public async Task DiagnoseHammerAuthoredTopology()
    {
        const string vmapPath = @"Hammer5Tools\Presets\hammer5tools\content\maps\blockout_zoo.vmap";
        if (!File.Exists(vmapPath))
            return;

        var document = VmapDocument.LoadInMemory(vmapPath);
        var meshes = Enumerate(document.WorldChildren)
            .Where(node => node.ContainsKey("meshData") && node["meshData"] is Element)
            .Select(node => (Element)node["meshData"]!)
            .ToArray();
        var adjacentOpposites = 0;
        var nonAdjacentOpposites = 0;
        var badVertexFans = 0;
        foreach (var mesh in meshes)
        {
            var opposites = (IntArray)mesh["edgeOppositeIndices"]!;
            var vertexEdges = (IntArray)mesh["vertexEdgeIndices"]!;
            var edgeVertices = (IntArray)mesh["edgeVertexIndices"]!;
            var nextEdges = (IntArray)mesh["edgeNextIndices"]!;
            for (var edge = 0; edge < opposites.Count; edge++)
            {
                if (opposites[edge] == (edge ^ 1))
                    adjacentOpposites++;
                else
                    nonAdjacentOpposites++;
            }
            badVertexFans += Enumerable.Range(0, vertexEdges.Count)
                .Count(vertex => !VertexFanCloses(
                    vertex,
                    vertexEdges[vertex],
                    edgeVertices,
                    opposites,
                    nextEdges));
        }

        await Assert.That(badVertexFans).IsEqualTo(0);
        await Assert.That(nonAdjacentOpposites).IsEqualTo(0);
    }

    [Test]
    public async Task DiagnoseFirewatchTopology()
    {
        const string vpkPath = @"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo_addons\de_firewatch\maps\de_firewatch.vpk";
        const string sourceVmapPath = @"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_firewatch\maps\de_firewatch.vmap";
        if (!File.Exists(vpkPath) || !File.Exists(sourceVmapPath))
            return;

        var directory = Path.Combine(Path.GetTempPath(), $"Hammer5Tools-navmesh-topology-{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        try
        {
            var vmapPath = Path.Combine(directory, "de_firewatch.vmap");
            File.Copy(sourceVmapPath, vmapPath);
            var result = NavMeshRadarGenerator.Generate(new NavMeshRadarRequest(
                vpkPath,
                vmapPath,
                NavMeshRadarMode.NavMeshOffset,
                16f,
                "materials/radgen/radgen_path.vmat"));
            await Assert.That(result.IsSuccess).IsTrue();

            var generated = VmapDocument.LoadInMemory(result.Value!.GeneratedVmapPath);
            var mesh = (Element)generated.WorldChildren.Single()["meshData"]!;
            var vertexEdges = (IntArray)mesh["vertexEdgeIndices"]!;
            var edgeVertices = (IntArray)mesh["edgeVertexIndices"]!;
            var opposites = (IntArray)mesh["edgeOppositeIndices"]!;
            var nextEdges = (IntArray)mesh["edgeNextIndices"]!;
            var edgeFaces = (IntArray)mesh["edgeFaceIndices"]!;
            var faceEdges = (IntArray)mesh["faceEdgeIndices"]!;
            var badOpposites = 0;
            var badNextVertices = 0;
            var selfBoundaryNext = 0;
            var badVertexEdges = 0;
            var nonAdjacentOpposites = 0;

            for (var edge = 0; edge < edgeVertices.Count; edge++)
            {
                var opposite = opposites[edge];
                if (opposite < 0 || opposite >= edgeVertices.Count || opposites[opposite] != edge)
                {
                    badOpposites++;
                    continue;
                }
                if (opposite != (edge ^ 1))
                    nonAdjacentOpposites++;
                var next = nextEdges[edge];
                if (next < 0 || next >= edgeVertices.Count
                    || edgeVertices[opposites[next]] != edgeVertices[edge])
                {
                    badNextVertices++;
                }
                if (edgeFaces[edge] == -1 && next == edge)
                    selfBoundaryNext++;
            }

            for (var vertex = 0; vertex < vertexEdges.Count; vertex++)
            {
                var edge = vertexEdges[vertex];
                if (edge < 0 || edge >= edgeVertices.Count || edgeVertices[opposites[edge]] != vertex)
                    badVertexEdges++;
            }

            var badFaceRings = Enumerable.Range(0, faceEdges.Count)
                .Count(face => !RingCloses(faceEdges[face], face, nextEdges, edgeFaces));
            var badBoundaryRings = Enumerable.Range(0, edgeFaces.Count)
                .Where(edge => edgeFaces[edge] == -1)
                .Count(edge => !RingCloses(edge, -1, nextEdges, edgeFaces));
            var badVertexFans = Enumerable.Range(0, vertexEdges.Count)
                .Count(vertex => !VertexFanCloses(
                    vertex,
                    vertexEdges[vertex],
                    edgeVertices,
                    opposites,
                    nextEdges));
            var report = $"vertices={vertexEdges.Count}, edges={edgeVertices.Count}, faces={faceEdges.Count}, "
                + $"badOpposites={badOpposites}, badNextVertices={badNextVertices}, "
                + $"selfBoundaryNext={selfBoundaryNext}, badVertexEdges={badVertexEdges}, "
                + $"badFaceRings={badFaceRings}, badBoundaryRings={badBoundaryRings}, badVertexFans={badVertexFans}, "
                + $"nonAdjacentOpposites={nonAdjacentOpposites}";
            await Assert.That(report).IsEqualTo(
                $"vertices={vertexEdges.Count}, edges={edgeVertices.Count}, faces={faceEdges.Count}, "
                + "badOpposites=0, badNextVertices=0, selfBoundaryNext=0, badVertexEdges=0, "
                + "badFaceRings=0, badBoundaryRings=0, badVertexFans=0, nonAdjacentOpposites=0");
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    private static bool RingCloses(int start, int face, IntArray nextEdges, IntArray edgeFaces)
    {
        var edge = start;
        for (var count = 0; count <= nextEdges.Count; count++)
        {
            if (edge < 0 || edge >= nextEdges.Count || edgeFaces[edge] != face)
                return false;
            edge = nextEdges[edge];
            if (edge == start)
                return count >= 2;
        }
        return false;
    }

    private static bool VertexFanCloses(
        int vertex,
        int start,
        IntArray edgeVertices,
        IntArray opposites,
        IntArray nextEdges)
    {
        var expected = Enumerable.Range(0, edgeVertices.Count)
            .Where(edge => edgeVertices[opposites[edge]] == vertex)
            .ToHashSet();
        var visited = new HashSet<int>();
        var edge = start;
        while (visited.Add(edge))
        {
            if (!expected.Contains(edge))
                return false;
            edge = nextEdges[opposites[edge]];
        }
        return edge == start && visited.SetEquals(expected);
    }

    private static IEnumerable<Element> Enumerate(ElementArray children)
    {
        foreach (var child in children)
        {
            yield return child;
            if (child.ContainsKey("children") && child["children"] is ElementArray descendants)
            {
                foreach (var descendant in Enumerate(descendants))
                    yield return descendant;
            }
        }
    }
}
