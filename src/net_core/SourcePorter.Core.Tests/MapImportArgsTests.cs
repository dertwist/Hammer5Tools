using SourcePorter.Core.Domain;
using SourcePorter.Core.Toolchain;

namespace SourcePorter.Core.Tests;

/// <summary>
/// Covers the map-import argument building and the source1import <c>-usebsp</c>
/// access-violation recovery decision (see <see cref="MapImportService"/>).
/// </summary>
public class MapImportArgsTests
{
    [Fact]
    public void InitialBspMode_maps_options_to_mode()
    {
        Assert.Equal(MapImportService.BspMode.UseBsp,
            MapImportService.InitialBspMode(new ImportOptions { UseBsp = true }));
        Assert.Equal(MapImportService.BspMode.NoMerge,
            MapImportService.InitialBspMode(new ImportOptions { UseBsp = false, UseBspNoMergeInstances = true }));
        Assert.Equal(MapImportService.BspMode.None,
            MapImportService.InitialBspMode(new ImportOptions { UseBsp = false, UseBspNoMergeInstances = false }));
    }

    [Fact]
    public void BuildMapImportArgs_emits_usebsp_for_merge_mode()
    {
        var args = MapImportService.BuildMapImportArgs("s1game", "s1content", "de_grind", "de_grind", MapImportService.BspMode.UseBsp);

        Assert.Contains("-usebsp ", args); // trailing space ⇒ not the _nomergeinstances variant
        Assert.Contains("-s2addon \"de_grind\"", args);
        Assert.EndsWith("maps\\de_grind.vmf", args);
    }

    [Fact]
    public void BuildMapImportArgs_emits_nomerge_flag()
    {
        var args = MapImportService.BuildMapImportArgs("s1game", "s1content", "de_grind", "de_grind", MapImportService.BspMode.NoMerge);

        Assert.Contains("-usebsp_nomergeinstances ", args);
        Assert.DoesNotContain("-usebsp ", args);
    }

    [Fact]
    public void BuildMapImportArgs_omits_bsp_flag_for_none()
    {
        var args = MapImportService.BuildMapImportArgs("s1game", "s1content", "de_grind", "de_grind", MapImportService.BspMode.None);

        Assert.DoesNotContain("-usebsp", args);
    }

    [Fact]
    public void NextFallback_degrades_geometry_mode_one_step()
    {
        // On an access violation the import retries with progressively less BSP processing:
        // merge → no-merge → vmf-only → (give up).
        Assert.Equal(MapImportService.BspMode.NoMerge, MapImportService.NextFallback(MapImportService.BspMode.UseBsp));
        Assert.Equal(MapImportService.BspMode.None, MapImportService.NextFallback(MapImportService.BspMode.NoMerge));
        Assert.Null(MapImportService.NextFallback(MapImportService.BspMode.None));
    }

    [Fact]
    public void ConfirmIfNotCsgo_answers_the_prompt_only_for_a_non_csgo_gameinfo_dir()
    {
        // source1import only prompts when the gameinfo dir isn't named csgo (our custom-content
        // gameinfo lives in a <map>-named staged dir) — answer 'y' there, nothing for csgo.
        Assert.Null(MapImportService.ConfirmIfNotCsgo(@"E:\Steam\csgo"));
        Assert.Null(MapImportService.ConfirmIfNotCsgo(@"E:\Steam\csgo\"));
        Assert.Equal("y\n", MapImportService.ConfirmIfNotCsgo(@"C:\Temp\SourcePorter\de_gracia\de_gracia"));
    }

    [Fact]
    public void AccessViolationExitCode_is_the_windows_status_code()
    {
        // STATUS_ACCESS_VIOLATION 0xC0000005 as a signed int (what Process.ExitCode reports).
        Assert.Equal(-1073741819, MapImportService.AccessViolationExitCode);
    }
}
