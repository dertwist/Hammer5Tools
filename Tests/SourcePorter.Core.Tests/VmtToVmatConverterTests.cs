using Hammer5Tools.Core.Format.Materials;

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
        var vmt = VmtFile.Parse("""
            "LightmappedGeneric"
            {
                "$basetexture" "metal/wall"
                "$basetexturetransform" "scale 1 1 translate .5 .25"
            }
            """);
        var vmat = new VmtToVmatConverter().Convert(vmt);

        Assert.Equal("scale 1 1 translate 0.5 0.25", vmt["$basetexturetransform"]);
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

    // Equivalent to the shipped materials/concrete/hr_c/hr_conc_d_blend fixture from
    // docs/blend_material_porting.md §2 (decompiled verbatim from pak01_dir.vpk). Exercises the
    // csgo_lightmappedgeneric.vfx per-shader override: F_LAYERS, the Layer1/2-prefixed names, the
    // $blendmodulatetexture → TextureBlendModulation mapping, and the vec4 detail transforms.
    [Fact]
    public void WorldVertexTransition_blend_emits_two_layers_and_blend_modulation()
    {
        var vmat = Convert("""
            "WorldVertexTransition"
            {
                "$basetexture"    "concrete/hr_c/hr_conc_d_color"
                "$bumpmap"        "concrete/hr_c/hr_conc_d_normals_normal"
                "$basetexture2"   "brick/hr_brick/inferno/brick_f_color"
                "$bumpmap2"       "brick/hr_brick/inferno/brick_f_normals_normal"
                "$blendmodulatetexture" "brick/hr_brick/inferno/flagstone_d_blend"
                "$detail"         "detail/noise_detail_01_color"
                "$detailscale"    "12"
                "$detailblendfactor" "0.25"
                "$surfaceprop"    "concrete"
            }
            """);

        Assert.Equal("csgo_lightmappedgeneric.vfx", vmat.Shader);

        // Blending is enabled by the F_LAYERS combo — without it the layer-2 samplers are dead code.
        Assert.Equal("1", vmat.Get("F_LAYERS"));

        // Layer 1: albedo is TextureColor (asymmetric), normal/detail are Layer1-prefixed.
        Assert.Equal("materials/concrete/hr_c/hr_conc_d_color.tga", vmat.Get("TextureColor"));
        Assert.Equal("materials/concrete/hr_c/hr_conc_d_normals_normal.tga", vmat.Get("TextureLayer1NormalRoughness"));
        Assert.Equal("materials/detail/noise_detail_01_color.tga", vmat.Get("TextureLayer1Detail"));

        // Layer 2 is fully prefixed.
        Assert.Equal("materials/brick/hr_brick/inferno/brick_f_color.tga", vmat.Get("TextureLayer2Color"));
        Assert.Equal("materials/brick/hr_brick/inferno/brick_f_normals_normal.tga", vmat.Get("TextureLayer2NormalRoughness"));

        // $blendmodulatetexture (dropped before this change) maps to TextureBlendModulation + F_FANCY_BLENDING.
        Assert.Equal("materials/brick/hr_brick/inferno/flagstone_d_blend.tga", vmat.Get("TextureBlendModulation"));
        Assert.Equal("1", vmat.Get("F_FANCY_BLENDING"));

        // Detail flag uses the no-underscore spelling shipped in every decompiled material.
        Assert.Equal("1", vmat.Get("F_DETAILTEXTURE"));

        // vec4 detail transforms: $detailscale pads to [s s 0 0]; $detailblendfactor is the w component.
        Assert.Equal("[12.000000 12.000000 0.000000 0.000000]", vmat.Get("g_vLayer1DetailScale"));
        Assert.Equal("[1.000000 1.000000 1.000000 0.250000]", vmat.Get("g_vLayer1DetailTintAndBlend"));

        // The wrong flat-table names must NOT be emitted for this shader.
        Assert.Null(vmat.Get("TextureColorB"));
        Assert.Null(vmat.Get("TextureNormalB"));
        Assert.Null(vmat.Get("F_DETAIL_TEXTURE")); // underscore spelling — zero shipped occurrences
    }

    // The override must not leak into the default/single-layer path: a plain lightmappedgeneric with
    // only $basetexture stays single-layer (no F_LAYERS) and its albedo is still TextureColor.
    [Fact]
    public void Plain_single_layer_lightmappedgeneric_does_not_leak_blend_override()
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
        Assert.Null(vmat.Get("F_LAYERS")); // single-layer: the combo is gated on worldvertextransition
    }
}
