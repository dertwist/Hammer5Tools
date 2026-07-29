using System.Text.RegularExpressions;

namespace SourcePorter.Core.Toolchain;

/// <summary>
/// Turns the toolchain's firehose into a readable console. For every imported
/// material/model the importer emits a whole block — a VTF property dump, several
/// <c>+- Wrote file …tga</c> lines, <c>ProcessTexture</c> notices, search-path spam —
/// which is collapsed here into a single <c>Ported foo.vmat</c> / <c>Ported foo.vmdl</c>
/// line. Runs of identical lines (e.g. hundreds of <i>"Found a displacement missing a
/// needed subkey"</i>) fold into <c>… (repeated N more times)</c>. Warnings, errors,
/// leaks, and the map-import banners always pass through unchanged.
/// <para>
/// Stateful and processed line-by-line. Call <see cref="Flush"/> once at the end to
/// emit a trailing repeat-count. Not thread-safe — the caller serialises access (the
/// import streams output from several tools at once).
/// </para>
/// </summary>
public sealed partial class LogCompactor
{
    private string? _last;
    private int _repeat;

    /// <summary>Feeds one raw line in; yields 0..N console lines out.</summary>
    public IEnumerable<string> Process(string raw)
    {
        foreach (var transformed in Transform(raw ?? string.Empty))
            foreach (var emitted in Collapse(transformed))
                yield return emitted;
    }

    /// <summary>Emits any pending "repeated N more times" tail. Call once at the end.</summary>
    public IEnumerable<string> Flush() => FlushRepeat();

    // --- noise removal + per-asset summarising (raw line -> 0 or 1 line) ---
    private static IEnumerable<string> Transform(string raw)
    {
        // Blank lines and the "----" banners just add height — drop them.
        if (raw.Trim().Length == 0 || SeparatorRegex().IsMatch(raw))
            yield break;

        // Our own "- Running Command: <tool> <args>" banners -> one concise line.
        var cmd = RunningCommandRegex().Match(raw);
        if (cmd.Success)
        {
            var summary = SummarizeCommand(cmd.Groups["cmd"].Value);
            if (summary is not null)
                yield return summary;
            yield break;
        }

        // "+- Wrote file …\foo.vmat" -> "Ported foo.vmat" (and likewise vmdl/vmap);
        // intermediate textures (tga/psd/raw) are dropped.
        var wrote = WroteAssetRegex().Match(raw);
        if (wrote.Success)
        {
            var name = wrote.Groups["name"].Value;
            switch (wrote.Groups["ext"].Value.ToLowerInvariant())
            {
                case "vmat": yield return $"  Ported {name}.vmat"; break;
                case "vmdl": yield return $"  Ported {name}.vmdl"; break;
                case "vmap": yield return $"  Imported map {name}.vmap"; break;
                // tga / psd / raw: intermediate texture sources — drop.
            }
            yield break;
        }

        if (IsNoise(raw))
            yield break;

        yield return raw;
    }

    // Map a "- Running Command" body to a concise line, or null to drop it.
    private static string? SummarizeCommand(string cmd)
    {
        if (cmd.StartsWith("cs_mdl_import", StringComparison.OrdinalIgnoreCase))
        {
            var m = MdlArgRegex().Match(cmd);
            return m.Success ? $"  Ported {m.Groups["name"].Value}.vmdl" : null;
        }

        if (cmd.StartsWith("resourcecompiler", StringComparison.OrdinalIgnoreCase))
        {
            if (cmd.Contains("-filelist", StringComparison.OrdinalIgnoreCase))
                return "  Compiling dependency filelist…";
            var m = QuotedFileRegex().Match(cmd);
            return m.Success ? $"  Compiled {m.Groups["name"].Value}.{m.Groups["ext"].Value}" : null;
        }

        if (cmd.StartsWith("source1import", StringComparison.OrdinalIgnoreCase))
        {
            if (cmd.Contains("-usefilelist", StringComparison.OrdinalIgnoreCase))
                return "▶ Importing dependency sources…";
            var m = MapArgRegex().Match(cmd);
            return m.Success ? $"▶ Importing map {m.Groups["name"].Value}.vmf…" : "▶ Importing map…";
        }

        // vbsp / vpk / anything else our orchestrator runs: drop the banner.
        return null;
    }

    private static bool IsNoise(string raw)
    {
        var trimmed = raw.TrimStart();
        return raw.StartsWith("Adding Search Path", StringComparison.Ordinal)
            || raw.StartsWith("Removing Search Path", StringComparison.Ordinal)
            || raw.StartsWith("Command Line:", StringComparison.Ordinal)
            || raw.StartsWith("Creating device for graphics adapter", StringComparison.Ordinal)
            || raw.StartsWith("Blacklisting files", StringComparison.Ordinal)
            || raw.StartsWith("Building file list", StringComparison.Ordinal)
            || raw.StartsWith("File spec:", StringComparison.Ordinal)
            || raw.StartsWith("Found file to import", StringComparison.Ordinal)
            || raw.StartsWith("Final import list order", StringComparison.Ordinal)
            || raw.StartsWith("MSG_FILEWRITE", StringComparison.Ordinal)
            || raw.Contains("Failed to cache VMT specified in resource/vmtcache.txt", StringComparison.Ordinal)
            || ProgressHeaderRegex().IsMatch(raw)
            || trimmed.StartsWith("ProcessTexture", StringComparison.Ordinal)
            || trimmed.StartsWith("vtf ", StringComparison.Ordinal)
            || trimmed.StartsWith("TEXTUREFLAGS_", StringComparison.Ordinal)
            || trimmed.StartsWith("transparency:", StringComparison.Ordinal);
    }

    // --- fold consecutive identical lines into "line  (repeated N more times)" ---
    private IEnumerable<string> Collapse(string line)
    {
        if (line == _last)
        {
            _repeat++;
            yield break;
        }

        foreach (var tail in FlushRepeat())
            yield return tail;

        _last = line;
        yield return line;
    }

    private IEnumerable<string> FlushRepeat()
    {
        if (_last is not null && _repeat > 0)
        {
            yield return $"  (repeated {_repeat} more time{(_repeat == 1 ? "" : "s")})";
            _repeat = 0;
        }
    }

    [GeneratedRegex(@"^-{4,}$")]
    private static partial Regex SeparatorRegex();

    [GeneratedRegex(@"^- Running Command:\s*(?<cmd>.+)$")]
    private static partial Regex RunningCommandRegex();

    // "+- Wrote file <path>\<name>.<ext>" (ignores any trailing " (Copied from …)").
    [GeneratedRegex(@"Wrote file .*[\\/](?<name>[^\\/]+?)\.(?<ext>vmat|vmdl|vmap|tga|psd|raw)\b", RegexOptions.IgnoreCase)]
    private static partial Regex WroteAssetRegex();

    // "- (6/153) …" per-asset progress headers from source1import.
    [GeneratedRegex(@"^- \(\d+/\d+\)")]
    private static partial Regex ProgressHeaderRegex();

    [GeneratedRegex(@"""[^""]*[\\/](?<name>[^""\\/]+)\.mdl""", RegexOptions.IgnoreCase)]
    private static partial Regex MdlArgRegex();

    [GeneratedRegex(@"maps[\\/](?<name>[^\\/""]+)\.vmf", RegexOptions.IgnoreCase)]
    private static partial Regex MapArgRegex();

    [GeneratedRegex(@"""[^""]*[\\/](?<name>[^""\\/]+)\.(?<ext>vmat|vmdl)""", RegexOptions.IgnoreCase)]
    private static partial Regex QuotedFileRegex();
}
