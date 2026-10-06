using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;

namespace Hammer5Tools.Core;

internal static unsafe class AutomationApi
{
    [UnmanagedCallersOnly(EntryPoint = "h5t_model_bounds_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int ModelBounds(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Encoding.UTF8.GetBytes(CoreApi.InspectModel(NativeInterop.ReadUtf8(request, length))));
    [UnmanagedCallersOnly(EntryPoint = "h5t_texture_inspect_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int TextureInspect(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Texture(request, length, "inspect"));
    [UnmanagedCallersOnly(EntryPoint = "h5t_texture_split_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int TextureSplit(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Texture(request, length, "split"));
    [UnmanagedCallersOnly(EntryPoint = "h5t_texture_pack_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int TexturePack(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Texture(request, length, "pack"));
    private static byte[] Texture(byte* request, int length, string operation) =>
        Encoding.UTF8.GetBytes(CoreApi.PrepareTexture(NativeInterop.ReadUtf8(request, length), operation));
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_insert_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int InsertMap(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Map(request, length, "insert"));
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_nodes_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int MapNodes(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Map(request, length, "nodes"));
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_transform_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int TransformMap(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Map(request, length, "transform"));
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_group_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int GroupMap(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Map(request, length, "group"));
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmap_zoo_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int ZooMap(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Map(request, length, "zoo"));
    private static byte[] Map(byte* request, int length, string operation) =>
        Encoding.UTF8.GetBytes(CoreApi.AuthorMap(NativeInterop.ReadUtf8(request, length), operation));
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmat_author_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int AuthorMaterial(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Author(request, length, "vmat", false));
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmdl_author_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int AuthorModel(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Author(request, length, "vmdl", false));
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmat_batch_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int BatchMaterial(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Author(request, length, "vmat", true));
    [UnmanagedCallersOnly(EntryPoint = "h5t_vmdl_batch_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int BatchModel(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Author(request, length, "vmdl", true));

    private static byte[] Author(byte* request, int length, string format, bool batch) =>
        Encoding.UTF8.GetBytes(CoreApi.AuthorSourceAssets(NativeInterop.ReadUtf8(request, length), format, batch));
    [UnmanagedCallersOnly(EntryPoint = "h5t_compile_job_status_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int JobStatus(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => JobRequest(request, length, false));

    [UnmanagedCallersOnly(EntryPoint = "h5t_compile_job_cancel_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int JobCancel(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => JobRequest(request, length, true));

    private static byte[] JobRequest(byte* request, int length, bool cancel)
    {
        using var document = JsonDocument.Parse(NativeInterop.ReadUtf8(request, length));
        var id = document.RootElement.GetProperty("job_id").GetString()!;
        return Encoding.UTF8.GetBytes(cancel ? CoreApi.CancelCompilationJob(id) : CoreApi.CompilationJobStatus(id));
    }
    [UnmanagedCallersOnly(EntryPoint = "h5t_compile_assets_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int Compile(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Encoding.UTF8.GetBytes(CoreApi.CompileAssets(NativeInterop.ReadUtf8(request, length))));

    [UnmanagedCallersOnly(EntryPoint = "h5t_compile_log_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int ReadLog(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Encoding.UTF8.GetBytes(CoreApi.ReadCompilerLog(NativeInterop.ReadUtf8(request, length))));
    [UnmanagedCallersOnly(EntryPoint = "h5t_resolve_asset_path_json", CallConvs = [typeof(CallConvCdecl)])]
    public static int ResolvePath(byte* request, int length, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            using var document = JsonDocument.Parse(NativeInterop.ReadUtf8(request, length));
            var root = document.RootElement;
            return JsonSerializer.SerializeToUtf8Bytes(CoreApi.ResolveAssetPath(
                root.GetProperty("path").GetString()!,
                root.GetProperty("addonRoot").GetString(),
                root.GetProperty("mustExist").GetBoolean()), AutomationJsonContext.Default.String);
        });
}
