using SourcePorter.Core.Materials;

namespace SourcePorter.Core.Tests;

public class VmtToVmatConverterTests
{
    private static VmatDocument Convert(string vmt)
        => new VmtToVmatConverter().Convert(VmtFile.Parse(vmt));

    [Fact]
    public void Lightmappedgeneric_brush_material_maps_shader_and_textures()
    {
        var vmat = Convert("""
            "LightmappedGeneric"
            {
                "$basetexture" "de_coastal/sand_dirt"
                "$surfaceprop" "sand"
            }
            """);

        Assert.Equal("csgo_lightmappedgeneric.vfx", vmat.Shader);
        Assert.Equal("materials/de_coastal/sand_dirt.tga", vmat.Get("TextureColor"));
    }

    [Fact]
    public void Basetexturetransform_scale_becomes_texcoord_scale()
    {
        // The UV-scale fix: a Source 1 transform scale must survive into g_vTexCoord*Scale.
        var vmat = Convert("""
            "LightmappedGeneric"
            {
                "$basetexture" "metal/wall"
                "$basetexturetransform" "center .5 .5 scale 4 2 rotate 0 translate 0 0"
            }
            """);

        Assert.Equal("[4.000000 2.000000]", vmat.Get("g_vTexCoordScale"));
        Assert.Null(vmat.Get("g_vTexCoordOffset")); // translate was 0 0
    }

    [Fact]
    public void Basetexturetransform_translate_becomes_offset()
    {
        var vmat = Convert("""
            "LightmappedGeneric"
            {
                "$basetexture" "metal/wall"
                "$basetexturetransform" "scale 1 1 translate .5 .25"
            }
            """);

        Assert.Null(vmat.Get("g_vTexCoordScale")); // scale was 1 1
        Assert.Equal("[0.500000 0.250000]", vmat.Get("g_vTexCoordOffset"));
    }

    [Fact]
    public void Normalmap_sets_legacy_inverted_flag_and_bumpmap_is_folded_in()
    {
        var vmat = Convert("""
            "VertexLitGeneric"
            {
                "$basetexture" "models/foo"
                "$bumpmap" "models/foo_normal"
            }
            """);

        Assert.Equal("csgo_vertexlitgeneric.vfx", vmat.Shader);
        Assert.Equal("materials/models/foo_normal.tga", vmat.Get("TextureNormal"));
        Assert.Equal("1", vmat.Get("legacy_source1_inverted_normal"));
    }

    [Fact]
    public void Feature_flags_and_settings_are_emitted_with_transforms()
    {
        var vmat = Convert("""
            "VertexLitGeneric"
            {
                "$basetexture" "x"
                "$translucent" "1"
                "$phong" "1"
                "$phongexponent" "20"
                "$detailscale" "8"
            }
            """);

        Assert.Equal("1", vmat.Get("F_TRANSLUCENT"));
        Assert.Equal("1", vmat.Get("F_SPECULAR_DIRECT"));
        Assert.Equal("20.000000", vmat.Get("g_flSpecularExponent"));
        Assert.Equal("[8.000000 8.000000]", vmat.Get("g_vDetailTexCoordScale"));
    }

    [Fact]
    public void Color_int_braces_are_normalized_to_floats()
    {
        var vmat = Convert("""
            "VertexLitGeneric"
            {
                "$basetexture" "x"
                "$color" "{255 128 0}"
            }
            """);

        Assert.Equal("[1.000000 0.501961 0.000000 1.000000]", vmat.Get("g_vColorTint"));
    }

    [Fact]
    public void Surfaceprop_goes_into_system_attributes_block()
    {
        var text = Convert("""
            "LightmappedGeneric"
            {
                "$basetexture" "x"
                "$surfaceprop" "metal"
            }
            """).ToText();

        Assert.Contains("SystemAttributes", text);
        Assert.Contains("PhysicsSurfaceProperties \"metal\"", text);
    }

    [Fact]
    public void Tool_material_emits_tool_attributes()
    {
        // Tool-material detection is path-based (materials/tools/tools*), like upstream — so the
        // VMT must be parsed with that source path for the converter to treat it as a tool material.
        var vmt = VmtFile.Parse("""
            "UnlitGeneric"
            {
                "%compileclip" "1"
                "$basetexture" "tools/toolsclip"
            }
            """, sourcePath: "materials/tools/toolsclip.vmt");
        var doc = new VmtToVmatConverter().Convert(vmt);

        Assert.Equal("generic.vfx", doc.Shader);
        Assert.Contains("tools.toolsmaterial \"1\"", doc.ToText());
    }

    [Fact]
    public void Patch_material_resolves_include_and_applies_replace()
    {
        var baseVmt = """
            "LightmappedGeneric"
            {
                "$basetexture" "base/wall"
                "$surfaceprop" "concrete"
            }
            """;
        var patch = """
            "patch"
            {
                "include" "materials/base/wall.vmt"
                "replace"
                {
                    "$basetexture" "override/wall"
                }
            }
            """;

        var vmt = VmtFile.Parse(patch, _ => baseVmt);
        var vmat = new VmtToVmatConverter().Convert(vmt);

        Assert.Equal("csgo_lightmappedgeneric.vfx", vmat.Shader);
        Assert.Equal("materials/override/wall.tga", vmat.Get("TextureColor")); // replaced
        Assert.Contains("concrete", vmat.ToText()); // inherited from the included base
    }

    [Fact]
    public void Unknown_shader_falls_back_to_black_unlit()
    {
        var vmat = Convert("\"SomeWeirdShader\"\n{\n\"$basetexture\" \"x\"\n}");
        Assert.Equal("csgo_black_unlit.vfx", vmat.Shader);
    }
}
