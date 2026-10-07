namespace Hammer5Tools.Core.IO.SoundEvents;

using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using Hammer5Tools.Core.Cs2;
using SteamDatabase.ValvePak;

/// <summary>Previews loose or compiled audio using the Windows media subsystem.</summary>
public sealed partial class SoundPreview(ICs2Locator? locator) : IDisposable
{
    private readonly string Alias = $"h5t_audio_{Guid.NewGuid():N}";
    private string? TemporaryPath;
    private bool Open;
    private int Revision;

    /// <summary>Returns the playback position in milliseconds.</summary>
    public int Position => Status("position");

    /// <summary>Returns the decoded audio duration in milliseconds.</summary>
    public int Duration => Status("length");

    /// <summary>Decodes a resource if necessary and begins playback.</summary>
    public async Task PlayAsync(string path, string? contentRoot, bool loop, CancellationToken cancellationToken = default)
    {
        if (!OperatingSystem.IsWindows()) throw new PlatformNotSupportedException("Audio preview requires Windows.");
        Stop();
        var revision = Revision;
        var prepared = await Task.Run(() => Prepare(path, contentRoot, cancellationToken), cancellationToken);
        if (prepared.Temporary) TemporaryPath = prepared.Path;
        try
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (revision != Revision) throw new OperationCanceledException("Preview was stopped.");
            Send($"open \"{prepared.Path}\" type mpegvideo alias {Alias}");
            Open = true;
            Send($"set {Alias} time format milliseconds");
            Send($"play {Alias}" + (loop ? " repeat" : string.Empty));
        }
        catch
        {
            Stop();
            throw;
        }
    }

    /// <summary>Seeks without reopening the file.</summary>
    public void Seek(int milliseconds, bool loop)
    {
        if (!OperatingSystem.IsWindows() || !Open) return;
        Send($"play {Alias} from {Math.Clamp(milliseconds, 0, Duration)}" + (loop ? " repeat" : string.Empty));
    }

    /// <summary>Stops playback and releases the decoded temporary file.</summary>
    public void Stop()
    {
        Revision++;
        if (OperatingSystem.IsWindows() && Open)
        {
            MciSendString($"close {Alias}", null, 0, IntPtr.Zero);
            Open = false;
        }
        if (TemporaryPath is { } path)
        {
            File.Delete(path);
            TemporaryPath = null;
        }
    }

    private (string Path, bool Temporary) Prepare(string path, string? contentRoot, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var resolved = Path.IsPathRooted(path) ? path : contentRoot is null ? null : Path.Combine(contentRoot, path);
        if (resolved is not null && File.Exists(resolved) && Path.GetExtension(resolved).ToLowerInvariant() is ".wav" or ".mp3") return (resolved, false);
        byte[] bytes;
        if (resolved is not null && File.Exists(resolved)) bytes = File.ReadAllBytes(resolved);
        else
        {
            var root = locator?.FindCs2Path() ?? throw new FileNotFoundException("No CS2 installation was found.");
            using var package = new Package();
            package.Read(Path.Combine(root, "game", "csgo", "pak01_dir.vpk"));
            var resourcePath = path.Replace('\\', '/');
            if (!resourcePath.EndsWith("_c", StringComparison.Ordinal)) resourcePath += "_c";
            var entry = package.FindEntry(resourcePath) ?? throw new FileNotFoundException($"Could not find {path}.");
            package.ReadEntry(entry, out bytes);
        }
        using var stream = new MemoryStream(bytes);
        using var resource = new ValveResourceFormat.Resource();
        resource.Read(stream);
        using var content = ValveResourceFormat.IO.FileExtract.Extract(resource, null!);
        var data = content.Data ?? throw new InvalidDataException("The sound contains no decoded audio.");
        var extension = data.AsSpan().StartsWith("RIFF"u8) ? ".wav" : ".mp3";
        var temporary = Path.Combine(Path.GetTempPath(), $"h5t-audio-{Guid.NewGuid():N}{extension}");
        cancellationToken.ThrowIfCancellationRequested();
        File.WriteAllBytes(temporary, data);
        return (temporary, true);
    }

    private int Status(string key)
    {
        if (!OperatingSystem.IsWindows() || !Open) return 0;
        var result = new char[64];
        if (MciSendString($"status {Alias} {key}", result, result.Length, IntPtr.Zero) != 0) return 0;
        var end = Array.IndexOf(result, '\0');
        return int.TryParse(result.AsSpan(0, end < 0 ? result.Length : end), out var value) ? value : 0;
    }

    [SupportedOSPlatform("windows")]
    private static void Send(string command)
    {
        var code = MciSendString(command, null, 0, IntPtr.Zero);
        if (code != 0) throw new InvalidOperationException($"Windows audio preview failed ({code}).");
    }

    [SupportedOSPlatform("windows")]
    [LibraryImport("winmm.dll", EntryPoint = "mciSendStringW", StringMarshalling = StringMarshalling.Utf16)]
    private static partial uint MciSendString(string command, [Out] char[]? result, int resultLength, IntPtr callback);

    /// <inheritdoc/>
    public void Dispose() => Stop();
}
