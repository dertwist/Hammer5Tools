namespace SourcePorter.Core.Domain;

/// <summary>
/// Flags passed through to <c>source1import</c>, mirroring the switches exposed
/// by Valve's <c>import_map_community.py</c> GUI.
/// </summary>
public sealed class ImportOptions
{
    /// <summary>
    /// Generate and use a BSP on import (runs the map through <c>vbsp</c> for clean
    /// geometry). Highly recommended. Mutually exclusive with
    /// <see cref="UseBspNoMergeInstances"/>.
    /// </summary>
    public bool UseBsp { get; set; } = true;

    /// <summary>Like <see cref="UseBsp"/> but keeps func_instance hierarchy (no merge).</summary>
    public bool UseBspNoMergeInstances { get; set; }

    /// <summary>Only produce the .vmap(s); skip importing/compiling dependencies.</summary>
    public bool SkipDeps { get; set; }

    /// <summary>
    /// Compile the imported asset <em>sources</em> (materials, models, refs) to their
    /// <c>_c</c> files via <c>resourcecompiler</c> during the dependency phase. When
    /// <c>false</c> (the default, for speed) the dependencies are still <em>imported</em>
    /// — so the addon's <c>content\</c> tree is fully populated — but the slow
    /// per-asset compile is skipped, leaving compilation to Hammer (or a later run with
    /// this enabled). Independent of <see cref="SkipDeps"/> (which skips importing deps
    /// entirely) and of the main-map <c>.vmap</c> compile (see
    /// <see cref="MapImportService.CompileMapAsync"/>).
    /// </summary>
    public bool CompileAssets { get; set; }

    /// <summary>Tee the toolchain console output to a log file (guide §1.2.2.1).</summary>
    public bool WriteLog { get; set; } = true;

    /// <summary>
    /// Collapse the toolchain's verbose per-asset output (VTF dumps, "Wrote file …tga",
    /// ProcessTexture notices, search-path spam, command banners) into one concise line
    /// per imported material/model — "Ported foo.vmat", "Ported foo.vmdl" — and fold
    /// runs of identical lines into "… (repeated N more times)". Warnings, errors, and
    /// the map-import banners always pass through unchanged. On by default. See
    /// <see cref="Toolchain.LogCompactor"/>.
    /// </summary>
    public bool CompactLog { get; set; } = true;

    /// <summary>
    /// Max concurrent tool processes for the dependency phase (model import +
    /// material compile run in parallel). 1 = sequential (matches the Python).
    /// Defaults to all available logical processors minus one (min 1).
    /// </summary>
    public int MaxParallelism { get; set; } = Math.Max(1, Environment.ProcessorCount - 1);
}
