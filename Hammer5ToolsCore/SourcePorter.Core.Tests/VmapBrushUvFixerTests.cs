using System.Numerics;
using Hammer5Tools.Core.Format.Vmap;
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

    [Fact]
    public void ResolveDim_strips_materials_prefix_and_falls_back_to_basetexture2()
    {
        var root = Path.Combine(Path.GetTempPath(), "dimtest_" + Guid.NewGuid().ToString("N"));
        var matDir = Path.Combine(root, "materials", "custom");
        Directory.CreateDirectory(matDir);
        try
        {
            // VMT referencing $basetexture with leading "materials/" prefix
            var vmt1 = Path.Combine(matDir, "wall.vmt");
            File.WriteAllText(vmt1, "\"LightmappedGeneric\"\n{\n\t\"$basetexture\"\t\"materials/custom/wall_diffuse\"\n}");

            // Create valid minimal 512x512 VTF file header
            var vtf1 = Path.Combine(matDir, "wall_diffuse.vtf");
            byte[] vtfHeader = new byte[64];
            vtfHeader[0] = (byte)'V'; vtfHeader[1] = (byte)'T'; vtfHeader[2] = (byte)'F'; vtfHeader[3] = 0; // VTF\0
            BitConverter.GetBytes(7u).CopyTo(vtfHeader, 4); // version major 7
            BitConverter.GetBytes(4u).CopyTo(vtfHeader, 8); // version minor 4
            BitConverter.GetBytes((ushort)512).CopyTo(vtfHeader, 16); // width
            BitConverter.GetBytes((ushort)512).CopyTo(vtfHeader, 18); // height
            File.WriteAllBytes(vtf1, vtfHeader);

            var cache = new Dictionary<string, (float W, float H)?>();
            var res1 = VmapBrushUvFixer.ResolveDim("materials/custom/wall.vmat", root, cache);

            Assert.NotNull(res1);
            Assert.Equal(512f, res1.Value.W);
            Assert.Equal(512f, res1.Value.H);

            // VMT with only $basetexture2
            var vmt2 = Path.Combine(matDir, "blend.vmt");
            File.WriteAllText(vmt2, "\"WorldVertexTransition\"\n{\n\t\"$basetexture2\"\t\"custom/wall_diffuse\"\n}");
            var res2 = VmapBrushUvFixer.ResolveDim("materials/custom/blend.vmat", root, cache);

            Assert.NotNull(res2);
            Assert.Equal(512f, res2.Value.W);
            Assert.Equal(512f, res2.Value.H);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    [Fact]
    public void TextureHeaderReader_reads_tga_and_png_dimensions()
    {
        var dir = Path.Combine(Path.GetTempPath(), "texhdrtest_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        try
        {
            // TGA 1024x512
            var tgaPath = Path.Combine(dir, "test.tga");
            byte[] tgaHeader = new byte[18];
            BitConverter.GetBytes((ushort)1024).CopyTo(tgaHeader, 12);
            BitConverter.GetBytes((ushort)512).CopyTo(tgaHeader, 14);
            File.WriteAllBytes(tgaPath, tgaHeader);

            var tgaDim = Hammer5Tools.Core.Format.Materials.TextureHeaderReader.TryReadDimensions(tgaPath);
            Assert.NotNull(tgaDim);
            Assert.Equal(1024, tgaDim.Value.Width);
            Assert.Equal(512, tgaDim.Value.Height);

            // PNG 2048x1024
            var pngPath = Path.Combine(dir, "test.png");
            byte[] pngHeader = new byte[24];
            pngHeader[0] = 0x89; pngHeader[1] = (byte)'P'; pngHeader[2] = (byte)'N'; pngHeader[3] = (byte)'G';
            System.Buffers.Binary.BinaryPrimitives.WriteInt32BigEndian(pngHeader.AsSpan(16), 2048);
            System.Buffers.Binary.BinaryPrimitives.WriteInt32BigEndian(pngHeader.AsSpan(20), 1024);
            File.WriteAllBytes(pngPath, pngHeader);

            var pngDim = Hammer5Tools.Core.Format.Materials.TextureHeaderReader.TryReadDimensions(pngPath);
            Assert.NotNull(pngDim);
            Assert.Equal(2048, pngDim.Value.Width);
            Assert.Equal(1024, pngDim.Value.Height);
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }
}
