using System.Buffers;
using System.Collections.Concurrent;
using System.Diagnostics.CodeAnalysis;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text.Json;

using Hammer5Tools.Core.Format.Vmap;

namespace Hammer5Tools.Core;

/// <summary>
/// NativeAOT ABI for the git <c>.vmap</c> 3-way merge driver (<see cref="VmapMerger"/>).
/// Stateful, like <c>VpkIndex</c>: <c>open</c> loads both files (and an optional
/// ancestor), scans and diffs them, and returns a handle plus the conflict list;
/// the caller resolves any conflicts (<c>resolve</c>/<c>resolve_all</c>) and then
/// <c>write</c>s the merged file; <c>close</c> releases the loaded documents.
/// </summary>
internal static unsafe class VmapMergeApi
{
    private static readonly ConcurrentDictionary<long, VmapMergeSession> Sessions = new();
    private static long NextHandle;

    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, typeof(ElementFactory))]
    /// <summary>Request: {oursPath, theirsPath, basePath?, allowUnrelated?}.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_merge_open", CallConvs = [typeof(CallConvCdecl)])]
    public static int Open(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var root = JsonDocument.Parse(NativeInterop.ReadUtf8(request, requestLength)).RootElement;
            var oursPath = RequireString(root, "oursPath");
            var theirsPath = RequireString(root, "theirsPath");
            var basePath = GetOptionalString(root, "basePath");
            var allowUnrelated = GetBool(root, "allowUnrelated");

            var session = VmapMerger.Merge(oursPath, theirsPath, basePath, allowUnrelated);
            var handle = Interlocked.Increment(ref NextHandle);
            Sessions[handle] = session;
            return WriteSummary(handle, session);
        });

    /// <summary>Records a manual resolution for one conflicting block. side: "ours" | "theirs".</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_merge_resolve", CallConvs = [typeof(CallConvCdecl)])]
    public static int Resolve(long handle, byte* blockId, int blockIdLength, byte* side, int sideLength)
    {
        if (!Sessions.TryGetValue(handle, out var session))
            return -1;
        try
        {
            session.Resolve(NativeInterop.ReadUtf8(blockId, blockIdLength), NativeInterop.ReadUtf8(side, sideLength));
            return 0;
        }
        catch (ArgumentException)
        {
            return -1;
        }
    }

    /// <summary>Picks one side for every remaining conflict — the "primary vmap" choice.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_merge_resolve_all", CallConvs = [typeof(CallConvCdecl)])]
    public static int ResolveAll(long handle, byte* side, int sideLength)
    {
        if (!Sessions.TryGetValue(handle, out var session))
            return -1;
        session.ResolveAll(NativeInterop.ReadUtf8(side, sideLength));
        return 0;
    }

    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.Binary", "Datamodel.NET")]
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor, "Datamodel.Codecs.KeyValues2", "Datamodel.NET")]
    /// <summary>Applies the merge and writes it to outPath. Fails if conflicts remain unresolved.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_merge_write", CallConvs = [typeof(CallConvCdecl)])]
    public static int Write(long handle, byte* outPath, int outPathLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            if (!Sessions.TryGetValue(handle, out var session))
                throw new ArgumentException("Invalid merge handle.", nameof(handle));

            session.Write(NativeInterop.ReadUtf8(outPath, outPathLength));

            var buffer = new ArrayBufferWriter<byte>();
            using var writer = new Utf8JsonWriter(buffer);
            writer.WriteStartObject();
            writer.WriteStartArray("orphaned");
            foreach (var block in session.Orphaned)
                WriteBlockSummary(writer, block);
            writer.WriteEndArray();
            writer.WriteEndObject();
            writer.Flush();
            return buffer.WrittenSpan.ToArray();
        });

    /// <summary>Releases a merge session's loaded documents. Safe to call once per handle.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_merge_close", CallConvs = [typeof(CallConvCdecl)])]
    public static void Close(long handle)
    {
        if (Sessions.TryRemove(handle, out var session))
            session.Dispose();
    }

    private static byte[] WriteSummary(long handle, VmapMergeSession session)
    {
        var buffer = new ArrayBufferWriter<byte>();
        using var writer = new Utf8JsonWriter(buffer);
        writer.WriteStartObject();
        writer.WriteNumber("handle", handle);
        writer.WriteNumber("oursBlockCount", session.OursDoc.Blocks.Count);
        writer.WriteNumber("theirsBlockCount", session.TheirsDoc.Blocks.Count);
        writer.WriteNumber("realignedCount", session.Realigned.Count);

        WriteBlockArray(writer, "added", session.Added);
        WriteBlockArray(writer, "removed", session.Removed);
        WriteBlockArray(writer, "changed", session.Changed);

        writer.WriteStartArray("conflicts");
        foreach (var conflict in session.Conflicts)
        {
            writer.WriteStartObject();
            writer.WriteString("id", conflict.Id);
            writer.WriteString("kind", conflict.Kind);
            writer.WriteString("label", conflict.Label);
            writer.WriteString("reason", conflict.Reason);
            WriteOptionalString(writer, "oursDigest", conflict.Ours?.Digest);
            WriteOptionalString(writer, "theirsDigest", conflict.Theirs?.Digest);
            writer.WriteEndObject();
        }
        writer.WriteEndArray();

        writer.WriteEndObject();
        writer.Flush();
        return buffer.WrittenSpan.ToArray();
    }

    private static void WriteBlockArray(Utf8JsonWriter writer, string propertyName, IReadOnlyList<VmapMergeBlock> blocks)
    {
        writer.WriteStartArray(propertyName);
        foreach (var block in blocks)
            WriteBlockSummary(writer, block);
        writer.WriteEndArray();
    }

    private static void WriteBlockSummary(Utf8JsonWriter writer, VmapMergeBlock block)
    {
        writer.WriteStartObject();
        writer.WriteString("id", block.Id);
        writer.WriteString("kind", block.Kind);
        writer.WriteString("label", block.Label);
        writer.WriteEndObject();
    }

    private static void WriteOptionalString(Utf8JsonWriter writer, string propertyName, string? value)
    {
        if (value is null)
            writer.WriteNull(propertyName);
        else
            writer.WriteString(propertyName, value);
    }

    private static string RequireString(JsonElement root, string propertyName) =>
        root.GetProperty(propertyName).GetString()
        ?? throw new ArgumentException($"'{propertyName}' must not be null.");

    private static string? GetOptionalString(JsonElement root, string propertyName) =>
        root.TryGetProperty(propertyName, out var property) && property.ValueKind == JsonValueKind.String
            ? property.GetString()
            : null;

    private static bool GetBool(JsonElement root, string propertyName) =>
        root.TryGetProperty(propertyName, out var property) && property.GetBoolean();
}
