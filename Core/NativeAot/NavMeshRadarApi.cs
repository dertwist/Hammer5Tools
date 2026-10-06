using System.Buffers;
using System.Diagnostics.CodeAnalysis;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;

using Hammer5Tools.Core.Format.NavMesh;

namespace Hammer5Tools.Core;

/// <summary>NativeAOT ABI for NAV-based radar generation.</summary>
internal static unsafe class NavMeshRadarApi
{
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    /// <summary>
    /// Generates a radar sub-map from a compact binary request, streaming stage progress as
    /// <c>"{fraction}|{stage}"</c> lines through <paramref name="progressCallback"/> (may be null).
    /// </summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_navmesh_radar_generate_binary", CallConvs = [typeof(CallConvCdecl)])]
    public static int GenerateBinary(
        byte* request, int requestLength,
        delegate* unmanaged[Cdecl]<byte*, int, void> progressCallback,
        byte** output, int* outputLength) =>
        NativeInterop.InvokeBinary(output, outputLength, () =>
            GenerateBinaryPayload(request, requestLength, progressCallback));

    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    /// <summary>Reports the radar sub-map path and whether the main map already references it.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_navmesh_radar_status_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int StatusJson(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            using var document = JsonDocument.Parse(NativeInterop.ReadUtf8(request, requestLength));
            var result = NavMeshRadarGenerator.Inspect(
                document.RootElement.GetProperty("mainVmapPath").GetString() ?? "");

            var buffer = new ArrayBufferWriter<byte>();
            using var writer = new Utf8JsonWriter(buffer);
            writer.WriteStartObject();
            if (result.IsSuccess && result.Value is { } value)
            {
                writer.WriteStartObject("value");
                writer.WriteString("generatedVmapPath", value.GeneratedVmapPath);
                writer.WriteBoolean("prefabPresent", value.PrefabPresent);
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
    /// <summary>Generates a radar sub-map from a JSON request.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_navmesh_radar_generate_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int GenerateJson(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            using var document = JsonDocument.Parse(NativeInterop.ReadUtf8(request, requestLength));
            var root = document.RootElement;
            var modeName = root.GetProperty("mode").GetString();
            var mode = modeName switch
            {
                "baked_bomb_damage" => NavMeshRadarMode.BakedBombDamage,
                "navmesh_offset" => NavMeshRadarMode.NavMeshOffset,
                _ => throw new JsonException($"Unknown NavMesh Radar mode '{modeName}'."),
            };
            var addPrefabReference = true;
            if (root.TryGetProperty("addPrefabReference", out var addPrefabElement)
                && addPrefabElement.ValueKind is JsonValueKind.True or JsonValueKind.False)
            {
                addPrefabReference = addPrefabElement.GetBoolean();
            }
            else if (root.TryGetProperty("addPrefab", out var addPrefabAlt)
                && addPrefabAlt.ValueKind is JsonValueKind.True or JsonValueKind.False)
            {
                addPrefabReference = addPrefabAlt.GetBoolean();
            }

            var collapseFaces = true;
            if (root.TryGetProperty("collapseFaces", out var collapseElement)
                && collapseElement.ValueKind is JsonValueKind.True or JsonValueKind.False)
            {
                collapseFaces = collapseElement.GetBoolean();
            }

            var collapseFacesIntoNgons = false;
            if (root.TryGetProperty("collapseFacesIntoNgons", out var collapseNgonsElement)
                && collapseNgonsElement.ValueKind is JsonValueKind.True or JsonValueKind.False)
            {
                collapseFacesIntoNgons = collapseNgonsElement.GetBoolean();
            }

            var radarRequest = new NavMeshRadarRequest(
                root.GetProperty("vpkPath").GetString() ?? "",
                root.GetProperty("mainVmapPath").GetString() ?? "",
                mode,
                root.TryGetProperty("offset", out var offset) ? offset.GetSingle() : 16f,
                root.TryGetProperty("materialPath", out var material)
                    ? material.GetString() ?? ""
                    : "materials/radgen/radgen_path.vmat",
                addPrefabReference,
                collapseFaces,
                collapseFacesIntoNgons);
            var result = NavMeshRadarGenerator.Generate(radarRequest);

            var buffer = new ArrayBufferWriter<byte>();
            using var writer = new Utf8JsonWriter(buffer);
            writer.WriteStartObject();
            if (result.IsSuccess && result.Value is { } value)
            {
                writer.WriteStartObject("value");
                writer.WriteString("generatedVmapPath", value.GeneratedVmapPath);
                writer.WriteString("mode", value.Mode == NavMeshRadarMode.BakedBombDamage
                    ? "baked_bomb_damage"
                    : "navmesh_offset");
                writer.WriteNumber("sourceCount", value.SourceCount);
                writer.WriteNumber("faceCount", value.FaceCount);
                writer.WriteNumber("meshCount", value.MeshCount);
                writer.WriteNumber("offset", value.Offset);
                writer.WriteBoolean("referenceAdded", value.ReferenceAdded);
                if (value.BackupPath is { } backupPath)
                    writer.WriteString("backupPath", backupPath);
                else
                    writer.WriteNull("backupPath");
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

    /// <summary>Streams one <c>"{fraction}|{stage}"</c> progress line to the caller.</summary>
    private static void EmitProgress(
        delegate* unmanaged[Cdecl]<byte*, int, void> progressCallback, float fraction, string stage)
    {
        var bytes = Encoding.UTF8.GetBytes($"{fraction.ToString("0.####", System.Globalization.CultureInfo.InvariantCulture)}|{stage}");
        fixed (byte* pointer = bytes)
            progressCallback(pointer, bytes.Length);
    }

    private static void WriteDiagnostics(Utf8JsonWriter writer, IReadOnlyList<CoreDiagnostic> diagnostics)
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

    private static byte[] GenerateBinaryPayload(
        byte* request, int requestLength,
        delegate* unmanaged[Cdecl]<byte*, int, void> progressCallback)
    {
        var reader = NativeBinary.Read(request, requestLength, NativeBinaryMessage.NavMeshRadarRequest);
        var vpkPath = reader.ReadString();
        var mainVmapPath = reader.ReadString();
        var mode = reader.ReadByte() switch
        {
            0 => NavMeshRadarMode.BakedBombDamage,
            1 => NavMeshRadarMode.NavMeshOffset,
            var value => throw new InvalidDataException($"Unknown binary NavMesh Radar mode '{value}'."),
        };
        var offset = reader.ReadSingle();
        var materialPath = reader.ReadString();
        var addPrefabReference = reader.ReadBoolean();
        var collapseFaces = reader.ReadBoolean();
        var collapseFacesIntoNgons = reader.ReadBoolean();
        reader.EnsureFinished();

        var result = NavMeshRadarGenerator.Generate(
            new NavMeshRadarRequest(
                vpkPath,
                mainVmapPath,
                mode,
                offset,
                materialPath,
                addPrefabReference,
                collapseFaces,
                collapseFacesIntoNgons),
            progressCallback is null
                ? null
                : (fraction, stage) => EmitProgress(progressCallback, fraction, stage));
        return NativeBinary.Create(NativeBinaryMessage.NavMeshRadarResult, writer =>
        {
            writer.WriteBoolean(result.IsSuccess);
            if (result.IsSuccess && result.Value is { } value)
            {
                writer.WriteString(value.GeneratedVmapPath);
                writer.WriteByte(value.Mode == NavMeshRadarMode.BakedBombDamage ? (byte)0 : (byte)1);
                writer.WriteInt32(value.SourceCount);
                writer.WriteInt32(value.FaceCount);
                writer.WriteInt32(value.MeshCount);
                writer.WriteSingle(value.Offset);
                writer.WriteBoolean(value.ReferenceAdded);
                writer.WriteNullableString(value.BackupPath);
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
