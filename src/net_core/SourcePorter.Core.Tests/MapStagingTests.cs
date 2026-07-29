using SourcePorter.Core.Domain;
using SourcePorter.Core.Toolchain;

namespace SourcePorter.Core.Tests;

public class MapStagingTests
{
    private const string Header = "versioninfo\r\n{\r\n\"editorversion\" \"400\"\r\n}\r\n";

    [Fact]
    public void StageVmf_passes_through_a_structured_map_that_already_has_the_header()
    {
        // A real file under a maps\ folder, with the required header → used in place.
        var dir = Path.Combine(Path.GetTempPath(), "sp_pass_" + Guid.NewGuid().ToString("N"), "maps");
        Directory.CreateDirectory(dir);
        var inPlace = Path.Combine(dir, "ze_example.vmf");
        File.WriteAllText(inPlace, Header + "world\r\n{\r\n}\r\n");
        try
        {
            var staged = MapStaging.StageVmf(inPlace);

            Assert.Equal(inPlace, staged); // no copy
        }
        finally { Directory.Delete(Path.GetDirectoryName(dir)!, recursive: true); }
    }

    [Fact]
    public void StageVmf_copies_a_loose_map_into_temp_and_adds_the_missing_header()
    {
        var mapName = "sp_test_" + Guid.NewGuid().ToString("N");
        var loose = Path.Combine(Path.GetTempPath(), mapName + ".vmf");
        File.WriteAllText(loose, "world\r\n{\r\n}\r\n"); // decompiled-style: no preamble
        try
        {
            var staged = MapStaging.StageVmf(loose);

            Assert.NotEqual(loose, staged);
            Assert.True(File.Exists(staged), "staged .vmf should exist");
            // It now satisfies source1import's content-dir / map-name split…
            Assert.True(Cs2Install.TryParseSourceMap(staged, out _, out var parsedName));
            Assert.Equal(mapName, parsedName);
            // …and the missing preamble was added (the fix for the Hammer round-trip).
            Assert.True(VmfNormalizer.HasImportableHeader(staged));
            // The user's original file is left untouched.
            Assert.False(VmfNormalizer.HasImportableHeader(loose));
        }
        finally
        {
            File.Delete(loose);
            var stagingDir = Path.Combine(MapStaging.StagingRoot, mapName);
            if (Directory.Exists(stagingDir))
                Directory.Delete(stagingDir, recursive: true);
        }
    }
}
