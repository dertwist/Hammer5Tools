using Hammer5Tools.Core.Format.Snapshots;

namespace Hammer5Tools.Core.Tests;

public sealed class NativeBinaryTests
{
    [Test]
    public async Task RoundTripsSnapshotWithoutTextEncoding()
    {
        var source = new SnapshotDocument([
            new SnapshotChannel("position", "position_3d", [[1f, 2f, 3f], [4f, 5f, 6f]]),
            new SnapshotChannel("radius", "generic_float", [[2f], [3f]]),
        ]);

        var payload = NativeBinary.Create(NativeBinaryMessage.SnapshotDocument,
            writer => SnapshotBinarySerializer.Write(writer, source));
        var reader = NativeBinaryReader.Open(payload, NativeBinaryMessage.SnapshotDocument);
        var result = SnapshotBinarySerializer.Read(ref reader);
        reader.EnsureFinished();

        await Assert.That(result.Streams[0].Values[1]).IsEquivalentTo(new[] { 4f, 5f, 6f });
        await Assert.That(result.Streams[1].Values[0]).IsEquivalentTo(new[] { 2f });
    }

    [Test]
    public async Task RejectsPayloadsWithTrailingBytes()
    {
        var payload = NativeBinary.Create(NativeBinaryMessage.TextResult, writer => writer.WriteString("ok"));
        var invalid = new byte[payload.Length + 1];
        payload.CopyTo(invalid, 0);

        await Assert.That(() => NativeBinaryReader.Open(invalid, NativeBinaryMessage.TextResult))
            .Throws<InvalidDataException>();
    }
}
