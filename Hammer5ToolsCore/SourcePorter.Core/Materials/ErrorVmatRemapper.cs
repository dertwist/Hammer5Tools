namespace SourcePorter.Core.Materials;

/// <summary>
/// Repairs <c>.vmat</c> files that Valve's <c>source1import</c> left as <c>shader "error.vfx"</c> —
/// it does that for materials whose shader it can't map (e.g. <c>Water</c>). Those files embed the
/// original Source 1 material verbatim in a <c>legacy_import { }</c> block, so this re-runs the
/// non-binary <see cref="VmtToVmatConverter"/> over that embedded VMT to produce the correct shader
/// (<c>csgo_water</c>, …) and parameters, preserving the <c>legacy_import</c> block. No toolchain,
/// and no need to locate the original <c>.vmt</c> on disk — it's already inside the file.
/// </summary>
public static class ErrorVmatRemapper
{
    /// <summary>Outcome of <see cref="FixAddon"/>.</summary>
    public sealed record Result(int Scanned, int Remapped);

    /// <summary>Walks every <c>.vmat</c> under <paramref name="contentRoot"/> and remaps the error ones.</summary>
    public static Result FixAddon(string contentRoot, Action<string>? log = null)
    {
        var materialsDir = Path.Combine(contentRoot, "materials");
        if (!Directory.Exists(materialsDir))
            return new Result(0, 0);

        var scanned = 0;
        var remapped = 0;
        foreach (var vmat in Directory.EnumerateFiles(materialsDir, "*.vmat", SearchOption.AllDirectories))
        {
            scanned++;
            if (TryRemapFile(vmat, contentRoot, log))
                remapped++;
        }
        return new Result(scanned, remapped);
    }

    /// <summary>Remaps a single <c>.vmat</c> if it's an <c>error.vfx</c> material with a usable
    /// <c>legacy_import</c> VMT. Returns true if rewritten.</summary>
    public static bool TryRemapFile(string vmatPath, string contentRoot, Action<string>? log = null)
    {
        string text;
        try { text = File.ReadAllText(vmatPath); }
        catch (IOException) { return false; }

        if (!text.Contains("error.vfx", StringComparison.OrdinalIgnoreCase))
            return false;
        if (ExtractBlock(text, "legacy_import") is not { } legacy)
            return false;

        // The inner content of legacy_import is itself a VMT: `"Water" { … }`.
        var vmt = VmtFile.Parse(legacy.Inner, sourcePath: RelativeVmtPath(vmatPath, contentRoot));
        var doc = new VmtToVmatConverter().Convert(vmt);

        // A still-unmappable shader (error/black) is no better than what we started with — leave it.
        if (doc.Shader is "error.vfx" or "csgo_black_unlit.vfx")
            return false;

        // Re-emit the original block with a clean, well-formed key.
        doc.AddRawBlock("\"legacy_import\"\n" + legacy.Braced);

        try { File.WriteAllText(vmatPath, doc.ToText(Path.GetFileName(vmatPath))); }
        catch (IOException) { return false; }

        log?.Invoke($"Remapped error.vfx → {doc.Shader}: {RelativeVmtPath(vmatPath, contentRoot)}");
        return true;
    }

    private static string RelativeVmtPath(string vmatPath, string contentRoot)
    {
        var rel = Path.GetRelativePath(contentRoot, vmatPath).Replace('\\', '/');
        return rel.EndsWith(".vmat", StringComparison.OrdinalIgnoreCase) ? rel[..^5] + ".vmt" : rel;
    }

    /// <summary>The <c>{ … }</c> block following <paramref name="key"/> (<see cref="Braced"/>) and its
    /// inner content (<see cref="Inner"/>), brace-matched while ignoring braces inside quoted strings
    /// (VMT color ints like <c>"{196 237 250}"</c>).</summary>
    private readonly record struct Block(string Braced, string Inner);

    private static Block? ExtractBlock(string text, string key)
    {
        var keyIdx = text.IndexOf(key, StringComparison.OrdinalIgnoreCase);
        if (keyIdx < 0)
            return null;

        var open = text.IndexOf('{', keyIdx);
        if (open < 0)
            return null;

        var depth = 0;
        var inQuote = false;
        for (var i = open; i < text.Length; i++)
        {
            var c = text[i];
            if (c == '"')
                inQuote = !inQuote;
            else if (!inQuote && c == '{')
                depth++;
            else if (!inQuote && c == '}')
            {
                depth--;
                if (depth == 0)
                    return new Block(text[open..(i + 1)].Trim(), text[(open + 1)..i].Trim());
            }
        }
        return null;
    }
}
