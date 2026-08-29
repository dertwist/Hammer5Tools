using System.Buffers;
using System.Diagnostics.CodeAnalysis;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text.Json;

using Hammer5Tools.Core.Format.NavMesh;

namespace Hammer5Tools.Core;

/// <summary>NativeAOT ABI for NAV-based radar generation.</summary>
internal static unsafe class NavMeshRadarApi
{
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

            var radarRequest = new NavMeshRadarRequest(
                root.GetProperty("vpkPath").GetString() ?? "",
                root.GetProperty("mainVmapPath").GetString() ?? "",
                mode,
                root.TryGetProperty("offset", out var offset) ? offset.GetSingle() : 16f,
                root.TryGetProperty("materialPath", out var material)
                    ? material.GetString() ?? ""
                    : "materials/radgen/radgen_path.vmat",
                addPrefabReference,
                collapseFaces);
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
        });
}
