using SourcePorter.Core.Toolchain;

namespace SourcePorter.Core.Tests;

public class RefsCleanupTests
{
    [Fact]
    public void Clean_removes_only_scratch_txt_files_and_leaves_real_assets_untouched()
    {
        var root = Path.Combine(Path.GetTempPath(), "sp_refs_" + Guid.NewGuid().ToString("N"));
        var models = Path.Combine(root, "models");
        var refsDir = Path.Combine(models, "prop_refs", "mesh");
        Directory.CreateDirectory(refsDir);
        try
        {
            // Real ported assets — must survive.
            File.WriteAllText(Path.Combine(models, "prop.vmdl"), "vmdl");
            var materials = Path.Combine(root, "materials");
            Directory.CreateDirectory(materials);
            File.WriteAllText(Path.Combine(materials, "prop.vmat"), "vmat");
            File.WriteAllText(Path.Combine(models, "prop.dmx"), "mesh");

            // Scratch files the importer regenerates every run — must be removed.
            File.WriteAllText(Path.Combine(models, "prop_refs.txt"), "refs");
            File.WriteAllText(Path.Combine(models, "prop_mdl_lst.txt"), "lst");
            File.WriteAllText(Path.Combine(refsDir, "meshinfo.txt"), "numUVs=1");

            var result = RefsCleanup.Clean(root);

            Assert.Equal(2, result.FileCount); // prop_refs.txt + prop_mdl_lst.txt
            Assert.Equal(1, result.DirCount);  // prop_refs\ (only held meshinfo.txt)
            Assert.True(File.Exists(Path.Combine(models, "prop.vmdl")));
            Assert.True(File.Exists(Path.Combine(materials, "prop.vmat")));
            Assert.True(File.Exists(Path.Combine(models, "prop.dmx")));
            Assert.False(Directory.Exists(refsDir));
            Assert.False(File.Exists(Path.Combine(models, "prop_refs.txt")));
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    [Fact]
    public void Clean_never_deletes_a_refs_dir_that_holds_a_non_txt_file()
    {
        var root = Path.Combine(Path.GetTempPath(), "sp_refs_" + Guid.NewGuid().ToString("N"));
        var refsDir = Path.Combine(root, "models", "prop_refs", "mesh");
        Directory.CreateDirectory(refsDir);
        try
        {
            File.WriteAllText(Path.Combine(refsDir, "meshinfo.txt"), "numUVs=1");
            // Not a real importer output, but proves the guard is content-based, not name-based.
            File.WriteAllText(Path.Combine(refsDir, "prop.vmdl"), "vmdl");

            var result = RefsCleanup.Clean(root);

            Assert.Equal(0, result.DirCount);
            Assert.True(Directory.Exists(refsDir));
            Assert.True(File.Exists(Path.Combine(refsDir, "prop.vmdl")));
        }
        finally { Directory.Delete(root, recursive: true); }
    }
}
