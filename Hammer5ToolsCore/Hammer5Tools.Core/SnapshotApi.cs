using System.Buffers;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;

using Hammer5Tools.Core.Format.Snapshots;

namespace Hammer5Tools.Core;

/// <summary>NativeAOT ABI for Source 2 particle snapshot editing.</summary>
internal static unsafe class SnapshotApi
{
    [UnmanagedCallersOnly(EntryPoint = "h5t_vsnap_read_binary", CallConvs = [typeof(CallConvCdecl)])]
    public static int ReadBinary(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.InvokeBinary(output, outputLength, () => ReadBinaryPayload(request, requestLength));

    [UnmanagedCallersOnly(EntryPoint = "h5t_vsnap_serialize_binary", CallConvs = [typeof(CallConvCdecl)])]
    public static int SerializeBinary(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.InvokeBinary(output, outputLength, () => SerializeBinaryPayload(request, requestLength));

    [UnmanagedCallersOnly(EntryPoint = "h5t_vsnap_generate_binary", CallConvs = [typeof(CallConvCdecl)])]
    public static int GenerateBinary(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.InvokeBinary(output, outputLength, () => GenerateBinaryPayload(request, requestLength));

    [UnmanagedCallersOnly(EntryPoint = "h5t_vsnap_read_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int ReadJson(byte* text, int textLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => WriteJson(
            SnapshotDocumentSerializer.DeserializeText(NativeInterop.ReadUtf8(text, textLength))));

    [UnmanagedCallersOnly(EntryPoint = "h5t_vsnap_serialize_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int SerializeJson(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Encoding.UTF8.GetBytes(
            SnapshotDocumentSerializer.Serialize(ReadDocument(NativeInterop.ReadUtf8(request, requestLength)))));

    [UnmanagedCallersOnly(EntryPoint = "h5t_vsnap_generate_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int GenerateJson(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            using var json = JsonDocument.Parse(NativeInterop.ReadUtf8(request, requestLength));
            var root = json.RootElement;
            SnapshotDocument document;
            if (root.TryGetProperty("positions", out var positions))
            {
                document = SnapshotGenerator.FromPositions(positions.EnumerateArray()
                    .Select(ReadVector).ToArray());
            }
            else
            {
                document = SnapshotGenerator.GeneratePrimitive(
                    root.GetProperty("primitive").GetString()!,
                    root.GetProperty("count").GetInt32(),
                    root.GetProperty("size").GetSingle());
            }
            return WriteJson(document);
        });

    [UnmanagedCallersOnly(EntryPoint = "h5t_vsnap_light_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int ApplyLightingJson(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            using var json = JsonDocument.Parse(NativeInterop.ReadUtf8(request, requestLength));
            var root = json.RootElement;
            var document = ReadDocument(root.GetProperty("document"));
            return WriteJson(SnapshotGenerator.ApplyTwoPointLighting(
                document,
                root.GetProperty("firstIndex").GetInt32(),
                root.GetProperty("secondIndex").GetInt32()));
        });

    [UnmanagedCallersOnly(EntryPoint = "h5t_vsnap_lightning_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int GenerateLightningJson(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            using var json = JsonDocument.Parse(NativeInterop.ReadUtf8(request, requestLength));
            var root = json.RootElement;
            var start = ReadVector3(root.GetProperty("start"));
            var end = ReadVector3(root.GetProperty("end"));
            return WriteJson(SnapshotGenerator.GenerateLightning(
                start,
                end,
                root.GetProperty("pointCount").GetInt32(),
                root.GetProperty("roughness").GetSingle(),
                root.GetProperty("branchProbability").GetSingle(),
                root.GetProperty("recursionDepth").GetInt32(),
                root.GetProperty("radius").GetSingle(),
                root.GetProperty("seed").GetInt32()));
        });

    [UnmanagedCallersOnly(EntryPoint = "h5t_vsnap_attributes_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int AttributesJson(byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var buffer = new ArrayBufferWriter<byte>();
            using var writer = new Utf8JsonWriter(buffer);
            writer.WriteStartObject();
            writer.WriteStartArray("attributes");
            foreach (var attribute in SnapshotAttributes.All)
            {
                writer.WriteStartObject();
                writer.WriteString("name", attribute.Name);
                writer.WriteString("type", attribute.Type);
                writer.WriteNumber("attribute", attribute.Attribute);
                writer.WriteString("display", attribute.DisplayName);
                writer.WriteEndObject();
            }
            writer.WriteEndArray();
            writer.WriteStartObject("unnameable");
            foreach (var (display, index) in SnapshotAttributes.UnnameableAttributes)
            {
                writer.WriteNumber(display, index);
            }
            writer.WriteEndObject();
            writer.WriteEndObject();
            writer.Flush();
            return buffer.WrittenSpan.ToArray();
        });

    private static SnapshotDocument ReadDocument(string json)
    {
        using var document = JsonDocument.Parse(json);
        return ReadDocument(document.RootElement);
    }

    private static SnapshotDocument ReadDocument(JsonElement root)
    {
        var channels = root.GetProperty("streams").EnumerateArray().Select(stream => new SnapshotChannel(
            stream.GetProperty("name").GetString()!,
            stream.GetProperty("type").GetString()!,
            stream.GetProperty("values").EnumerateArray().Select(value => value.ValueKind == JsonValueKind.Array
                ? ReadVector(value)
                : new[] { value.GetSingle() }).ToArray())).ToArray();
        return new SnapshotDocument(channels);
    }

    private static float[] ReadVector(JsonElement value) => value.EnumerateArray()
        .Select(component => component.GetSingle()).ToArray();

    private static Vector3 ReadVector3(JsonElement value)
    {
        var components = ReadVector(value);
        if (components.Length != 3)
        {
            throw new InvalidDataException("Lightning endpoints must contain three components.");
        }
        return new Vector3(components[0], components[1], components[2]);
    }

    private static byte[] WriteJson(SnapshotDocument document)
    {
        var buffer = new ArrayBufferWriter<byte>();
        using var writer = new Utf8JsonWriter(buffer);
        writer.WriteStartObject();
        writer.WriteNumber("count", document.Count);
        writer.WriteStartArray("streams");
        foreach (var stream in document.Streams)
        {
            writer.WriteStartObject();
            writer.WriteString("name", stream.Name);
            writer.WriteString("type", stream.Type);
            writer.WriteStartArray("values");
            foreach (var value in stream.Values)
            {
                if (stream.Type is "generic_float" or "generic_int")
                {
                    writer.WriteNumberValue(value[0]);
                    continue;
                }
                writer.WriteStartArray();
                foreach (var component in value)
                {
                    writer.WriteNumberValue(component);
                }
                writer.WriteEndArray();
            }
            writer.WriteEndArray();
            writer.WriteEndObject();
        }
        writer.WriteEndArray();
        writer.WriteEndObject();
        writer.Flush();
        return buffer.WrittenSpan.ToArray();
    }

    private static byte[] ReadBinaryPayload(byte* request, int requestLength)
    {
        var reader = NativeBinary.Read(request, requestLength, NativeBinaryMessage.SnapshotTextRequest);
        var text = reader.ReadString();
        reader.EnsureFinished();
        var document = SnapshotDocumentSerializer.DeserializeText(text);
        return NativeBinary.Create(NativeBinaryMessage.SnapshotDocument,
            writer => SnapshotBinarySerializer.Write(writer, document));
    }

    private static byte[] SerializeBinaryPayload(byte* request, int requestLength)
    {
        var reader = NativeBinary.Read(request, requestLength, NativeBinaryMessage.SnapshotDocument);
        var document = SnapshotBinarySerializer.Read(ref reader);
        reader.EnsureFinished();
        var text = SnapshotDocumentSerializer.Serialize(document);
        return NativeBinary.Create(NativeBinaryMessage.TextResult, writer => writer.WriteString(text));
    }

    private static byte[] GenerateBinaryPayload(byte* request, int requestLength)
    {
        var reader = NativeBinary.Read(request, requestLength, NativeBinaryMessage.SnapshotGenerateRequest);
        var kind = reader.ReadByte();
        SnapshotDocument document;
        switch (kind)
        {
            case 0:
                document = SnapshotGenerator.GeneratePrimitive(
                    reader.ReadString(), reader.ReadInt32(), reader.ReadSingle());
                break;
            case 1:
                document = SnapshotGenerator.FromPositions(ReadPositions(ref reader));
                break;
            default:
                throw new InvalidDataException($"Unknown binary snapshot generation kind '{kind}'.");
        }
        reader.EnsureFinished();
        return NativeBinary.Create(NativeBinaryMessage.SnapshotDocument,
            writer => SnapshotBinarySerializer.Write(writer, document));
    }

    private static float[][] ReadPositions(ref NativeBinaryReader reader)
    {
        var count = reader.ReadInt32();
        if (count is < 0 or > 1_000_000)
        {
            throw new InvalidDataException("The binary snapshot position count is invalid.");
        }

        reader.Align(sizeof(float));
        var positions = new float[count][];
        for (var index = 0; index < count; index++)
        {
            positions[index] = [reader.ReadSingle(), reader.ReadSingle(), reader.ReadSingle()];
        }
        return positions;
    }
}
