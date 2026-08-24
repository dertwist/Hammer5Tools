using System.Buffers;
using System.Collections.Concurrent;
using System.Globalization;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;

using Hammer5Tools.Core.SmartProps;

namespace Hammer5Tools.Native;

internal static unsafe class NativeApi
{
    private const int AbiVersion = 1;
    private static readonly ConcurrentDictionary<long, CancellationTokenSource> Cancellations = new();
    private static long NextCancellationId;

    [UnmanagedCallersOnly(EntryPoint = "h5t_core_abi_version", CallConvs = [typeof(CallConvCdecl)])]
    public static int GetAbiVersion() => AbiVersion;

    [UnmanagedCallersOnly(EntryPoint = "h5t_smartprop_evaluate_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int EvaluateSmartPropJson(
        byte* document,
        int documentLength,
        byte* nestedDocuments,
        int nestedDocumentsLength,
        int maximumDepth,
        int maximumModels,
        long cancellationId,
        byte** output,
        int* outputLength)
    {
        return Invoke(output, outputLength, () =>
        {
            var documentJson = ReadUtf8(document, documentLength);
            var options = new SmartPropEvaluationOptions(
                maximumDepth,
                maximumModels,
                GetCancellationToken(cancellationId));
            var result = nestedDocuments is null
                ? SmartPropEvaluator.EvaluateJson(documentJson, options)
                : SmartPropEvaluator.EvaluateJson(
                    documentJson,
                    ReadUtf8(nestedDocuments, nestedDocumentsLength),
                    options);
            return WriteEvaluationResult(result);
        });
    }

    [UnmanagedCallersOnly(EntryPoint = "h5t_core_create_cancellation", CallConvs = [typeof(CallConvCdecl)])]
    public static long CreateCancellation()
    {
        var id = Interlocked.Increment(ref NextCancellationId);
        Cancellations[id] = new CancellationTokenSource();
        return id;
    }

    [UnmanagedCallersOnly(EntryPoint = "h5t_core_cancel", CallConvs = [typeof(CallConvCdecl)])]
    public static int Cancel(long cancellationId)
    {
        if (!Cancellations.TryGetValue(cancellationId, out var cancellation))
            return -1;

        cancellation.Cancel();
        return 0;
    }

    [UnmanagedCallersOnly(EntryPoint = "h5t_core_release_cancellation", CallConvs = [typeof(CallConvCdecl)])]
    public static void ReleaseCancellation(long cancellationId)
    {
        if (Cancellations.TryRemove(cancellationId, out var cancellation))
            cancellation.Dispose();
    }

    [UnmanagedCallersOnly(EntryPoint = "h5t_smartprop_evaluate_expression", CallConvs = [typeof(CallConvCdecl)])]
    public static int EvaluateSmartPropExpression(
        byte* request,
        int requestLength,
        byte** output,
        int* outputLength)
    {
        return Invoke(output, outputLength, () =>
        {
            using var document = JsonDocument.Parse(ReadUtf8(request, requestLength));
            var root = document.RootElement;
            var variables = ReadVariables(root, "variables");
            var vectors = ReadVectors(root, "vectors");
            var context = new SmartPropContext(
                variables,
                vectors,
                GetInt32(root, "instanceIndex", 0),
                GetInt32(root, "instanceCount", 1),
                GetInt32(root, "randomSeed", 0),
                GetSingle(root, "linearScale", 1.0f));
            var value = SmartPropExpression.Evaluate(
                root.GetProperty("expression").GetString(),
                context,
                GetSingle(root, "default", 0.0f));
            return Encoding.UTF8.GetBytes(value.ToString("R", CultureInfo.InvariantCulture));
        });
    }

    [UnmanagedCallersOnly(EntryPoint = "h5t_smartprop_serialize_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int SerializeSmartPropJson(
        byte* document,
        int documentLength,
        byte** output,
        int* outputLength)
    {
        return Invoke(output, outputLength, () => Encoding.UTF8.GetBytes(
            SmartPropDocumentSerializer.SerializeJson(ReadUtf8(document, documentLength))));
    }

    [UnmanagedCallersOnly(EntryPoint = "h5t_smartprop_deserialize_text", CallConvs = [typeof(CallConvCdecl)])]
    public static int DeserializeSmartPropText(
        byte* text,
        int textLength,
        byte** output,
        int* outputLength)
    {
        return Invoke(output, outputLength, () => Encoding.UTF8.GetBytes(
            SmartPropDocumentSerializer.DeserializeText(ReadUtf8(text, textLength))));
    }

    [UnmanagedCallersOnly(EntryPoint = "h5t_core_release", CallConvs = [typeof(CallConvCdecl)])]
    public static void Release(void* memory)
    {
        NativeMemory.Free(memory);
    }

    private static int Invoke(byte** output, int* outputLength, Func<byte[]> operation)
    {
        if (output is null || outputLength is null)
            return -1;

        *output = null;
        *outputLength = 0;
        try
        {
            WriteOutput(operation(), output, outputLength);
            return 0;
        }
        catch (Exception exception)
        {
            WriteOutput(WriteNativeError(exception.Message), output, outputLength);
            return -2;
        }
    }

    private static string ReadUtf8(byte* input, int length)
    {
        if (input is null || length < 0)
            throw new ArgumentException("A valid UTF-8 input buffer is required.");

        return Encoding.UTF8.GetString(new ReadOnlySpan<byte>(input, length));
    }

    private static void WriteOutput(byte[] bytes, byte** output, int* outputLength)
    {
        var buffer = (byte*)NativeMemory.Alloc((nuint)bytes.Length + 1);
        bytes.CopyTo(new Span<byte>(buffer, bytes.Length));
        buffer[bytes.Length] = 0;
        *output = buffer;
        *outputLength = bytes.Length;
    }

    private static byte[] WriteEvaluationResult(SmartPropEvaluationResult result)
    {
        var buffer = new ArrayBufferWriter<byte>();
        using var writer = new Utf8JsonWriter(buffer);
        writer.WriteStartObject();
        writer.WriteStartArray("models");
        foreach (var model in result.Models)
        {
            writer.WriteStartObject();
            writer.WriteNumber("elementId", model.ElementId);
            writer.WriteString("modelName", model.ModelName);
            writer.WriteStartArray("transform");
            WriteMatrix(writer, model.Transform);
            writer.WriteEndArray();
            if (model.MaterialGroup is null)
                writer.WriteNull("materialGroup");
            else
                writer.WriteString("materialGroup", model.MaterialGroup);
            if (model.TintColor is { } tint)
            {
                writer.WriteStartArray("tintColor");
                writer.WriteNumberValue(tint.X);
                writer.WriteNumberValue(tint.Y);
                writer.WriteNumberValue(tint.Z);
                writer.WriteNumberValue(tint.W);
                writer.WriteEndArray();
            }
            else
            {
                writer.WriteNull("tintColor");
            }
            writer.WriteEndObject();
        }
        writer.WriteEndArray();
        writer.WriteStartArray("diagnostics");
        foreach (var diagnostic in result.Diagnostics)
        {
            writer.WriteStartObject();
            writer.WriteString("severity", diagnostic.Severity.ToString());
            writer.WriteString("code", diagnostic.Code);
            writer.WriteString("message", diagnostic.Message);
            writer.WriteEndObject();
        }
        writer.WriteEndArray();
        writer.WriteEndObject();
        writer.Flush();
        return buffer.WrittenSpan.ToArray();
    }

    private static void WriteMatrix(Utf8JsonWriter writer, System.Numerics.Matrix4x4 matrix)
    {
        writer.WriteNumberValue(matrix.M11);
        writer.WriteNumberValue(matrix.M12);
        writer.WriteNumberValue(matrix.M13);
        writer.WriteNumberValue(matrix.M14);
        writer.WriteNumberValue(matrix.M21);
        writer.WriteNumberValue(matrix.M22);
        writer.WriteNumberValue(matrix.M23);
        writer.WriteNumberValue(matrix.M24);
        writer.WriteNumberValue(matrix.M31);
        writer.WriteNumberValue(matrix.M32);
        writer.WriteNumberValue(matrix.M33);
        writer.WriteNumberValue(matrix.M34);
        writer.WriteNumberValue(matrix.M41);
        writer.WriteNumberValue(matrix.M42);
        writer.WriteNumberValue(matrix.M43);
        writer.WriteNumberValue(matrix.M44);
    }

    private static byte[] WriteNativeError(string message)
    {
        var buffer = new ArrayBufferWriter<byte>();
        using var writer = new Utf8JsonWriter(buffer);
        writer.WriteStartObject();
        writer.WriteString("error", message);
        writer.WriteEndObject();
        writer.Flush();
        return buffer.WrittenSpan.ToArray();
    }

    private static CancellationToken GetCancellationToken(long cancellationId)
    {
        if (cancellationId == 0)
            return default;
        if (!Cancellations.TryGetValue(cancellationId, out var cancellation))
            throw new ArgumentException("The cancellation handle is invalid.");
        return cancellation.Token;
    }

    private static Dictionary<string, float> ReadVariables(JsonElement root, string propertyName)
    {
        var values = new Dictionary<string, float>(StringComparer.OrdinalIgnoreCase);
        if (!root.TryGetProperty(propertyName, out var property) || property.ValueKind != JsonValueKind.Object)
            return values;

        foreach (var item in property.EnumerateObject())
            values[item.Name] = item.Value.GetSingle();
        return values;
    }

    private static Dictionary<string, System.Numerics.Vector4> ReadVectors(JsonElement root, string propertyName)
    {
        var values = new Dictionary<string, System.Numerics.Vector4>(StringComparer.OrdinalIgnoreCase);
        if (!root.TryGetProperty(propertyName, out var property) || property.ValueKind != JsonValueKind.Object)
            return values;

        foreach (var item in property.EnumerateObject())
        {
            var components = item.Value.EnumerateArray().Select(value => value.GetSingle()).Take(4).ToArray();
            values[item.Name] = new(
                components.ElementAtOrDefault(0),
                components.ElementAtOrDefault(1),
                components.ElementAtOrDefault(2),
                components.ElementAtOrDefault(3));
        }
        return values;
    }

    private static int GetInt32(JsonElement root, string propertyName, int defaultValue)
        => root.TryGetProperty(propertyName, out var property) ? property.GetInt32() : defaultValue;

    private static float GetSingle(JsonElement root, string propertyName, float defaultValue)
        => root.TryGetProperty(propertyName, out var property) ? property.GetSingle() : defaultValue;
}
