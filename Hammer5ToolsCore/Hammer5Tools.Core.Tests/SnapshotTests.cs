using System.Numerics;

using Hammer5Tools.Core.Format.Snapshots;

namespace Hammer5Tools.Core.Tests;

public sealed class SnapshotTests
{
    [Test]
    public async Task RoundTripsStandardStreams()
    {
        var source = new SnapshotDocument([
            new SnapshotChannel("position", "position_3d", [[1f, 2f, 3f], [4f, 5f, 6f]]),
            new SnapshotChannel("radius", "generic_float", [[2f], [3f]]),
        ]);

        var text = SnapshotDocumentSerializer.Serialize(source);
        var result = SnapshotDocumentSerializer.DeserializeText(text);

        await Assert.That(result.Count).IsEqualTo(2);
        await Assert.That(result.Streams[0].Values[1][2]).IsEqualTo(6f);
        await Assert.That(text).Contains("stream_data");
    }

    [Test]
    public async Task RejectsStreamsTheEngineWouldDrop()
    {
        var unknownName = new SnapshotDocument([
            new SnapshotChannel("position", "position_3d", [[1f, 2f, 3f]]),
            new SnapshotChannel("parent_particle_id", "generic_float", [[7f]]),
        ]);
        var wrongType = new SnapshotDocument([
            new SnapshotChannel("trail_length", "generic_vector_3d", [[1f, 2f, 3f]]),
        ]);

        await Assert.That(() => SnapshotDocumentSerializer.Serialize(unknownName)).Throws<InvalidDataException>();
        await Assert.That(() => SnapshotDocumentSerializer.Serialize(wrongType)).Throws<InvalidDataException>();
    }

    [Test]
    public async Task GeneratedSnapshotsOnlyUseLoadableStreamNames()
    {
        var lightning = SnapshotGenerator.GenerateLightning(
            new Vector3(0f, 0f, 160f), new Vector3(120f, 30f, 0f), 24, 32f, 0.65f, 2, 4.5f, 840_388);

        foreach (var document in new[] { lightning, SnapshotGenerator.FromPositions([[0f, 0f, 0f], [5f, 0f, 0f]]) })
        {
            foreach (var stream in document.Streams)
            {
                await Assert.That(SnapshotAttributes.Find(stream.Name)).IsNotNull();
            }
        }
    }

    [Test]
    public async Task GeneratesDeterministicSphereOnRequestedRadius()
    {
        var result = SnapshotGenerator.GeneratePrimitive("sphere", 32, 64f);
        var positions = result.Streams[0].Values;

        await Assert.That(result.Count).IsEqualTo(32);
        await Assert.That(positions.All(point => MathF.Abs(new Vector3(point[0], point[1], point[2]).Length() - 64f) < 0.001f)).IsTrue();
    }

    [Test]
    public async Task TwoPointLightingCreatesColorChannel()
    {
        var source = SnapshotGenerator.FromPositions([[0f, 0f, 0f], [5f, 0f, 0f], [10f, 0f, 0f]]);
        var result = SnapshotGenerator.ApplyTwoPointLighting(source, 0, 2);
        var color = result.Streams.Single(stream => stream.Name == "color");

        await Assert.That(color.Values[0][2]).IsEqualTo(0.25f);
        await Assert.That(color.Values[2][2]).IsEqualTo(1f);
    }

    [Test]
    public async Task LightningGenerationIsDeterministicAndPreservesEndpoints()
    {
        var first = SnapshotGenerator.GenerateLightning(
            new Vector3(0f, 0f, 100f), new Vector3(20f, 10f, 0f), 64, 20f, 0.65f, 2, 4f, 1234);
        var second = SnapshotGenerator.GenerateLightning(
            new Vector3(0f, 0f, 100f), new Vector3(20f, 10f, 0f), 64, 20f, 0.65f, 2, 4f, 1234);
        var positions = first.Streams.Single(stream => stream.Name == "position").Values;
        var branchIds = first.Streams.Single(stream => stream.Name == "scratch_float").Values;
        var radii = first.Streams.Single(stream => stream.Name == "radius").Values;

        await Assert.That(SnapshotDocumentSerializer.Serialize(first))
            .IsEqualTo(SnapshotDocumentSerializer.Serialize(second));
        await Assert.That(positions[0]).IsEquivalentTo(new[] { 0f, 0f, 100f });
        await Assert.That(positions[63]).IsEquivalentTo(new[] { 20f, 10f, 0f });
        await Assert.That(branchIds.Select(value => value[0]).Distinct().Count()).IsGreaterThan(1);
        await Assert.That(radii[0][0]).IsGreaterThan(radii[63][0]);
    }

    [Test]
    public async Task RoundTripsAvailableDesktopFixtures()
    {
        var root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "particles");
        if (!Directory.Exists(root))
        {
            return;
        }

        var paths = Directory.EnumerateFiles(root, "*.vsnap", SearchOption.AllDirectories).ToArray();
        foreach (var path in paths)
        {
            var document = SnapshotDocumentSerializer.DeserializeText(await File.ReadAllTextAsync(path));
            var reparsed = SnapshotDocumentSerializer.DeserializeText(SnapshotDocumentSerializer.Serialize(document));
            await Assert.That(reparsed.Count).IsEqualTo(document.Count);
        }
        await Assert.That(paths.Length).IsGreaterThan(0);
    }
}
