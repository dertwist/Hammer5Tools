using System.Diagnostics.CodeAnalysis;
using System.Reflection;
using Hammer5Tools.Core.IO.Vpk;
using ValveResourceFormat;
using ValveResourceFormat.IO;

namespace Hammer5Tools.Core.IO.CompiledResource;

/// <summary>Reads and decodes compiled resources without exposing parser objects.</summary>
[SuppressMessage("Design", "CA1031:Do not catch general exception types", Justification = "Resource failures are returned as structured diagnostics.")]
public sealed class CompiledResourceReader(VpkIndex index)
{
    /// <summary>Decodes a compiled sound from a mounted archive or loose root.</summary>
    public CoreResult<CompiledResourceContent> ReadSound(string path) => Read(path, "compiled_sound_read_failed");

    /// <summary>Extracts UTF-8 KeyValues3 text from a compiled SoundEvent resource.</summary>
    public CoreResult<CompiledResourceContent> ReadSoundEvents(string path) => Read(path, "compiled_soundevents_read_failed");

    private static string DetectFormat(byte[] data, string? fileName)
    {
        if (data.AsSpan().StartsWith("RIFF"u8))
            return "wav";
        // AAC ADTS syncword (0xFFFx where layer bits == 00) must be checked before MP3
        if (data.Length >= 2 && data[0] == 0xff && (data[1] & 0xf6) == 0xf0)
            return "aac";
        if (data.AsSpan().StartsWith("ID3"u8) || data.Length >= 2 && data[0] == 0xff && (data[1] & 0xe0) == 0xe0)
            return "mp3";
        var extension = Path.GetExtension(fileName);
        return extension?.ToUpperInvariant() switch
        {
            ".WAV" => "wav",
            ".MP3" => "mp3",
            ".AAC" => "aac",
            _ => "kv3",
        };
    }

    // FileExtract.Extract's return type is resolved dynamically below (its concrete
    // subtype varies by resource kind), so the trimmer/ILC cannot see the Data/FileName
    // property reads that follow. Without this, NativeAOT publish can strip them and the
    // reflection silently returns null instead of throwing.
    [DynamicDependency(DynamicallyAccessedMemberTypes.PublicProperties, typeof(ContentFile))]
    private CoreResult<CompiledResourceContent> Read(string path, string failureCode)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        try
        {
            var bytes = index.TryReadBytes(path);
            if (bytes is null)
                return CoreResult.Failure<CompiledResourceContent>("compiled_resource_missing", $"Could not find '{path}'.");
            using var stream = new MemoryStream(bytes, writable: false);
            using var resource = new Resource { FileName = path };
            resource.Read(stream);
            var method = typeof(FileExtract).GetMethods(BindingFlags.Public | BindingFlags.Static)
                .FirstOrDefault(candidate => candidate.Name == "Extract");
            if (method is null)
                return CoreResult.Failure<CompiledResourceContent>(failureCode, "The VRF extraction operation is unavailable.");
            var arguments = new object?[method.GetParameters().Length];
            arguments[0] = resource;
            var content = method.Invoke(null, arguments);
            var data = content?.GetType().GetProperty("Data")?.GetValue(content) as byte[];
            if (data is null || data.Length == 0)
                return CoreResult.Failure<CompiledResourceContent>(failureCode, $"Could not decode '{path}'.");
            var fileName = content?.GetType().GetProperty("FileName")?.GetValue(content)?.ToString();
            var format = DetectFormat(data, fileName);
            if (failureCode == "compiled_sound_read_failed" && format == "kv3")
                return CoreResult.Failure<CompiledResourceContent>(failureCode, $"'{path}' is a compound or non-audio sound container.");
            return CoreResult.Success(new CompiledResourceContent([.. data], format));
        }
        catch (Exception exception)
        {
            var inner = exception is TargetInvocationException tie ? tie.InnerException ?? exception : exception;
            return CoreResult.Failure<CompiledResourceContent>(failureCode, $"Could not decode '{path}': {inner.Message}");
        }
    }
}
