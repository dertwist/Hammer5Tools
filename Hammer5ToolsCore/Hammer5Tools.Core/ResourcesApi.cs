using System.Buffers;
using System.Collections.Concurrent;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text.Json;
using Hammer5Tools.Core.Format.Resources;
using Hammer5Tools.Core.IO.CompiledResource;
using Hammer5Tools.Core.IO.Vpk;

namespace Hammer5Tools.Core;

/// <summary>NativeAOT ABI for VPK indexing and compiled-resource reading.</summary>
internal static unsafe class ResourcesApi
{
    private static readonly ConcurrentDictionary<long, VpkIndex> VpkHandles = new();
    // One lazy reader belongs to the active addon so its material and texture caches are
    // shared by every caller. The reader leases a loader per read, so concurrent reads run
    // in parallel; this lock only guards swapping the reader when the addon changes.
    private static readonly Lock ModelReaderLock = new();
    private static ModelReaderKey? currentModelReaderKey;
    private static CompiledModelReader? currentModelReader;
    private static long NextVpkHandle;

    [UnmanagedCallersOnly(EntryPoint = "h5t_vpk_open", CallConvs = [typeof(CallConvCdecl)])]
    public static long VpkOpen()
    {
        var handle = Interlocked.Increment(ref NextVpkHandle);
        VpkHandles[handle] = new VpkIndex();
        return handle;
    }

    [UnmanagedCallersOnly(EntryPoint = "h5t_vpk_close", CallConvs = [typeof(CallConvCdecl)])]
    public static void VpkClose(long handle)
    {
        if (VpkHandles.TryRemove(handle, out var index))
            index.Dispose();
    }

    [UnmanagedCallersOnly(EntryPoint = "h5t_vpk_mount", CallConvs = [typeof(CallConvCdecl)])]
    public static int VpkMount(long handle, byte* path, int pathLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            GetVpk(handle).MountVpk(NativeInterop.ReadUtf8(path, pathLength));
            return [];
        });

    [UnmanagedCallersOnly(EntryPoint = "h5t_vpk_add_loose_root", CallConvs = [typeof(CallConvCdecl)])]
    public static int VpkAddLooseRoot(long handle, byte* directory, int directoryLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            GetVpk(handle).AddLooseRoot(NativeInterop.ReadUtf8(directory, directoryLength));
            return [];
        });

    /// <summary>Returns 1/0 for exists/not, or -1 when <paramref name="handle"/> is invalid.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vpk_exists", CallConvs = [typeof(CallConvCdecl)])]
    public static int VpkExists(long handle, byte* path, int pathLength)
    {
        try
        {
            return GetVpk(handle).Exists(NativeInterop.ReadUtf8(path, pathLength)) ? 1 : 0;
        }
        catch
        {
            return -1;
        }
    }

    /// <summary>Returns the mounted package count, or -1 when <paramref name="handle"/> is invalid.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vpk_package_count", CallConvs = [typeof(CallConvCdecl)])]
    public static int VpkPackageCount(long handle) =>
        VpkHandles.TryGetValue(handle, out var index) ? index.PackageCount : -1;

    /// <summary>Writes the raw file bytes to <paramref name="output"/>. Returns 0 = found, 1 = not found, &lt;0 = error (JSON in <paramref name="output"/>).</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vpk_read_bytes", CallConvs = [typeof(CallConvCdecl)])]
    public static int VpkReadBytes(long handle, byte* path, int pathLength, byte** output, int* outputLength)
    {
        if (output is null || outputLength is null)
            return -1;

        *output = null;
        *outputLength = 0;
        try
        {
            var data = GetVpk(handle).TryReadBytes(NativeInterop.ReadUtf8(path, pathLength));
            if (data is null)
                return 1;
            NativeInterop.WriteOutput(data, output, outputLength);
            return 0;
        }
        catch (Exception exception)
        {
            NativeInterop.WriteOutput(NativeInterop.WriteNativeError(exception.Message), output, outputLength);
            return -2;
        }
    }

    /// <summary>Writes a JSON array of <c>[path, size]</c> pairs for entries matching one of the JSON-array suffixes.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vpk_entries_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int VpkEntriesJson(long handle, byte* suffixesJson, int suffixesJsonLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var suffixes = suffixesJsonLength > 0
                ? JsonDocument.Parse(NativeInterop.ReadUtf8(suffixesJson, suffixesJsonLength)).RootElement
                    .EnumerateArray().Select(element => element.GetString() ?? "").ToArray()
                : [];
            var entries = GetVpk(handle).EnumerateEntries(suffixes);

            var buffer = new ArrayBufferWriter<byte>();
            using var writer = new Utf8JsonWriter(buffer);
            writer.WriteStartArray();
            foreach (var entry in entries)
            {
                writer.WriteStartArray();
                writer.WriteStringValue(entry.Path);
                writer.WriteNumberValue(entry.Size);
                writer.WriteEndArray();
            }
            writer.WriteEndArray();
            writer.Flush();
            return buffer.WrittenSpan.ToArray();
        });

    /// <summary>Request: {gameDirectory, activeAddon, resourcePath, contextAddon?, maximumTextureDimension?, baseColorOnly?, skin?}.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_compiled_model_read_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int CompiledModelReadJson(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var root = JsonDocument.Parse(NativeInterop.ReadUtf8(request, requestLength)).RootElement;
            CompiledModelReader reader;
            lock (ModelReaderLock)
            {
                reader = GetModelReader(root);
            }
            var result = reader.Read(
                root.GetProperty("resourcePath").GetString()!,
                GetOptionalString(root, "contextAddon"),
                GetInt32(root, "maximumTextureDimension", 1024),
                GetBoolean(root, "baseColorOnly", false),
                GetInt32(root, "skin", 0));
            return WriteCompiledModelResult(result);
        });

    /// <summary>Request: {gameDirectory, activeAddon, resourcePath, contextAddon?}.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_compiled_model_material_groups_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int CompiledModelMaterialGroupsJson(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var root = JsonDocument.Parse(NativeInterop.ReadUtf8(request, requestLength)).RootElement;
            CompiledModelReader reader;
            lock (ModelReaderLock)
            {
                reader = GetModelReader(root);
            }
            var result = reader.ReadMaterialGroups(
                root.GetProperty("resourcePath").GetString()!,
                GetOptionalString(root, "contextAddon"));

            var buffer = new ArrayBufferWriter<byte>();
            using var writer = new Utf8JsonWriter(buffer);
            writer.WriteStartArray();
            if (result.IsSuccess)
                foreach (var group in result.Value!)
                    writer.WriteStringValue(group);
            writer.WriteEndArray();
            writer.Flush();
            return buffer.WrittenSpan.ToArray();
        });

    /// <summary>Request: {vpkPath, resourcePath, soundEvents?}. Mounts a scratch VpkIndex for one read.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_compiled_resource_read_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int CompiledResourceReadJson(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var root = JsonDocument.Parse(NativeInterop.ReadUtf8(request, requestLength)).RootElement;
            var resourcePath = root.GetProperty("resourcePath").GetString()!;
            var soundEvents = GetBoolean(root, "soundEvents", false);

            using var index = new VpkIndex();
            index.MountVpk(root.GetProperty("vpkPath").GetString()!);
            var reader = new CompiledResourceReader(index);
            var result = soundEvents ? reader.ReadSoundEvents(resourcePath) : reader.ReadSound(resourcePath);

            var buffer = new ArrayBufferWriter<byte>();
            using var writer = new Utf8JsonWriter(buffer);
            writer.WriteStartObject();
            if (result.IsSuccess && result.Value is { } content)
            {
                writer.WriteStartObject("value");
                writer.WriteBase64String("data", content.Data.AsSpan());
                writer.WriteString("format", content.Format);
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

    private static VpkIndex GetVpk(long handle) =>
        VpkHandles.TryGetValue(handle, out var index)
            ? index
            : throw new ArgumentException($"Invalid VPK handle {handle}.");

    private static CompiledModelReader GetModelReader(JsonElement root)
    {
        var gameDirectory = Path.TrimEndingDirectorySeparator(
            Path.GetFullPath(root.GetProperty("gameDirectory").GetString()!));
        var activeAddon = root.GetProperty("activeAddon").GetString()!;
        var key = new ModelReaderKey(gameDirectory.ToUpperInvariant(), activeAddon.ToUpperInvariant());
        if (currentModelReaderKey == key)
            return currentModelReader!;

        var replacement = new CompiledModelReader(gameDirectory, activeAddon);
        currentModelReader?.Dispose();
        currentModelReaderKey = key;
        currentModelReader = replacement;
        return currentModelReader;
    }

    private static byte[] WriteCompiledModelResult(Hammer5Tools.Core.CoreResult<CompiledModel> result)
    {
        var buffer = new ArrayBufferWriter<byte>();
        using var writer = new Utf8JsonWriter(buffer);
        writer.WriteStartObject();
        if (result.IsSuccess && result.Value is { } model)
        {
            writer.WritePropertyName("value");
            WriteCompiledModel(writer, model);
        }
        else
        {
            writer.WriteNull("value");
        }
        WriteDiagnostics(writer, result.Diagnostics);
        writer.WriteEndObject();
        writer.Flush();
        return buffer.WrittenSpan.ToArray();
    }

    private static void WriteCompiledModel(Utf8JsonWriter writer, CompiledModel model)
    {
        writer.WriteStartObject();
        writer.WriteBase64String("verticesBytes", MemoryMarshal.AsBytes(model.Vertices.AsSpan()));
        writer.WriteBase64String("normalsBytes", MemoryMarshal.AsBytes(model.Normals.AsSpan()));
        writer.WriteBase64String("uvsBytes", MemoryMarshal.AsBytes(model.Uvs.AsSpan()));
        writer.WriteBase64String("indicesBytes", MemoryMarshal.AsBytes(model.Indices.AsSpan()));
        writer.WritePropertyName("boundsMinimum");
        WriteVector3(writer, model.BoundsMinimum);
        writer.WritePropertyName("boundsMaximum");
        WriteVector3(writer, model.BoundsMaximum);
        // Submeshes sharing a material share the CompiledMaterial instance (the reader's
        // per-read materialCache), so the texture payload is written once into "materials"
        // and referenced by index. Inlining it per submesh multiplied a 5-map 1024px
        // material by the submesh count on every read.
        var materialIndices = new Dictionary<CompiledMaterial, int>(ReferenceEqualityComparer.Instance);
        var orderedMaterials = new List<CompiledMaterial>();
        foreach (var subMesh in model.SubMeshes)
        {
            if (materialIndices.ContainsKey(subMesh.Material))
                continue;
            materialIndices[subMesh.Material] = orderedMaterials.Count;
            orderedMaterials.Add(subMesh.Material);
        }

        writer.WriteStartArray("materials");
        foreach (var material in orderedMaterials)
            WriteCompiledMaterial(writer, material);
        writer.WriteEndArray();

        writer.WriteStartArray("submeshes");
        foreach (var subMesh in model.SubMeshes)
        {
            writer.WriteStartObject();
            writer.WriteNumber("indexOffset", subMesh.IndexOffset);
            writer.WriteNumber("indexCount", subMesh.IndexCount);
            writer.WriteNumber("materialIndex", materialIndices[subMesh.Material]);
            writer.WriteEndObject();
        }
        writer.WriteEndArray();
        writer.WriteEndObject();
    }

    private static void WriteCompiledMaterial(Utf8JsonWriter writer, CompiledMaterial material)
    {
        writer.WriteStartObject();
        writer.WriteString("name", material.Name);
        WriteOptionalTexture(writer, "baseColor", material.BaseColor);
        WriteOptionalTexture(writer, "normal", material.Normal);
        WriteOptionalTexture(writer, "metallicRoughness", material.MetallicRoughness);
        WriteOptionalTexture(writer, "ambientOcclusion", material.AmbientOcclusion);
        WriteOptionalTexture(writer, "emissive", material.Emissive);
        writer.WritePropertyName("baseColorFactor");
        WriteVector4(writer, material.BaseColorFactor);
        writer.WriteNumber("metallicFactor", material.MetallicFactor);
        writer.WriteNumber("roughnessFactor", material.RoughnessFactor);
        writer.WritePropertyName("emissiveFactor");
        WriteVector3(writer, material.EmissiveFactor);
        writer.WriteString("alphaMode", material.AlphaMode);
        writer.WriteNumber("alphaCutoff", material.AlphaCutoff);
        writer.WriteBoolean("doubleSided", material.DoubleSided);
        writer.WriteNumber("wrapU", material.WrapU);
        writer.WriteNumber("wrapV", material.WrapV);
        writer.WriteNumber("uvSet", material.UvSet);
        writer.WritePropertyName("uvScale");
        WriteVector2(writer, material.UvScale);
        writer.WritePropertyName("uvOffset");
        WriteVector2(writer, material.UvOffset);
        writer.WritePropertyName("uvCenter");
        WriteVector2(writer, material.UvCenter);
        writer.WriteNumber("uvRotation", material.UvRotation);
        writer.WriteEndObject();
    }

    private static void WriteOptionalTexture(Utf8JsonWriter writer, string name, CompiledTexture? texture)
    {
        if (texture is null)
        {
            writer.WriteNull(name);
            return;
        }
        writer.WriteStartObject(name);
        writer.WriteNumber("width", texture.Width);
        writer.WriteNumber("height", texture.Height);
        writer.WriteBase64String("rgba", texture.Rgba.AsSpan());
        writer.WriteEndObject();
    }

    private static void WriteVector2(Utf8JsonWriter writer, System.Numerics.Vector2 vector)
    {
        writer.WriteStartArray();
        writer.WriteNumberValue(vector.X);
        writer.WriteNumberValue(vector.Y);
        writer.WriteEndArray();
    }

    private static void WriteVector3(Utf8JsonWriter writer, System.Numerics.Vector3 vector)
    {
        writer.WriteStartArray();
        writer.WriteNumberValue(vector.X);
        writer.WriteNumberValue(vector.Y);
        writer.WriteNumberValue(vector.Z);
        writer.WriteEndArray();
    }

    private static void WriteVector4(Utf8JsonWriter writer, System.Numerics.Vector4 vector)
    {
        writer.WriteStartArray();
        writer.WriteNumberValue(vector.X);
        writer.WriteNumberValue(vector.Y);
        writer.WriteNumberValue(vector.Z);
        writer.WriteNumberValue(vector.W);
        writer.WriteEndArray();
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

    private static string? GetOptionalString(JsonElement root, string propertyName) =>
        root.TryGetProperty(propertyName, out var property) && property.ValueKind != JsonValueKind.Null
            ? property.GetString()
            : null;

    private static int GetInt32(JsonElement root, string propertyName, int defaultValue) =>
        root.TryGetProperty(propertyName, out var property) ? property.GetInt32() : defaultValue;

    private static bool GetBoolean(JsonElement root, string propertyName, bool defaultValue) =>
        root.TryGetProperty(propertyName, out var property) ? property.GetBoolean() : defaultValue;

    private readonly record struct ModelReaderKey(string GameDirectory, string ActiveAddon);
}
