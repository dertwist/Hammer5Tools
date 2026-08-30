using System.Text;
using System.Text.Json;

using Hammer5Tools.Core.Format.SmartProps;

namespace Hammer5Tools.Core.Format.Snapshots;

/// <summary>VSnap experiments: reads and writes Source 2 particle snapshots in KeyValues3 text form.</summary>
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

        using var output = new MemoryStream();
        using (var writer = new Utf8JsonWriter(output))
        {
            writer.WriteStartObject();
            writer.WriteStartObject("stream_data");
            writer.WriteNumber("num_values", document.Count);
            writer.WriteStartArray("streams");
            foreach (var stream in document.Streams)
            {
                writer.WriteStartObject();
                writer.WriteString("name", stream.Name);
                writer.WriteString("type", stream.Type);
                writer.WriteStartArray("values");
                foreach (var value in stream.Values)
                {
                    if (stream.Type == "generic_float")
                    {
                        writer.WriteNumberValue(value[0]);
                    }
                    else
                    {
                        writer.WriteStartArray();
                        foreach (var component in value)
                        {
                            writer.WriteNumberValue(component);
                        }
                        writer.WriteEndArray();
                    }
                }
                writer.WriteEndArray();
                writer.WriteEndObject();
            }
            writer.WriteEndArray();
            writer.WriteEndObject();
            writer.WriteEndObject();
            writer.Flush();
        }
        return SmartPropDocumentSerializer.SerializeJson(Encoding.UTF8.GetString(output.ToArray()));
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
        "generic_float" => 1,
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
