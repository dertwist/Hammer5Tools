namespace Hammer5Tools.Core.Format.Snapshots;

/// <summary>One typed channel in a Source 2 particle snapshot.</summary>
public sealed record SnapshotChannel(string Name, string Type, IReadOnlyList<float[]> Values);

/// <summary>VSnap experiments: an editable Source 2 particle snapshot.</summary>
public sealed record SnapshotDocument(IReadOnlyList<SnapshotChannel> Streams)
{
    /// <summary>Gets the common number of values stored by every stream.</summary>
    public int Count => Streams.Count == 0 ? 0 : Streams[0].Values.Count;
}
