using SourcePorter.Core.Toolchain;

namespace SourcePorter.Core.Tests;

public class ImportGameInfoTests
{
    [Fact]
    public void BuildGameInfo_makes_the_root_a_game_path_and_mounts_base_csgo()
    {
        var gi = ImportGameInfo.BuildGameInfo(@"E:\Steam\csgo");

        // The content root itself (where the gameinfo lives) is a Game search path...
        Assert.Contains("Game\t|gameinfo_path|.", gi);
        // ...and the real CS:GO dir + app 730 keep the base assets mounted.
        Assert.Contains("Game\t\"E:\\Steam\\csgo\"", gi);
        Assert.Contains("SteamAppId\t730", gi);
        Assert.StartsWith("\"GameInfo\"", gi);
    }

    [Fact]
    public void EnsureCustomGameInfo_writes_gameinfo_into_the_root()
    {
        var root = Path.Combine(Path.GetTempPath(), "spgi_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try
        {
            ImportGameInfo.EnsureCustomGameInfo(root, @"C:\csgo");
            var written = Path.Combine(root, "gameinfo.txt");
            Assert.True(File.Exists(written));
            Assert.Contains("|gameinfo_path|", File.ReadAllText(written));
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    [Fact]
    public void IsStagedContentDir_only_true_under_the_staging_root()
    {
        // A path under %TEMP%\SourcePorter is one of ours (safe to write a gameinfo into)...
        var staged = Path.Combine(MapStaging.StagingRoot, "de_gracia", "de_gracia");
        Assert.True(ImportGameInfo.IsStagedContentDir(staged));

        // ...an arbitrary user folder is not — we must never write into it.
        Assert.False(ImportGameInfo.IsStagedContentDir(@"D:\maps\my_project\content"));
        Assert.False(ImportGameInfo.IsStagedContentDir(""));
    }
}
