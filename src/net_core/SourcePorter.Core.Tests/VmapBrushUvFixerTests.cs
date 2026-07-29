using System.Numerics;
using SourcePorter.Core.Vmap;
using Xunit;

namespace SourcePorter.Core.Tests;

/// <summary>
/// Pins the brush-UV recompute math against <b>Hammer's own ground truth</b>: the user nudged +
/// reverted UVs on a <c>blend_roofing_tile_01</c> face in Source 2 Hammer (which re-bakes the
/// correct texcoords) and saved <c>ported_fixed.vmap</c>; these are the exact values it produced.
/// Self-contained (no fixtures), so it guards the formula forever.
/// </summary>
public class VmapBrushUvFixerTests
{
    [Theory]
    // pos                       expected u      expected v   (exact values Hammer re-baked, 1024px)
    [InlineData(300f, 0f, 31f, 0.18705384f, -1.2994702f)]
    [InlineData(300f, 147f, -29f, -1.0534085f, -1.2994702f)]
    public void RecomputeTexcoord_matches_hammers_rebaked_values(
        float px, float py, float pz, float expectedU, float expectedV)
    {
        // The exact per-face mapping Hammer stored for the corrected blend_roofing_tile_01 face.
        var axisU = new Vector4(0f, -0.92584765f, 0.377897f, 97.82129f);
        var axisV = new Vector4(-1f, 0f, 0f, 884.99976f);
        const float scaleU = 0.12499547f, scaleV = 0.13540001f, dim = 1024f;

        var uv = VmapBrushUvFixer.RecomputeTexcoord(
            new Vector3(px, py, pz), axisU, axisV, scaleU, scaleV, dim, dim);

        Assert.True(Math.Abs(uv.X - expectedU) < 5e-4f, $"u {uv.X} vs {expectedU}");
        Assert.True(Math.Abs(uv.Y - expectedV) < 5e-4f, $"v {uv.Y} vs {expectedV}");
    }

    [Fact]
    public void MapVmaps_returns_only_the_imported_maps_own_files()
    {
        var root = Path.Combine(Path.GetTempPath(), "mvtest_" + Guid.NewGuid().ToString("N"));
        var maps = Path.Combine(root, "maps");
        var prefabs = Path.Combine(maps, "prefabs", "de_test");
        Directory.CreateDirectory(prefabs);
        try
        {
            File.WriteAllText(Path.Combine(maps, "de_test.vmap"), "x");                 // the main map
            File.WriteAllText(Path.Combine(prefabs, "de_test_environment.vmap"), "x");  // its prefab
            File.WriteAllText(Path.Combine(maps, "ported_raw.vmap"), "x");              // a user file — must be ignored
            File.WriteAllText(Path.Combine(maps, "ported_fixed.vmap"), "x");            // a user file — must be ignored

            var got = VmapBrushUvFixer.MapVmaps(maps, "de_test").Select(Path.GetFileName).ToHashSet();

            Assert.Equal(2, got.Count);
            Assert.Contains("de_test.vmap", got);
            Assert.Contains("de_test_environment.vmap", got);
            Assert.DoesNotContain("ported_raw.vmap", got);
            Assert.DoesNotContain("ported_fixed.vmap", got);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }
}
