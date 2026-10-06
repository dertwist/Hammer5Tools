namespace Hammer5Tools.Core.Format.Snapshots;

/// <summary>Compact binary transport for editable particle snapshot documents.</summary>
internal static class SnapshotBinarySerializer
{
    public static void Write(NativeBinaryWriter writer, SnapshotDocument document)
    {
        ArgumentNullException.ThrowIfNull(writer);
        ArgumentNullException.ThrowIfNull(document);

        var count = document.Count;
        writer.WriteInt32(count);
        writer.WriteInt32(document.Streams.Count);
        foreach (var stream in document.Streams)
        {
            var width = GetWidth(stream.Type);
            if (width == 0 && stream.Values.Count == 0)
            {
                writer.WriteString(stream.Name);
                writer.WriteString(stream.Type);
                writer.WriteInt32(0);
                continue;
            }

            if (stream.Values.Count != count || stream.Values.Any(value => value.Length != width))
            {
                throw new InvalidDataException($"Snapshot stream '{stream.Name}' has inconsistent values.");
            }

            writer.WriteString(stream.Name);
            writer.WriteString(stream.Type);
            writer.WriteInt32(stream.Values.Count);
            writer.Align(sizeof(float));
            foreach (var value in stream.Values)
            {
                foreach (var component in value)
                {
                    writer.WriteSingle(component);
                }
            }
        }
    }

    public static SnapshotDocument Read(ref NativeBinaryReader reader)
    {
        var count = ReadCount(ref reader, "snapshot value count");
        var streamCount = ReadCount(ref reader, "snapshot stream count");
        var streams = new List<SnapshotChannel>(streamCount);
        for (var streamIndex = 0; streamIndex < streamCount; streamIndex++)
        {
            var name = reader.ReadString();
            var type = reader.ReadString();
            var width = GetWidth(type);
            var valueCount = ReadCount(ref reader, $"snapshot stream '{name}' value count");
            if (width == 0 && valueCount == 0)
            {
                streams.Add(new SnapshotChannel(name, type, []));
                continue;
            }
            if (valueCount != count)
            {
                throw new InvalidDataException($"Snapshot stream '{name}' contains {valueCount} values; expected {count}.");
            }

            reader.Align(sizeof(float));
            var values = new List<float[]>(valueCount);
            for (var valueIndex = 0; valueIndex < valueCount; valueIndex++)
            {
                var value = new float[width];
                for (var component = 0; component < width; component++)
                {
                    value[component] = reader.ReadSingle();
                }
                values.Add(value);
            }
            streams.Add(new SnapshotChannel(name, type, values));
        }

        return new SnapshotDocument(streams);
    }

    private static int ReadCount(ref NativeBinaryReader reader, string name)
    {
        var count = reader.ReadInt32();
        if (count < 0 || count > 1_000_000)
        {
            throw new InvalidDataException($"The {name} is invalid.");
        }
        return count;
    }

    private static int GetWidth(string type) => type switch
    {
        "position_3d" or "normal_3d" or "generic_vector_3d" => 3,
        "generic_float" or "generic_int" => 1,
        "bone_index_and_weight" => 0,
        _ => throw new InvalidDataException($"Unsupported snapshot stream type '{type}'."),
    };
}
