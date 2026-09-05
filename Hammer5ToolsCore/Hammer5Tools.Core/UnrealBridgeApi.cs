using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;

using Hammer5Tools.Core.Format.Unreal;

namespace Hammer5Tools.Core;

/// <summary>
/// NativeAOT ABI for the Unreal content bridge (<see cref="UnrealBridgeProgram"/>).
/// Each command reuses the bridge's mounted CUE4Parse <c>DefaultFileProvider</c>
/// and returns the JSON produced by the bridge as its output buffer.
/// </summary>
internal static unsafe class UnrealBridgeApi
{
    /// <summary>Request ignored. Drops the cached project mount so the next command re-reads from disk.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_unreal_reset", CallConvs = [typeof(CallConvCdecl)])]
    public static int Reset(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            UnrealBridgeProgram.ResetProviders();
            return Utf8("{\"ok\":true}");
        });

    /// <summary>Request: {contentDir}.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_unreal_info", CallConvs = [typeof(CallConvCdecl)])]
    public static int Info(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var contentDir = RequireString(request, requestLength, "contentDir");
            var provider = UnrealBridgeProgram.MountProvider(contentDir);
            return Utf8(UnrealBridgeProgram.Info(provider, contentDir));
        });

    /// <summary>Request: {contentDir, substring}.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_unreal_list", CallConvs = [typeof(CallConvCdecl)])]
    public static int List(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var root = ParseRequest(request, requestLength);
            var contentDir = RequireString(root, "contentDir");
            var provider = UnrealBridgeProgram.MountProvider(contentDir);
            return Utf8(UnrealBridgeProgram.List(provider, GetString(root, "substring") ?? ""));
        });

    /// <summary>Request: {contentDir, objectPath}. Raw JSON of every export in the package.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_unreal_dump", CallConvs = [typeof(CallConvCdecl)])]
    public static int Dump(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var root = ParseRequest(request, requestLength);
            var provider = UnrealBridgeProgram.MountProvider(RequireString(root, "contentDir"));
            return Utf8(UnrealBridgeProgram.Dump(provider, RequireString(root, "objectPath")));
        });

    /// <summary>Request: {contentDir, objectPath}. Flat list of referenced object paths.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_unreal_iter_refs", CallConvs = [typeof(CallConvCdecl)])]
    public static int IterRefs(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var root = ParseRequest(request, requestLength);
            var provider = UnrealBridgeProgram.MountProvider(RequireString(root, "contentDir"));
            return Utf8(UnrealBridgeProgram.IterRefs(provider, RequireString(root, "objectPath")));
        });

    /// <summary>Request: {contentDir, mapPath}. Normalized actor list for the map.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_unreal_dump_scene", CallConvs = [typeof(CallConvCdecl)])]
    public static int DumpScene(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var root = ParseRequest(request, requestLength);
            var provider = UnrealBridgeProgram.MountProvider(RequireString(root, "contentDir"));
            return Utf8(UnrealBridgeProgram.DumpScene(provider, RequireString(root, "mapPath")));
        });

    /// <summary>Request: {contentDir, bpPath}. Normalized component list for the Blueprint.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_unreal_dump_blueprint", CallConvs = [typeof(CallConvCdecl)])]
    public static int DumpBlueprint(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var root = ParseRequest(request, requestLength);
            var provider = UnrealBridgeProgram.MountProvider(RequireString(root, "contentDir"));
            return Utf8(UnrealBridgeProgram.DumpBlueprint(provider, RequireString(root, "bpPath")));
        });

    /// <summary>Request: {contentDir, matPath}. Resolved textures/scalars/vectors/switches/shader flags.</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_unreal_dump_material", CallConvs = [typeof(CallConvCdecl)])]
    public static int DumpMaterial(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var root = ParseRequest(request, requestLength);
            var provider = UnrealBridgeProgram.MountProvider(RequireString(root, "contentDir"));
            return Utf8(UnrealBridgeProgram.DumpMaterial(provider, RequireString(root, "matPath")));
        });

    /// <summary>Request: {contentDir, mapPath, outDir, flags?}. <c>flags</c> is "mesh"/"heightmap"/"weightmap"/"all" (default "all").</summary>
    [UnmanagedCallersOnly(EntryPoint = "h5t_unreal_export_landscape", CallConvs = [typeof(CallConvCdecl)])]
    public static int ExportLandscape(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            var root = ParseRequest(request, requestLength);
            var provider = UnrealBridgeProgram.MountProvider(RequireString(root, "contentDir"));
            var flags = GetString(root, "flags") ?? "all";
            return Utf8(UnrealBridgeProgram.ExportLandscape(
                provider, RequireString(root, "mapPath"), RequireString(root, "outDir"), flags));
        });

    private static byte[] Utf8(string text) => Encoding.UTF8.GetBytes(text);

    private static JsonElement ParseRequest(byte* request, int requestLength) =>
        JsonDocument.Parse(NativeInterop.ReadUtf8(request, requestLength)).RootElement;

    /// <summary>Reads a single string property directly out of the raw request (info's only field).</summary>
    private static string RequireString(byte* request, int requestLength, string propertyName) =>
        RequireString(ParseRequest(request, requestLength), propertyName);

    private static string RequireString(JsonElement root, string propertyName) =>
        root.GetProperty(propertyName).GetString()
        ?? throw new ArgumentException($"'{propertyName}' must not be null.");

    private static string? GetString(JsonElement root, string propertyName) =>
        root.TryGetProperty(propertyName, out var property) && property.ValueKind == JsonValueKind.String
            ? property.GetString()
            : null;
}
