using System.Buffers;
using System.Collections.Immutable;
using System.Diagnostics.CodeAnalysis;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text.Json;

using Hammer5Tools.Core.Format.Vmap;

namespace Hammer5Tools.Core;

/// <summary>NativeAOT ABI for the VMAP read/rewrite/write contract.</summary>
internal static unsafe class VmapApi
{
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    /// <summary>Reads an uncompiled VMAP into a compact binary scene projection.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_read_scene_binary", CallConvs = [typeof(CallConvCdecl)])]
    public static int ReadValveMapSceneBinary(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.InvokeBinary(output, outputLength, () => ReadValveMapSceneBinaryPayload(request, requestLength));

    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    /// <summary>Rewrites VMAP asset references from a compact binary request.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_rewrite_references_binary", CallConvs = [typeof(CallConvCdecl)])]
    public static int RewriteVmapReferencesBinary(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.InvokeBinary(output, outputLength, () => RewriteVmapReferencesBinaryPayload(request, requestLength));

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
    /// <summary>Reads only the asset-reference list from an uncompiled VMAP, skipping the node/entity
    /// projection and thumbnail decoding that <see cref="ReadValveMapJson"/> does.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_read_asset_references_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int ReadValveMapAssetReferencesJson(byte* path, int pathLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var document = VmapDocument.LoadInMemory(NativeInterop.ReadUtf8(path, pathLength));
            var buffer = new ArrayBufferWriter<byte>();
            using var writer = new Utf8JsonWriter(buffer);
            writer.WriteStartArray();
            if (document.Model.PrefixAttributes.TryGetValue("map_asset_references", out var value)
                && value is not string
                && value is System.Collections.IEnumerable references)
            {
                foreach (var reference in references)
                {
                    if (reference is not null)
                        writer.WriteStringValue(reference.ToString());
                }
            }
            writer.WriteEndArray();
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

    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    /// <summary>Reads an uncompiled VMAP into flattened, drawable scene geometry.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_read_scene_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int ReadValveMapSceneJson(byte* path, int pathLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var scene = new ValveMapSceneReader().Read(NativeInterop.ReadUtf8(path, pathLength));
            var buffer = new ArrayBufferWriter<byte>();
            using var writer = new Utf8JsonWriter(buffer);
            WriteValveMapScene(writer, scene);
            writer.Flush();
            return buffer.WrittenSpan.ToArray();
        });

    private static void WriteValveMapScene(Utf8JsonWriter writer, ValveMapScene scene)
    {
        writer.WriteStartObject();
        writer.WriteString("path", scene.Path);

        writer.WriteStartArray("meshes");
        foreach (var mesh in scene.Meshes)
        {
            writer.WriteStartObject();
            writer.WriteString("name", mesh.Name);
            WriteFloatsBase64(writer, "positionsBytes", mesh.Positions);
            WriteFloatsBase64(writer, "normalsBytes", mesh.Normals);
            WriteFloatsBase64(writer, "uvsBytes", mesh.TextureCoordinates);
            writer.WriteBase64String("indicesBytes", MemoryMarshal.AsBytes(mesh.Indices.AsSpan()));
            writer.WriteStartArray("submeshes");
            foreach (var submesh in mesh.SubMeshes)
            {
                writer.WriteStartObject();
                writer.WriteNumber("indexOffset", submesh.IndexOffset);
                writer.WriteNumber("indexCount", submesh.IndexCount);
                writer.WriteString("material", submesh.Material);
                writer.WriteEndObject();
            }
            writer.WriteEndArray();
            writer.WriteEndObject();
        }
        writer.WriteEndArray();

        writer.WriteStartArray("props");
        foreach (var prop in scene.Props)
        {
            writer.WriteStartObject();
            writer.WriteString("name", prop.Name);
            writer.WriteString("className", prop.ClassName);
            writer.WriteString("model", prop.Model);
            WriteTransform(writer, prop.Transform);
            writer.WriteEndObject();
        }
        writer.WriteEndArray();

        writer.WriteStartArray("smartProps");
        foreach (var smartProp in scene.SmartProps)
        {
            writer.WriteStartObject();
            writer.WriteString("name", smartProp.Name);
            writer.WriteString("file", smartProp.File);
            WriteTransform(writer, smartProp.Transform);
            writer.WriteStartObject("variables");
            foreach (var (name, value) in smartProp.Variables)
            {
                writer.WritePropertyName(name);
                WriteScalar(writer, value);
            }
            writer.WriteEndObject();
            writer.WriteEndObject();
        }
        writer.WriteEndArray();

        writer.WriteStartArray("diagnostics");
        foreach (var diagnostic in scene.Diagnostics)
            writer.WriteStringValue(diagnostic);
        writer.WriteEndArray();

        writer.WriteEndObject();
    }

    private static void WriteFloatsBase64(Utf8JsonWriter writer, string name, ImmutableArray<float> values) =>
        writer.WriteBase64String(name, MemoryMarshal.AsBytes(values.AsSpan()));

    private static void WriteTransform(Utf8JsonWriter writer, ImmutableArray<float> transform)
    {
        writer.WriteStartArray("transform");
        foreach (var component in transform)
            writer.WriteNumberValue(component);
        writer.WriteEndArray();
    }

    /// <summary>Writes a SmartProp parameter override as its closest JSON form.</summary>
    private static void WriteScalar(Utf8JsonWriter writer, object? value)
    {
        switch (value)
        {
            case null:
                writer.WriteNullValue();
                break;
            case bool boolean:
                writer.WriteBooleanValue(boolean);
                break;
            case string text:
                writer.WriteStringValue(text);
                break;
            case float number:
                writer.WriteNumberValue(number);
                break;
            case int number:
                writer.WriteNumberValue(number);
                break;
            case System.Numerics.Vector2 vector:
                writer.WriteStartArray();
                writer.WriteNumberValue(vector.X);
                writer.WriteNumberValue(vector.Y);
                writer.WriteEndArray();
                break;
            case System.Numerics.Vector3 vector:
                writer.WriteStartArray();
                writer.WriteNumberValue(vector.X);
                writer.WriteNumberValue(vector.Y);
                writer.WriteNumberValue(vector.Z);
                writer.WriteEndArray();
                break;
            case Datamodel.Color color:
                writer.WriteStartArray();
                writer.WriteNumberValue(color.R);
                writer.WriteNumberValue(color.G);
                writer.WriteNumberValue(color.B);
                writer.WriteEndArray();
                break;
            default:
                writer.WriteStringValue(value.ToString());
                break;
        }
    }

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

    private static byte[] ReadValveMapSceneBinaryPayload(byte* request, int requestLength)
    {
        var reader = NativeBinary.Read(request, requestLength, NativeBinaryMessage.VmapSceneRequest);
        var path = reader.ReadString();
        reader.EnsureFinished();
        var scene = new ValveMapSceneReader().Read(path);
        return NativeBinary.Create(NativeBinaryMessage.VmapSceneResult,
            writer => ValveMapSceneBinarySerializer.Write(writer, scene));
    }

    private static byte[] RewriteVmapReferencesBinaryPayload(byte* request, int requestLength)
    {
        var reader = NativeBinary.Read(request, requestLength, NativeBinaryMessage.VmapRewriteRequest);
        var path = reader.ReadString();
        var count = reader.ReadInt32();
        if (count is < 0 or > 1_000_000)
        {
            throw new InvalidDataException("The binary VMAP rename count is invalid.");
        }

        var renames = new Dictionary<string, string>(count, StringComparer.Ordinal);
        for (var index = 0; index < count; index++)
        {
            renames[reader.ReadString()] = reader.ReadString();
        }
        reader.EnsureFinished();

        var result = VmapReferenceRewriter.Rewrite(path, renames);
        return NativeBinary.Create(NativeBinaryMessage.VmapRewriteResult, writer =>
        {
            writer.WriteBoolean(result.IsSuccess);
            if (result.IsSuccess)
            {
                writer.WriteBoolean(result.Value);
            }
            WriteDiagnostics(writer, result.Diagnostics);
        });
    }

    private static void WriteDiagnostics(NativeBinaryWriter writer, IReadOnlyList<CoreDiagnostic> diagnostics)
    {
        writer.WriteInt32(diagnostics.Count);
        foreach (var diagnostic in diagnostics)
        {
            writer.WriteString(diagnostic.Severity.ToString());
            writer.WriteString(diagnostic.Code);
            writer.WriteString(diagnostic.Message);
        }
    }
}
