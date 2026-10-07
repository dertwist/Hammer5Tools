using System.Text;

using ValveKeyValue;
using ValveResourceFormat.Serialization.KeyValues;

namespace Hammer5Tools.Core.Format.Snapshots;

/// <summary>Reads and writes Source 2 particle snapshots in KeyValues3 text form.</summary>
public static class SnapshotDocumentSerializer
{
    /// <summary>Parses and validates a particle snapshot.</summary>
    public static SnapshotDocument DeserializeText(string text)
    {
        ArgumentNullException.ThrowIfNull(text);

        using var ms = new MemoryStream(Encoding.UTF8.GetBytes(text));
        var root = KVDocumentExtensions.ParseKV3(ms).Root["stream_data"];
        if (root is null)
        {
            throw new InvalidDataException("Missing 'stream_data' section in particle snapshot.");
        }

        var declaredCount = Convert.ToInt32(root["num_values"].Value);
        var streams = new List<SnapshotChannel>();
        var streamsNode = root["streams"];
        if (streamsNode is not null && streamsNode.IsArray)
        {
            foreach (var stream in streamsNode.AsArraySpan())
            {
                var name = stream["name"]?.ToString() ?? string.Empty;
                var type = stream["type"]?.ToString() ?? string.Empty;
                var width = GetWidth(type);
                var values = new List<float[]>();
                var valuesNode = stream["values"];
                if (valuesNode is not null && valuesNode.IsArray)
                {
                    foreach (var value in valuesNode.AsArraySpan())
                    {
                        values.Add(ReadValue(value, width));
                    }
                }
                if (width != 0 && values.Count != declaredCount)
                {
                    throw new InvalidDataException($"Snapshot stream '{name}' contains {values.Count} values; expected {declaredCount}.");
                }
                streams.Add(new SnapshotChannel(name, type, values));
            }
        }

        if (streams.Where(stream => stream.Type != "bone_index_and_weight")
            .Select(stream => stream.Values.Count).Distinct().Skip(1).Any())
        {
            throw new InvalidDataException("Snapshot streams do not have a common value count.");
        }
        return new SnapshotDocument(streams);
    }

    /// <summary>Serializes a particle snapshot as Valve-compatible KeyValues3 text.</summary>
    public static string Serialize(SnapshotDocument document)
    {
        ArgumentNullException.ThrowIfNull(document);
        Validate(document);

        // Built as KeyValues3 directly rather than via JSON: a JSON round trip cannot tell 0.0f
        // from 0, so every whole-valued sample came back out as a KV3 int. The engine's snapshot
        // loader wants doubles in a float stream and rejects the file, so the types have to
        // survive all the way to the writer.
        var streams = KVObject.Array(document.Streams.Count);
        foreach (var stream in document.Streams)
        {
            var entry = KVObject.Collection();
            entry["name"] = new KVObject(stream.Name);
            entry["type"] = new KVObject(stream.Type);
            var values = KVObject.Array(stream.Values.Count);
            foreach (var value in stream.Values)
            {
                if (stream.Type == "generic_int")
                {
                    // The compiler type-checks these five streams as ints and rejects a float.
                    values.Add(new KVObject((int)value[0]));
                    continue;
                }
                if (stream.Type == "generic_float")
                {
                    values.Add(new KVObject(value[0]));
                    continue;
                }
                var vector = KVObject.Array(value.Length);
                foreach (var component in value)
                {
                    vector.Add(new KVObject(component));
                }
                values.Add(vector);
            }
            entry["values"] = values;
            streams.Add(entry);
        }

        var streamData = KVObject.Collection();
        streamData["num_values"] = new KVObject(document.Count);
        streamData["streams"] = streams;
        var root = KVObject.Collection();
        root["stream_data"] = streamData;
        return root.ToKV3String();
    }

    private static float[] ReadValue(KVObject value, int width)
    {
        if (width == 1)
        {
            return [Convert.ToSingle(value.Value)];
        }
        if (!value.IsArray)
        {
            throw new InvalidDataException($"Expected an array with {width} components.");
        }
        var span = value.AsArraySpan();
        if (span.Length != width)
        {
            throw new InvalidDataException($"Expected {width} components, found {span.Length}.");
        }
        var result = new float[width];
        for (var i = 0; i < width; i++)
        {
            result[i] = Convert.ToSingle(span[i].Value);
        }
        return result;
    }

    private static int GetWidth(string type) => type switch
    {
        "position_3d" or "normal_3d" or "generic_vector_3d" => 3,
        "generic_float" or "generic_int" => 1,
        "bone_index_and_weight" => 0,
        _ => throw new InvalidDataException($"Unsupported snapshot stream type '{type}'."),
    };

    private static void Validate(SnapshotDocument document)
    {
        foreach (var stream in document.Streams)
        {
            SnapshotAttributes.ValidateStream(stream.Name, stream.Type);
            var width = GetWidth(stream.Type);
            if (width == 0 && stream.Values.Count == 0)
            {
                continue;
            }
            if (stream.Values.Count != document.Count || stream.Values.Any(value => value.Length != width))
            {
                throw new InvalidDataException($"Snapshot stream '{stream.Name}' has inconsistent values.");
            }
        }
    }
}
