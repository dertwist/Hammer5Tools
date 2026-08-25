using System.Buffers;
using System.Diagnostics.CodeAnalysis;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text.Json;

using Hammer5Tools.Core.Format.Vmap;

namespace Hammer5Tools.Core;

/// <summary>NativeAOT ABI for the VMAP read/rewrite/write contract.</summary>
internal static unsafe class VmapApi
{
    // Datamodel.Datamodel's static constructor registers its built-in codecs via
    // Activator.CreateInstance(Type), and Binary.Decode looks up the KeyValues2 source
    // generator's per-project ElementFactory the same way — both via a reflection scan
    // that NativeAOT trims away unless something declares them reachable. ElementFactory
    // is generated into this project's own global namespace by the KeyValues2 package's
    // analyzer; it exists even though nothing there subclasses Datamodel.Element.
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    /// <summary>Reads an uncompiled VMAP into the shared read-only projection.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_read_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int ReadValveMapJson(byte* path, int pathLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var document = new ValveMapReader().Read(NativeInterop.ReadUtf8(path, pathLength));
            var buffer = new ArrayBufferWriter<byte>();
            using var writer = new Utf8JsonWriter(buffer);
            WriteValveMapDocument(writer, document);
            writer.Flush();
            return buffer.WrittenSpan.ToArray();
        });

    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    /// <summary>Request: {path, renames: {old: new, ...}}.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_rewrite_references_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int RewriteVmapReferencesJson(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var root = JsonDocument.Parse(NativeInterop.ReadUtf8(request, requestLength)).RootElement;
            var renames = new Dictionary<string, string>();
            foreach (var property in root.GetProperty("renames").EnumerateObject())
                renames[property.Name] = property.Value.GetString() ?? "";
            var result = VmapReferenceRewriter.Rewrite(root.GetProperty("path").GetString()!, renames);

            var buffer = new ArrayBufferWriter<byte>();
            using var writer = new Utf8JsonWriter(buffer);
            writer.WriteStartObject();
            if (result.IsSuccess)
                writer.WriteBoolean("value", result.Value);
            else
                writer.WriteNull("value");
            WriteDiagnostics(writer, result.Diagnostics);
            writer.WriteEndObject();
            writer.Flush();
            return buffer.WrittenSpan.ToArray();
        });

    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    /// <summary>Writes typed Unreal placements to a VMAP. <paramref name="request"/> is the raw
    /// UnrealMapWriteRequest JSON (unchanged from the caller); <paramref name="outputPath"/> is separate.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_write_unreal_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int WriteUnrealMapJson(
        byte* request, int requestLength, byte* outputPath, int outputPathLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var result = UnrealMapWriter.WriteJson(
                NativeInterop.ReadUtf8(request, requestLength),
                NativeInterop.ReadUtf8(outputPath, outputPathLength));

            var buffer = new ArrayBufferWriter<byte>();
            using var writer = new Utf8JsonWriter(buffer);
            writer.WriteStartObject();
            if (result.IsSuccess && result.Value is { } value)
            {
                writer.WriteStartObject("value");
                writer.WriteNumber("placementCount", value.PlacementCount);
                writer.WriteString("encoding", value.Encoding);
                writer.WriteNumber("encodingVersion", value.EncodingVersion);
                writer.WriteEndObject();
            }
            else
            {
                writer.WriteNull("value");
            }
            WriteDiagnostics(writer, result.Diagnostics);
            writer.WriteEndObject();
            writer.Flush();
            return buffer.WrittenSpan.ToArray();
        });

    private static void WriteValveMapDocument(Utf8JsonWriter writer, ValveMapDocument document)
    {
        writer.WriteStartObject();
        writer.WriteString("path", document.Path);
        writer.WritePropertyName("world");
        WriteValveMapNode(writer, document.World);
        writer.WriteStartArray("nodes");
        foreach (var node in document.Nodes)
            WriteValveMapNode(writer, node);
        writer.WriteEndArray();
        writer.WriteStartArray("entities");
        foreach (var entity in document.Entities)
            WriteValveMapEntity(writer, entity);
        writer.WriteEndArray();
        writer.WriteStartArray("assetReferences");
        foreach (var reference in document.AssetReferences)
            writer.WriteStringValue(reference);
        writer.WriteEndArray();
        if (document.Thumbnail is { } thumbnail)
            writer.WriteBase64String("thumbnail", [.. thumbnail]);
        else
            writer.WriteNull("thumbnail");
        if (document.ThumbnailFormat is { } format)
            writer.WriteString("thumbnailFormat", format);
        else
            writer.WriteNull("thumbnailFormat");
        writer.WriteEndObject();
    }

    private static void WriteValveMapNode(Utf8JsonWriter writer, ValveMapNode node)
    {
        writer.WriteStartObject();
        writer.WriteString("name", node.Name);
        writer.WriteString("className", node.ClassName);
        WriteProperties(writer, node.Properties);
        writer.WriteStartArray("children");
        foreach (var child in node.Children)
            WriteValveMapNode(writer, child);
        writer.WriteEndArray();
        writer.WriteEndObject();
    }

    private static void WriteValveMapEntity(Utf8JsonWriter writer, ValveMapEntity entity)
    {
        writer.WriteStartObject();
        writer.WriteString("className", entity.ClassName);
        if (entity.Origin is { } origin)
            writer.WriteString("origin", origin);
        else
            writer.WriteNull("origin");
        if (entity.Angles is { } angles)
            writer.WriteString("angles", angles);
        else
            writer.WriteNull("angles");
        WriteProperties(writer, entity.Properties);
        writer.WriteEndObject();
    }

    private static void WriteProperties(Utf8JsonWriter writer, IReadOnlyDictionary<string, string> properties)
    {
        writer.WriteStartObject("properties");
        foreach (var (key, value) in properties)
            writer.WriteString(key, value);
        writer.WriteEndObject();
    }

    private static void WriteDiagnostics(Utf8JsonWriter writer, IReadOnlyList<Hammer5Tools.Core.CoreDiagnostic> diagnostics)
    {
        writer.WriteStartArray("diagnostics");
        foreach (var diagnostic in diagnostics)
        {
            writer.WriteStartObject();
            writer.WriteString("severity", diagnostic.Severity.ToString());
            writer.WriteString("code", diagnostic.Code);
            writer.WriteString("message", diagnostic.Message);
            writer.WriteEndObject();
        }
        writer.WriteEndArray();
    }
}
