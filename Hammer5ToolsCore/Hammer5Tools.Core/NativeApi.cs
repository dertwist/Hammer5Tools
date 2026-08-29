using System.Buffers;
using System.Globalization;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;

using Hammer5Tools.Core.Format.SmartProps;

namespace Hammer5Tools.Core;

internal static unsafe class NativeApi
{
    private const int AbiVersion = 2;

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

    private static int Invoke(byte** output, int* outputLength, Func<byte[]> operation) =>
        NativeInterop.Invoke(output, outputLength, operation);

    private static string ReadUtf8(byte* input, int length) => NativeInterop.ReadUtf8(input, length);

    private static void WriteOutput(byte[] bytes, byte** output, int* outputLength) =>
        NativeInterop.WriteOutput(bytes, output, outputLength);

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
            writer.WriteStartArray("materialTints");
            foreach (var materialTint in model.MaterialTints ?? [])
            {
                writer.WriteStartObject();
                writer.WriteString("material", materialTint.Material);
                writer.WriteStartArray("color");
                writer.WriteNumberValue(materialTint.Color.X);
                writer.WriteNumberValue(materialTint.Color.Y);
                writer.WriteNumberValue(materialTint.Color.Z);
                writer.WriteNumberValue(materialTint.Color.W);
                writer.WriteEndArray();
                writer.WriteEndObject();
            }
            writer.WriteEndArray();
            writer.WriteStartArray("materialOverrides");
            foreach (var replacement in model.MaterialOverrides ?? [])
            {
                writer.WriteStartObject();
                writer.WriteString("originalMaterial", replacement.OriginalMaterial);
                writer.WriteString("replacementMaterial", replacement.ReplacementMaterial);
                writer.WriteEndObject();
            }
            writer.WriteEndArray();
            if (model.Deformer is { } deformer)
            {
                writer.WriteStartObject("deformer");
                WriteVector(writer, "size", deformer.Size);
                writer.WriteStartArray("controlPoints");
                foreach (var point in deformer.ControlPoints)
                    WriteVectorValue(writer, point);
                writer.WriteEndArray();
                writer.WriteStartArray("midpoints");
                foreach (var point in deformer.Midpoints)
                    WriteVectorValue(writer, point);
                writer.WriteEndArray();
                writer.WriteStartArray("deformerFrame");
                WriteMatrix(writer, deformer.DeformerFrame);
                writer.WriteEndArray();
                writer.WriteStartArray("volumeFrame");
                WriteMatrix(writer, deformer.VolumeFrame);
                writer.WriteEndArray();
                writer.WriteEndObject();
            }
            else
            {
                writer.WriteNull("deformer");
            }
            writer.WriteEndObject();
        }
        writer.WriteEndArray();
        writer.WriteStartArray("widgets");
        foreach (var widget in result.Widgets)
        {
            writer.WriteStartObject();
            writer.WriteString("type", widget.Type);
            writer.WriteNumber("elementId", widget.ElementId);
            writer.WriteStartArray("transform");
            WriteMatrix(writer, widget.Transform);
            writer.WriteEndArray();
            WriteVector(writer, "offset", widget.Offset);
            WriteVector(writer, "minimumBounds", widget.MinimumBounds);
            WriteVector(writer, "maximumBounds", widget.MaximumBounds);
            WriteVector(writer, "axis", widget.Axis);
            WriteVector(writer, "color", widget.Color);
            WriteBooleanArray(writer, "handles", widget.Handles);
            WriteBooleanArray(writer, "activeAxes", widget.ActiveAxes);
            writer.WriteNumber("scale", widget.Scale);
            writer.WriteNumber("radius", widget.Radius);
            writer.WriteNumber("angle", widget.Angle);
            writer.WriteNumber("size", widget.Size);
            writer.WriteString("shape", widget.Shape);
            writer.WriteString("name", widget.Name);
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

    private static void WriteVector(Utf8JsonWriter writer, string name, System.Numerics.Vector3 vector)
    {
        writer.WriteStartArray(name);
        writer.WriteNumberValue(vector.X);
        writer.WriteNumberValue(vector.Y);
        writer.WriteNumberValue(vector.Z);
        writer.WriteEndArray();
    }

    /// <summary>Writes a bare <c>[x, y, z]</c> array, for a vector nested inside an array-of-vectors.</summary>
    private static void WriteVectorValue(Utf8JsonWriter writer, System.Numerics.Vector3 vector)
    {
        writer.WriteStartArray();
        writer.WriteNumberValue(vector.X);
        writer.WriteNumberValue(vector.Y);
        writer.WriteNumberValue(vector.Z);
        writer.WriteEndArray();
    }

    private static void WriteBooleanArray(Utf8JsonWriter writer, string name, IReadOnlyList<bool> values)
    {
        writer.WriteStartArray(name);
        foreach (var value in values)
            writer.WriteBooleanValue(value);
        writer.WriteEndArray();
    }

    private static CancellationToken GetCancellationToken(long cancellationId) =>
        NativeInterop.GetCancellationToken(cancellationId);

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
