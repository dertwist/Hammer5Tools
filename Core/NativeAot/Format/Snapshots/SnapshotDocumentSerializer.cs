using System.Text.Json;

using Hammer5Tools.Core.Format.SmartProps;

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

        using var json = JsonDocument.Parse(SmartPropDocumentSerializer.DeserializeText(text));
        var root = json.RootElement.GetProperty("stream_data");
        var declaredCount = root.GetProperty("num_values").GetInt32();
        var streams = new List<SnapshotChannel>();
        foreach (var stream in root.GetProperty("streams").EnumerateArray())
        {
            var name = stream.GetProperty("name").GetString() ?? string.Empty;
            var type = stream.GetProperty("type").GetString() ?? string.Empty;
            var width = GetWidth(type);
            var values = new List<float[]>();
            foreach (var value in stream.GetProperty("values").EnumerateArray())
            {
                values.Add(ReadValue(value, width));
            }
            if (width != 0 && values.Count != declaredCount)
            {
                throw new InvalidDataException($"Snapshot stream '{name}' contains {values.Count} values; expected {declaredCount}.");
            }
            streams.Add(new SnapshotChannel(name, type, values));
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

    private static float[] ReadValue(JsonElement value, int width)
    {
        if (width == 1)
        {
            return [value.GetSingle()];
        }
        if (value.ValueKind != JsonValueKind.Array)
        {
            throw new InvalidDataException($"Expected an array with {width} components.");
        }
        var result = value.EnumerateArray().Select(component => component.GetSingle()).ToArray();
        if (result.Length != width)
        {
            throw new InvalidDataException($"Expected {width} components, found {result.Length}.");
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
