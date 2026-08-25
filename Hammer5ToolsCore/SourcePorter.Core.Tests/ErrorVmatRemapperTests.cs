using SourcePorter.Core.Materials;

namespace SourcePorter.Core.Tests;

public class ErrorVmatRemapperTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), "sperr_" + Guid.NewGuid().ToString("N"));

    public ErrorVmatRemapperTests() => Directory.CreateDirectory(_root);

    // The exact error.vfx water material source1import produced for wine_water.
    private const string WineWater = """
        "Layer0"
        {
        	"Shader"		"error.vfx"
        	"g_vErrorColorTint"		"[1.000000 0.000000 1.000000 1.000000]"
        	"SystemAttributes"
        	{
        		"PhysicsSurfaceProperties"		"Water"
        	}
        	"legacy_import"
        	{
        		"Water"
        		{
        			"$surfaceprop"		"Water"
        			"$normalmap"		"liquids/water_river_normal_sharp"
        			"$flowmap"		"vineyard/liquids/flowmap"
        			"$reflecttint"		"{196 237 250}"
        			"$refractamount"		"0.800000"
        			"%compilewater"		"1"
        			"%tooltexture"		"dev/water_normal"
        			"GPU<2"
        			{
        				"$reflecttint"		"{91 103 111}"
        			}
        		}
        	}
        }
        """;

    private string WriteVmat(string rel, string content)
    {
        var path = Path.Combine(_root, "materials", rel.Replace('/', Path.DirectorySeparatorChar));
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, content);
        return path;
    }

    [Fact]
    public void Remaps_water_error_vfx_to_csgo_water()
    {
        var path = WriteVmat("vineyard/liquids/wine_water.vmat", WineWater);

        var result = ErrorVmatRemapper.FixAddon(_root);

        Assert.Equal(1, result.Scanned);
        Assert.Equal(1, result.Remapped);

        var fixedText = File.ReadAllText(path);
        Assert.Contains("csgo_water.vfx", fixedText);
        Assert.DoesNotContain("\"error.vfx\"", fixedText);
        // A water param survived the conversion, and the original VMT is preserved for reference.
        Assert.Contains("TextureNormal", fixedText);
        Assert.Contains("legacy_import", fixedText);
    }

    [Fact]
    public void Water_with_compilewater_is_not_treated_as_a_tool_material()
    {
        // Regression: %compilewater previously made IsToolMaterial true → wrong "generic" shader.
        var vmt = VmtFile.Parse("\"Water\"\n{\n\"%compilewater\" \"1\"\n}", sourcePath: "materials/liquids/wine_water.vmt");
        Assert.False(vmt.IsToolMaterial);
        Assert.Equal("csgo_water.vfx", new VmtToVmatConverter().Convert(vmt).Shader);
    }

    [Fact]
    public void Toolsclip_path_is_still_a_tool_material()
    {
        Assert.True(VmtFile.IsToolMaterialPath("materials/tools/toolsclip_tile.vmt"));
        Assert.False(VmtFile.IsToolMaterialPath("materials/liquids/wine_water.vmt"));
        Assert.False(VmtFile.IsToolMaterialPath(null));
    }

    [Fact]
    public void Non_error_vmat_is_left_untouched()
    {
        var path = WriteVmat("ok.vmat", "Layer0\n{\n\tshader \"csgo_lightmappedgeneric.vfx\"\n}\n");
        var before = File.ReadAllText(path);

        var result = ErrorVmatRemapper.FixAddon(_root);

        Assert.Equal(0, result.Remapped);
        Assert.Equal(before, File.ReadAllText(path));
    }

    public void Dispose()
    {
        if (Directory.Exists(_root))
            Directory.Delete(_root, recursive: true);
    }
}
