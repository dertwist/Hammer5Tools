using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;

namespace Hammer5Tools.Core;

internal static unsafe class AssetGroupApi
{
    [UnmanagedCallersOnly(EntryPoint = "h5t_assetgroup_normalize_name", CallConvs = [typeof(CallConvCdecl)])]
    public static int NormalizeName(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () =>
        {
            using var document = JsonDocument.Parse(NativeInterop.ReadUtf8(request, requestLength));
            var root = document.RootElement;
            return Encoding.UTF8.GetBytes(CoreApi.NormalizeAssetGroupName(
                root.GetProperty("name").GetString() ?? "",
                root.GetProperty("sourceExtension").GetString() ?? "",
                root.GetProperty("algorithm").GetInt32()));
        });

    [UnmanagedCallersOnly(EntryPoint = "h5t_assetgroup_render_template", CallConvs = [typeof(CallConvCdecl)])]
    public static int RenderTemplate(byte* request, int requestLength, byte** output, int* outputLength) =>
        NativeInterop.Invoke(output, outputLength, () => Encoding.UTF8.GetBytes(
            CoreApi.RenderAssetGroupTemplate(NativeInterop.ReadUtf8(request, requestLength))));
}
