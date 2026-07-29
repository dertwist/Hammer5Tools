using SourcePorter.Core.Toolchain;

namespace SourcePorter.Core.Tests;

public class RefsFileTests
{
    [Fact]
    public void RoundTrips_through_the_importfilelist_format()
    {
        string[] input =
        [
            "materials/dev/dev_measuregeneric01.vmt",
            "models/props/cs_office/computer.mdl",
        ];

        var block = RefsFile.RefsStringFromList(input);
        var lines = block.Split('\n');

        var parsed = RefsFile.ListStringFromRefs(lines)
            .Split('\n', StringSplitOptions.RemoveEmptyEntries);

        Assert.Equal(input, parsed);
    }

    [Fact]
    public void Splits_mdl_refs_from_other_refs()
    {
        string[] input =
        [
            "materials/dev/dev_measuregeneric01.vmt",
            "models/props/cs_office/computer.mdl",
            "models/props/de_dust/hr_dust/dust_crate.mdl",
        ];

        var block = RefsFile.RefsStringFromList(input).Split('\n');
        var (mdls, others) = RefsFile.SplitMdlFromRefs(block);

        Assert.Equal(2, mdls.Count);
        Assert.All(mdls, m => Assert.EndsWith(".mdl", m));
        Assert.Contains("materials/dev/dev_measuregeneric01.vmt", others);
    }
}
