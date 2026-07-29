using System.Text;

namespace SourcePorter.Core.Toolchain;

/// <summary>
/// Faithful port of the list/refs helpers in Valve's <c>import_scripts/utils/utlc.py</c>.
/// These read and write the <c>importfilelist { "file" "…" }</c> KeyValues format
/// that <c>source1import</c> consumes and emits, and split model refs out of a
/// dependency list. Behaviour matches the Python 1:1 so the orchestration in
/// <see cref="MapImportService"/> stays equivalent.
/// </summary>
public static class RefsFile
{
    /// <summary>
    /// <c>ReadTextFile</c>: read lines, trim each, drop blanks and <c>//</c> comments.
    /// </summary>
    public static List<string> ReadTextFile(string path)
    {
        var result = new List<string>();
        foreach (var raw in File.ReadAllLines(path))
        {
            var line = raw.Trim();
            if (line.Length == 0)
                continue;
            if (line.StartsWith("//", StringComparison.Ordinal))
                continue;
            result.Add(line);
        }
        return result;
    }

    /// <summary>
    /// <c>RefsStringFromList</c>: wrap a list of file paths into the
    /// <c>importfilelist { "file" "…" }</c> block.
    /// </summary>
    public static string RefsStringFromList(IEnumerable<string> list)
    {
        var sb = new StringBuilder();
        sb.Append("importfilelist\n{\n");
        foreach (var entry in list)
        {
            var line = entry.Trim().Replace("\"", "");
            if (line.Length != 0)
                sb.Append("\t\"file\" \"").Append(line).Append("\"\n");
        }
        sb.Append("}\n");
        return sb.ToString();
    }

    /// <summary>
    /// <c>ListStringFromRefs</c>: parse an <c>importfilelist</c> block (already read
    /// into lines) back into a newline-joined list of file names. Mirrors the
    /// Python state machine that expects importfilelist / { / file / }.
    /// </summary>
    public static string ListStringFromRefs(IEnumerable<string> refs)
    {
        var cleaned = refs
            .Select(x => x.Replace("\"", "").Trim())
            .ToList();

        string[] expecting = ["importfilelist", "{", "file", "}", "Done"];
        var idx = 0;
        var sb = new StringBuilder();

        foreach (var line in cleaned)
        {
            if (line.Length == 0)
                continue;

            if (expecting[idx] == "Done")
                break;

            if (line.StartsWith("//", StringComparison.Ordinal) || line.StartsWith("#", StringComparison.Ordinal))
                continue;

            if (expecting[idx] == "file")
            {
                if (line.StartsWith("file", StringComparison.Ordinal))
                {
                    var fname = line[4..].Trim();
                    sb.Append(fname).Append('\n');
                }
                else if (line.StartsWith("}", StringComparison.Ordinal))
                {
                    break;
                }
                else
                {
                    throw new FormatException("Error Expecting: \"file\" <filename> or }");
                }
                continue;
            }

            if (line != expecting[idx])
                throw new FormatException($"Expecting {expecting[idx]}");

            idx++;
        }

        return sb.ToString();
    }

    /// <summary>
    /// <c>SplitMdlFromRefs</c>: split a refs block into model paths (ending in
    /// <c>.mdl</c>) and everything else.
    /// </summary>
    public static (List<string> Mdls, List<string> Others) SplitMdlFromRefs(IEnumerable<string> refs)
    {
        var flat = ListStringFromRefs(refs).Split('\n');
        var mdls = new List<string>();
        var others = new List<string>();

        foreach (var line in flat)
        {
            if (line.EndsWith(".mdl", StringComparison.OrdinalIgnoreCase))
                mdls.Add(line);
            else
                others.Add(line);
        }

        return (mdls, others);
    }

    /// <summary><c>EnsureFileWritable</c>: clear the read-only attribute if the file exists.</summary>
    public static void EnsureFileWritable(string path)
    {
        if (File.Exists(path))
            File.SetAttributes(path, File.GetAttributes(path) & ~FileAttributes.ReadOnly);
    }
}
