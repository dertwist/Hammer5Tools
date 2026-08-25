namespace SourcePorter.Core.Toolchain;

/// <summary>
/// Resolves the Valve command-line tools relative to a CS2 install. The import
/// tools live under <c>game/bin/win64</c>; the legacy <c>vbsp.exe</c> used by the
/// community importer ships alongside the import scripts under
/// <c>game/csgo/import_scripts/bin</c>.
/// </summary>
/// <remarks>
/// Stub: paths are computed but existence is not yet enforced. The import
/// orchestrator (Phase 2) will validate these and surface the
/// "vpk.signatures" workaround from guide §-1.1 when reads fail.
/// </remarks>
public sealed class ValveToolLocator(string cs2GameRoot)
{
    private readonly string _bin = Path.Combine(cs2GameRoot, "bin", "win64");
    private readonly string _importBin =
        Path.Combine(cs2GameRoot, "csgo", "import_scripts", "bin");

    public string Source1Import => Path.Combine(_bin, "source1import.exe");
    public string ResourceCompiler => Path.Combine(_bin, "resourcecompiler.exe");
    public string ModelImporter => Path.Combine(_bin, "cs_mdl_import.exe");
    public string Vpk => Path.Combine(_bin, "vpk.exe");
    public string Vbsp => Path.Combine(_importBin, "vbsp.exe");

    /// <summary>The <c>vpk.signatures</c> file (guide §-1.1 workaround target).</summary>
    public string VpkSignatures => Path.Combine(_bin, "vpk.signatures");

    /// <summary>The tool list whose presence the UI should verify up front.</summary>
    public IEnumerable<(string Name, string Path)> All =>
    [
        (nameof(Source1Import), Source1Import),
        (nameof(ResourceCompiler), ResourceCompiler),
        (nameof(ModelImporter), ModelImporter),
        (nameof(Vbsp), Vbsp),
        (nameof(Vpk), Vpk),
    ];
}
