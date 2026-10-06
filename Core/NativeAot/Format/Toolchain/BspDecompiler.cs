using System.IO.Compression;
using System.Linq;

using Hammer5Tools.Core.IO.Toolchain;

namespace Hammer5Tools.Core.Format.Toolchain;

/// <summary>
/// Decompiles a Source 1 <c>.bsp</c> back to a <c>.vmf</c> using
/// <a href="https://github.com/ata4/bspsrc/">BSPSource</a> so it can then go through
/// the normal VMF import path. BSPSource is bundled as a single self-contained
/// <c>bspsrc.exe</c> (it carries its own Java runtime), shipped under
/// <c>tools/bspsrc/</c> next to the app — no system Java is required.
/// </summary>
public sealed class BspDecompiler(ProcessRunner runner, string? bspsrcLocation = null)
{
    public event Action<string>? OnLog;

    /// <summary>
    /// Decompiles <paramref name="bspPath"/> to <paramref name="outputVmfPath"/>. When
    /// <paramref name="unpackEmbedded"/> is set, the BSP's embedded files (custom
    /// materials/models/etc. the mapper packed into the map) are extracted too, so the
    /// imported addon is self-contained. Returns the written <c>.vmf</c> and the unpack
    /// directory (if any) — see <see cref="BspDecompileResult"/>.
    /// </summary>
    public async Task<BspDecompileResult> DecompileAsync(
        string bspPath, string outputVmfPath, bool unpackEmbedded = false, CancellationToken ct = default)
    {
        if (!File.Exists(bspPath))
            throw new FileNotFoundException("BSP not found.", bspPath);

        bspPath = EnsureUnarchivedBsp(bspPath, OnLog);

        var exe = ResolveExe(bspsrcLocation)
            ?? throw new FileNotFoundException(
                "bspsrc.exe not found. It ships under tools/bspsrc/ next to the app; " +
                "rebuild it from tools/bspsrc-launcher, or set its path in settings.");

        Directory.CreateDirectory(Path.GetDirectoryName(outputVmfPath)!);

        // `bspsrc [OPTIONS] <bsp>...` with `-o <file>` as the .vmf destination. We do NOT use
        // BSPSource's `--unpack_embedded`: its "smart" unpack drops vbsp-generated materials
        // (e.g. the `maps/<map>/…_wvt_patch.vmt` worldvertextransition patches the map references).
        // Instead we extract the BSP's pakfile in full ourselves (BspPakfile.ExtractAll, below).
        var args = $"-o \"{outputVmfPath}\" \"{bspPath}\"";
        OnLog?.Invoke($"Decompiling {Path.GetFileName(bspPath)} with BSPSource" +
                      (unpackEmbedded ? " (unpacking embedded content)…" : "…"));

        void Forward(ProcessLine line) => OnLog?.Invoke(line.Text);
        runner.OnOutput += Forward;
        try
        {
            // BSPSource exits 0 even when a file fails (it logs the error instead), so
            // the missing-output check below — not the exit code — is the real gate.
            var exit = await runner.RunAsync(exe, args, Path.GetDirectoryName(exe), null, null, ct);
            if (exit != 0)
                throw new InvalidOperationException($"BSPSource failed (exit {exit}).");
        }
        finally
        {
            runner.OnOutput -= Forward;
        }

        if (!File.Exists(outputVmfPath))
            throw new InvalidOperationException(
                $"BSPSource did not produce {outputVmfPath} — see the log above for the cause.");

        // Extract the BSP's embedded pakfile in FULL into a sibling dir named after the output
        // .vmf (e.g. `<out-dir>\<map>\materials\…`), which becomes the content root. Full (not
        // BSPSource's filtered) extraction is what surfaces the vbsp-generated _wvt_patch
        // materials and every other packed resource the import needs.
        string? unpackDir = null;
        if (unpackEmbedded)
        {
            var candidate = Path.Combine(
                Path.GetDirectoryName(outputVmfPath)!,
                Path.GetFileNameWithoutExtension(outputVmfPath));
            using var pak = BspPakfile.Open(bspPath);
            if (pak.EntryCount > 0)
            {
                var n = pak.ExtractAll(candidate, m => OnLog?.Invoke(m));
                OnLog?.Invoke($"Unpacked {n} of {pak.EntryCount} embedded file(s) from the BSP pakfile (full, unfiltered).");
                unpackDir = candidate;
            }
            else
            {
                OnLog?.Invoke("No embedded files unpacked (map packs no custom content).");
            }
        }

        VmfNormalizer.EnsureImportableHeader(outputVmfPath, m => OnLog?.Invoke(m));
        VmfNormalizer.EnsureDisplacementOffsets(outputVmfPath, m => OnLog?.Invoke(m));
        // The content root source1import will read materials from is the unpack dir (or, when
        // nothing was unpacked, the .vmf's own dir). Strip color_correction entities whose .raw
        // isn't there — source1import access-violates on an unresolvable color-correction file.
        VmfNormalizer.EnsureNoUnresolvableColorCorrection(
            outputVmfPath, unpackDir ?? Path.GetDirectoryName(outputVmfPath)!, m => OnLog?.Invoke(m));

        return new BspDecompileResult(outputVmfPath, unpackDir);
    }

    /// <summary>Locates <c>bspsrc.exe</c> from an explicit path/dir, else <c>tools/bspsrc/</c> by the exe.</summary>
    public static string? ResolveExe(string? location)
    {
        if (!string.IsNullOrWhiteSpace(location))
        {
            if (File.Exists(location))
                return location;
            var inDir = Path.Combine(location, "bspsrc.exe");
            if (File.Exists(inDir))
                return inDir;
        }

        var env = Environment.GetEnvironmentVariable("H5T_BSPSRC");
        if (!string.IsNullOrWhiteSpace(env) && File.Exists(env))
            return env;

        var candidates = new[]
        {
            Path.Combine(AppContext.BaseDirectory, "tools", "bspsrc", "bspsrc.exe"),
            Path.Combine(AppContext.BaseDirectory, "app", "tools", "bspsrc", "bspsrc.exe"),
            Path.Combine(Environment.CurrentDirectory, "tools", "bspsrc", "bspsrc.exe"),
            Path.Combine(Environment.CurrentDirectory, "app", "tools", "bspsrc", "bspsrc.exe"),
            Path.Combine(AppContext.BaseDirectory, "..", "tools", "bspsrc", "bspsrc.exe"),
            Path.Combine(AppContext.BaseDirectory, "..", "app", "tools", "bspsrc", "bspsrc.exe"),
            Path.Combine(AppContext.BaseDirectory, "..", "..", "tools", "bspsrc", "bspsrc.exe"),
            Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "tools", "bspsrc", "bspsrc.exe"),
        };

        foreach (var candidate in candidates)
        {
            try
            {
                var full = Path.GetFullPath(candidate);
                if (File.Exists(full))
                    return full;
            }
            catch { }
        }

        return null;
    }

    /// <summary>
    /// Checks if <paramref name="path"/> is a ZIP archive (common for Steam Workshop / UGC downloads
    /// saved with a <c>.bsp</c> extension). If so, extracts it to a temporary directory and returns
    /// the path to the inner <c>.bsp</c> file.
    /// </summary>
    public static string EnsureUnarchivedBsp(string path, Action<string>? log = null)
    {
        if (!File.Exists(path))
            return path;

        try
        {
            using var stream = File.OpenRead(path);
            Span<byte> header = stackalloc byte[4];
            if (stream.Length >= 4 && stream.Read(header) == 4)
            {
                if (header[0] == 0x50 && header[1] == 0x4B && header[2] == 0x03 && header[3] == 0x04)
                {
                    log?.Invoke($"'{Path.GetFileName(path)}' is a ZIP archive archive. Unpacking inner BSP...");

                    var tempDir = Path.Combine(Path.GetTempPath(), "SourcePorter", "UnpackedArchives", Path.GetFileNameWithoutExtension(path));
                    Directory.CreateDirectory(tempDir);

                    ZipFile.ExtractToDirectory(path, tempDir, overwriteFiles: true);

                    var bsp = Directory.GetFiles(tempDir, "*.bsp", SearchOption.AllDirectories).FirstOrDefault();
                    if (bsp != null)
                    {
                        log?.Invoke($"Extracted inner BSP file: '{Path.GetFileName(bsp)}'");
                        return bsp;
                    }
                    else
                    {
                        log?.Invoke($"Warning: No .bsp file found inside zip archive '{path}'.");
                    }
                }
            }
        }
        catch (Exception ex)
        {
            log?.Invoke($"Failed to inspect/unpack archive: {ex.Message}");
        }

        return path;
    }
}

/// <summary>
/// Outcome of a <see cref="BspDecompiler.DecompileAsync"/> run: the path of the
/// written <c>.vmf</c> and, when embedded files were unpacked, the directory they
/// were extracted into (a ready-made content root with <c>materials\</c>,
/// <c>models\</c>, … ). <see cref="UnpackDir"/> is null when nothing was unpacked.
/// </summary>
public sealed record BspDecompileResult(string VmfPath, string? UnpackDir);
