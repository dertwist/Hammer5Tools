using SourcePorter.Core.Toolchain;

namespace SourcePorter.Core.Tests;

public class VmfDisplacementTests
{
    // A power-2 displacement as BSPSource writes it: normals/distances/alphas present,
    // but no offsets / offset_normals (the subkeys source1import requires).
    private const string DecompiledDispVmf =
        "world\r\n{\r\n\tsolid\r\n\t{\r\n\t\tside\r\n\t\t{\r\n" +
        "\t\t\tdispinfo\r\n\t\t\t{\r\n" +
        "\t\t\t\t\"power\" \"2\"\r\n" +
        "\t\t\t\t\"startposition\" \"[0 0 0]\"\r\n" +
        "\t\t\t\tnormals\r\n\t\t\t\t{\r\n\t\t\t\t\t\"row0\" \"0 0 1\"\r\n\t\t\t\t}\r\n" +
        "\t\t\t\tdistances\r\n\t\t\t\t{\r\n\t\t\t\t\t\"row0\" \"0\"\r\n\t\t\t\t}\r\n" +
        "\t\t\t}\r\n\t\t}\r\n\t}\r\n}\r\n";

    private static string WriteTemp(string content)
    {
        var path = Path.Combine(Path.GetTempPath(), "sp_disp_" + Guid.NewGuid().ToString("N") + ".vmf");
        File.WriteAllText(path, content);
        return path;
    }

    [Fact]
    public void Injects_offsets_and_offset_normals_sized_to_the_power()
    {
        var path = WriteTemp(DecompiledDispVmf);
        try
        {
            var fixedCount = VmfNormalizer.EnsureDisplacementOffsets(path);

            Assert.Equal(1, fixedCount);
            var text = File.ReadAllText(path);
            Assert.Contains("offsets", text);
            Assert.Contains("offset_normals", text);

            // power 2 -> N = 5 rows; offsets row0 is N triples of "0 0 0".
            Assert.Contains("\"row0\" \"0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\"", text);
            Assert.Contains("\"row4\" \"0 0 1 0 0 1 0 0 1 0 0 1 0 0 1\"", text);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void Is_idempotent_when_the_subkeys_already_exist()
    {
        var path = WriteTemp(DecompiledDispVmf);
        try
        {
            Assert.Equal(1, VmfNormalizer.EnsureDisplacementOffsets(path)); // first pass fixes
            Assert.Equal(0, VmfNormalizer.EnsureDisplacementOffsets(path)); // second is a no-op
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void Leaves_a_vmf_without_displacements_untouched()
    {
        var path = WriteTemp("world\r\n{\r\n\tsolid\r\n\t{\r\n\t}\r\n}\r\n");
        try
        {
            var before = File.ReadAllText(path);
            Assert.Equal(0, VmfNormalizer.EnsureDisplacementOffsets(path));
            Assert.Equal(before, File.ReadAllText(path));
        }
        finally { File.Delete(path); }
    }
}
