using SourcePorter.Core.Toolchain;

namespace SourcePorter.Core.Tests;

public class LogCompactorTests
{
    private static List<string> Run(params string[] lines)
    {
        var compactor = new LogCompactor();
        var output = new List<string>();
        foreach (var line in lines)
            output.AddRange(compactor.Process(line));
        output.AddRange(compactor.Flush());
        return output;
    }

    [Fact]
    public void A_material_block_collapses_to_one_Ported_line()
    {
        var output = Run(
            "- (6/153) vpk:…:materials\\models\\props_plants\\bushb.vmt",
            "\tProcessTexture:: Couldn't find orignal source texture (tga, psd) for models\\props_plants\\bushB!",
            "\tProcessTexture: Unable to find source texture(s) for materials\\models\\props_plants\\bushB.vtf, Converting VTF to sources.",
            "\t\tvtf width: 1024",
            "\t\tTEXTUREFLAGS_SRGB=false",
            "\t\ttransparency: noalpha",
            "\t+- Wrote file e:\\…\\content\\csgo_addons\\addon\\materials\\models\\props_plants\\bushb_color.tga",
            "\t+- Wrote file e:\\…\\content\\csgo_addons\\addon\\materials\\models\\props_plants\\bushb.vmat");

        Assert.Equal(["  Ported bushb.vmat"], output);
    }

    [Fact]
    public void A_model_import_command_becomes_a_Ported_vmdl_line()
    {
        var output = Run(
            "--------------------------------",
            "- Running Command: cs_mdl_import.exe -nop4 -i \"E:\\…\\csgo\" -o \"E:\\…\\addon\" \"models\\props\\de_inferno\\claypot03.mdl\"",
            "--------------------------------");

        Assert.Equal(["  Ported claypot03.vmdl"], output);
    }

    [Fact]
    public void The_map_import_command_is_kept_as_a_concise_banner()
    {
        var output = Run(
            "- Running Command: source1import.exe -retail -nop4 -nop4sync -usebsp -src1gameinfodir \"E:\\…\\csgo\" -src1contentdir \"E:\\…\\sdk_content\" -s2addon \"de_lake_test\" -game csgo maps\\de_lake_2.vmf");

        Assert.Equal(["▶ Importing map de_lake_2.vmf…"], output);
    }

    [Fact]
    public void Identical_consecutive_lines_fold_into_a_repeat_count()
    {
        var lines = Enumerable.Repeat("Found a displacement missing a needed subkey.", 5).ToArray();

        var output = Run(lines);

        Assert.Equal(
        [
            "Found a displacement missing a needed subkey.",
            "  (repeated 4 more times)",
        ], output);
    }

    [Fact]
    public void Warnings_errors_and_leaks_pass_through_unchanged()
    {
        var output = Run(
            "WARNING: Failed to find source 2 file for particle system explosion_coop_mission_c4",
            "VBSP FAILED, using vmf only for S2 geo.",
            "**** leaked ****");

        Assert.Equal(
        [
            "WARNING: Failed to find source 2 file for particle system explosion_coop_mission_c4",
            "VBSP FAILED, using vmf only for S2 geo.",
            "**** leaked ****",
        ], output);
    }

    [Fact]
    public void Search_path_spam_and_separators_are_dropped()
    {
        var output = Run(
            "Adding Search Path e:/…/csgo/ IMPORT_GAME",
            "--------------------------------",
            "",
            "Removing Search Path e:/…/csgo_imported BASE_MOD_EXPORT_GAME");

        Assert.Empty(output);
    }
}
