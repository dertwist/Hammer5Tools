using SourcePorter.Core.Validation;

namespace SourcePorter.Core.Tests;

public class AddonStatsTests
{
    [Fact]
    public void Counts_assets_and_sums_sizes_across_content_and_game_trees()
    {
        var root = Path.Combine(Path.GetTempPath(), "sp_stats_" + Guid.NewGuid().ToString("N"));
        var content = Path.Combine(root, "content");
        var game = Path.Combine(root, "game");
        Directory.CreateDirectory(Path.Combine(content, "materials"));
        Directory.CreateDirectory(Path.Combine(content, "models"));
        Directory.CreateDirectory(Path.Combine(content, "maps"));
        Directory.CreateDirectory(Path.Combine(game, "maps"));
        try
        {
            File.WriteAllText(Path.Combine(content, "materials", "a.vmat"), new string('x', 100));
            File.WriteAllText(Path.Combine(content, "materials", "a_color.tga"), new string('x', 50));
            File.WriteAllText(Path.Combine(content, "models", "m.vmdl"), "y");
            File.WriteAllText(Path.Combine(content, "maps", "lvl.vmap"), "z");
            File.WriteAllText(Path.Combine(game, "maps", "lvl.vmap_c"), new string('q', 200));

            var stats = AddonStats.Collect(content, game);

            Assert.Equal(1, stats.Materials);
            Assert.Equal(1, stats.Models);
            Assert.Equal(1, stats.Maps);
            Assert.Equal(1, stats.Textures);
            Assert.Equal(1, stats.CompiledFiles);
            Assert.Equal(152, stats.ContentBytes); // 100 + 50 + 1 + 1
            Assert.Equal(200, stats.GameBytes);
            Assert.Equal(352, stats.TotalBytes);
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    [Fact]
    public void Missing_dirs_yield_empty_stats_rather_than_throwing()
    {
        var stats = AddonStats.Collect(
            Path.Combine(Path.GetTempPath(), "nope_" + Guid.NewGuid().ToString("N")),
            Path.Combine(Path.GetTempPath(), "nope_" + Guid.NewGuid().ToString("N")));

        Assert.Equal(0, stats.TotalBytes);
        Assert.Equal(0, stats.Materials);
    }

    [Theory]
    [InlineData(0, "0 B")]
    [InlineData(512, "512 B")]
    [InlineData(1024, "1.0 KB")]
    [InlineData(1536, "1.5 KB")]
    [InlineData(1048576, "1.0 MB")]
    public void Human_renders_byte_sizes(long bytes, string expected)
    {
        Assert.Equal(expected, AddonStats.Human(bytes));
    }
}
