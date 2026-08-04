using SourcePorter.Core.Toolchain;

namespace SourcePorter.Core.Tests;

public class S1SourceLocatorTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), "spsrc_" + Guid.NewGuid().ToString("N"));

    private string Csgo => Path.Combine(_root, "csgo");
    private string Custom => Path.Combine(_root, "custom");

    public S1SourceLocatorTests()
    {
        Directory.CreateDirectory(Csgo);
        Directory.CreateDirectory(Custom);
    }

    private void WriteFile(string baseDir, string relForward)
    {
        var full = Path.Combine(baseDir, relForward.Replace('/', Path.DirectorySeparatorChar));
        Directory.CreateDirectory(Path.GetDirectoryName(full)!);
        File.WriteAllText(full, "x");
    }

    [Fact]
    public void Finds_loose_stock_source_in_csgo_dir()
    {
        WriteFile(Csgo, "models/props/crate.mdl");
        using var locator = new S1SourceLocator(Csgo, Custom);

        Assert.Equal(S1Source.CsgoVpk, locator.Locate("models/props/crate.mdl"));
        Assert.True(locator.Has("models/props/crate.mdl"));
    }

    [Fact]
    public void Finds_custom_content_source()
    {
        WriteFile(Custom, "materials/de_coastal/sand.vmt");
        using var locator = new S1SourceLocator(Csgo, Custom);

        Assert.Equal(S1Source.CustomContent, locator.Locate("materials/de_coastal/sand.vmt"));
    }

    [Fact]
    public void Custom_content_wins_over_stock_for_the_same_path()
    {
        WriteFile(Csgo, "materials/shared/wall.vmt");
        WriteFile(Custom, "materials/shared/wall.vmt");
        using var locator = new S1SourceLocator(Csgo, Custom);

        Assert.Equal(S1Source.CustomContent, locator.Locate("materials/shared/wall.vmt"));
    }

    [Fact]
    public void Reports_notfound_for_sourceless_asset()
    {
        using var locator = new S1SourceLocator(Csgo, Custom);

        Assert.Equal(S1Source.NotFound, locator.Locate("models/missing/gib.mdl"));
        Assert.False(locator.Has("models/missing/gib.mdl"));
    }

    [Fact]
    public void Custom_dir_equal_to_csgo_dir_is_not_double_counted_as_custom()
    {
        WriteFile(Csgo, "materials/x.vmt");
        // A loose-.vmf project can pass the csgo dir as the content dir; it must resolve as stock.
        using var locator = new S1SourceLocator(Csgo, Csgo);

        Assert.Equal(S1Source.CsgoVpk, locator.Locate("materials/x.vmt"));
    }

    // The staging area keeps one folder per previously-ported map and they are all handed in as
    // extra roots, but source1import mounts only one -src1contentdir. Picking the first root
    // (alphabetical: a stale "cs_climb_a71") instead of the one holding the files made every
    // material fail with "*** Found no files matching specification".
    [Fact]
    public void Custom_root_is_the_one_actually_holding_the_source()
    {
        var stale = Path.Combine(_root, "staging", "cs_climb_a71");
        var real = Path.Combine(_root, "staging", "de_swamp");
        Directory.CreateDirectory(stale);
        WriteFile(real, "materials/de_swamp/wood/hr_wood_planks_a.vmt");

        using var locator = new S1SourceLocator(Csgo, null, [stale, real]);

        Assert.Equal(real, locator.TryGetCustomRoot("materials/de_swamp/wood/hr_wood_planks_a.vmt"));
        Assert.Null(locator.TryGetCustomRoot("materials/de_swamp/wood/nope.vmt"));
    }

    [Fact]
    public void Handles_backslash_paths()
    {
        WriteFile(Csgo, "models/props/crate.mdl");
        using var locator = new S1SourceLocator(Csgo, null);

        Assert.True(locator.Has("models\\props\\crate.mdl".Replace('\\', '/')));
    }

    public void Dispose()
    {
        if (Directory.Exists(_root))
            Directory.Delete(_root, recursive: true);
    }
}
