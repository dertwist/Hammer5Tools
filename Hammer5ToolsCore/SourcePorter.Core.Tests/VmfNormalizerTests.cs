using SourcePorter.Core.Toolchain;

namespace SourcePorter.Core.Tests;

public class VmfNormalizerTests
{
    [Fact]
    public void Prepends_the_preamble_when_a_decompiled_vmf_starts_at_world()
    {
        var path = Path.Combine(Path.GetTempPath(), "vmfnorm_" + Guid.NewGuid().ToString("N") + ".vmf");
        File.WriteAllText(path, "world\r\n{\r\n\t\"id\" \"1\"\r\n}\r\n");
        try
        {
            Assert.False(VmfNormalizer.HasImportableHeader(path));

            var changed = VmfNormalizer.EnsureImportableHeader(path);

            Assert.True(changed);
            var text = File.ReadAllText(path);
            Assert.StartsWith("versioninfo", text);
            Assert.Contains("viewsettings", text);
            Assert.Contains("world", text); // original content preserved
            Assert.True(VmfNormalizer.HasImportableHeader(path));
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void Is_a_noop_when_the_header_is_already_present()
    {
        var path = Path.Combine(Path.GetTempPath(), "vmfnorm_" + Guid.NewGuid().ToString("N") + ".vmf");
        var original = "versioninfo\r\n{\r\n\t\"editorversion\" \"400\"\r\n}\r\nworld\r\n{\r\n}\r\n";
        File.WriteAllText(path, original);
        try
        {
            var changed = VmfNormalizer.EnsureImportableHeader(path);

            Assert.False(changed);
            Assert.Equal(original, File.ReadAllText(path)); // byte-for-byte unchanged
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void Strips_color_correction_only_when_its_raw_is_missing()
    {
        var root = Path.Combine(Path.GetTempPath(), "vmfcc_" + Guid.NewGuid().ToString("N"));
        var maps = Path.Combine(root, "maps");
        Directory.CreateDirectory(maps);
        // The "present" lookup file exists under the content root; the "missing" one doesn't.
        Directory.CreateDirectory(Path.Combine(root, "materials", "correction"));
        File.WriteAllText(Path.Combine(root, "materials", "correction", "cc_present.raw"), "x");

        var path = Path.Combine(maps, "m.vmf");
        File.WriteAllText(path,
            "world\r\n{\r\n}\r\n" +
            "entity\r\n{\r\n\t\"id\" \"1\"\r\n\t\"filename\" \"materials/correction/cc_missing.raw\"\r\n\t\"classname\" \"color_correction\"\r\n}\r\n" +
            "entity\r\n{\r\n\t\"id\" \"2\"\r\n\t\"filename\" \"materials/correction/cc_present.raw\"\r\n\t\"classname\" \"color_correction\"\r\n}\r\n" +
            "entity\r\n{\r\n\t\"id\" \"3\"\r\n\t\"classname\" \"info_player_start\"\r\n}\r\n");
        try
        {
            var removed = VmfNormalizer.EnsureNoUnresolvableColorCorrection(path, root);

            Assert.Equal(1, removed);
            var text = File.ReadAllText(path);
            Assert.DoesNotContain("cc_missing.raw", text); // the unresolvable one is gone
            Assert.Contains("cc_present.raw", text);       // the resolvable one survives (lossless)
            Assert.Contains("info_player_start", text);    // unrelated entities untouched

            // Idempotent: a second pass finds nothing left to remove.
            Assert.Equal(0, VmfNormalizer.EnsureNoUnresolvableColorCorrection(path, root));
        }
        finally { Directory.Delete(root, recursive: true); }
    }

    [Fact]
    public void Strips_color_correction_with_no_filename_key()
    {
        var root = Path.Combine(Path.GetTempPath(), "vmfcc_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        var path = Path.Combine(root, "m.vmf");
        File.WriteAllText(path,
            "entity\r\n{\r\n\t\"id\" \"1\"\r\n\t\"classname\" \"color_correction\"\r\n}\r\n");
        try
        {
            Assert.Equal(1, VmfNormalizer.EnsureNoUnresolvableColorCorrection(path, root));
            Assert.DoesNotContain("color_correction", File.ReadAllText(path));
        }
        finally { Directory.Delete(root, recursive: true); }
    }
}
