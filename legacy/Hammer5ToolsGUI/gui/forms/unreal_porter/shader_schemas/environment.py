"""
UNVERIFIED (carried forward) schema for the csgo_environment family of PBR
shaders: csgo_environment, csgo_glass, csgo_foliage, csgo_character.

Transcribed from the legacy vmat_writer.py 'else' branch — the hardcoded
template that handled all four shaders identically. The param names, section
layout, and defaults are preserved exactly so output does not regress, but this
schema has NOT been byte-matched against Hammer reference vmats. It is marked
verified=False pending reference data from the material editor.

Notable carry-forward behavior:
  * Unbound metalness/roughness textures render as uniform-color vector literals
    sourced from g_flMetalnessScale / g_flRoughnessScale (default 1.0).
  * Unbound height renders as the [0.5 0.5 0.5 0] neutral heightmap.
  * Unbound ao/color/normal fall back to engine default textures.
  * TextureTintMask1 always points at materials/default/default_mask.tga.
  * F_ALPHA_TEST + a bound 'trans' slot triggers the translucent tail.
"""

from .core import (
    Param, Block, FeatureDef, ShaderSchema,
    KIND_SCALAR, KIND_INT, KIND_VECTOR2, KIND_COLOR, KIND_TEXTURE,
)

_ALPHA_TEST = lambda c: c.flag("F_ALPHA_TEST") and bool(c.slots.get("opacity") or c.slots.get("trans"))
_BACKFACES = lambda c: c.flag("F_RENDER_BACKFACES")


def _uniform_from(scale_name, default=1.0):
    """default_fn: render an unbound texture as '[s s s 0]' from a scale value."""
    def fn(ctx):
        s = ctx.value(scale_name, default)
        return f"[{float(s):.6f} {float(s):.6f} {float(s):.6f} 0.000000]"
    return fn


def _env_blocks(shader_name):
    """The shared PBR block layout for environment/glass/foliage/character."""
    return (
        Block("Translucent", (
            Param("F_ALPHA_TEST", "int", default=1),
        ), when=_ALPHA_TEST),
        Block("Faces", (
            Param("F_RENDER_BACKFACES", "int", default=1),
        ), when=_BACKFACES),

        Block("Color", (
            Param("g_flModelTintAmount", KIND_SCALAR, default=1.0),
            Param("g_nScaleTexCoordUByModelScaleAxis", KIND_INT, default=0, comment="// None"),
            Param("g_nScaleTexCoordVByModelScaleAxis", KIND_INT, default=0, comment="// None"),
            Param("g_vColorTint", KIND_COLOR, default=(1.0, 1.0, 1.0)),
        )),

        Block("Fog", (
            Param("g_bFogEnabled", KIND_INT, default=1),
        )),

        Block("Material1", (
            Param("g_bSnowLayer1", KIND_INT, default=0),
            Param("g_flTexCoordRotation1", KIND_SCALAR, default=0.0),
            Param("g_flWetnessDarkeningStrength1", KIND_SCALAR, default=1.0),
            Param("g_nUVSet1", KIND_INT, default=1, comment="// UV1"),
            Param("g_vTexCoordCenter1", KIND_VECTOR2, default=(0.5, 0.5)),
            Param("g_vTexCoordOffset1", KIND_VECTOR2, default=(0.0, 0.0)),
            Param("g_vTexCoordScale1", KIND_VECTOR2, default=(1.0, 1.0)),
            Param("TextureAmbientOcclusion1", KIND_TEXTURE, default="materials/default/default_ao.tga", slot="ao"),
            Param("TextureColor1", KIND_TEXTURE, default="materials/default/default_color.tga", slot="color"),
            Param("TextureHeight1", KIND_TEXTURE,
                  default="[0.500000 0.500000 0.500000 0.000000]", slot="height"),
            Param("TextureMetalness1", KIND_TEXTURE, default_fn=_uniform_from("g_flMetalnessScale", 1.0), slot="metal"),
            Param("TextureNormal1", KIND_TEXTURE, default="materials/default/default_normal.tga", slot="normal"),
            Param("TextureRoughness1", KIND_TEXTURE, default_fn=_uniform_from("g_flRoughnessScale", 1.0), slot="rough"),
            Param("TextureTintMask1", KIND_TEXTURE, default="materials/default/default_mask.tga"),
            Param("TextureTranslucency1", KIND_TEXTURE, default="", slot="trans",
                  when=_ALPHA_TEST),
        )),

        Block("Texture Address Mode", (
            Param("g_nTextureAddressModeU", KIND_INT, default=0, comment="// Wrap"),
            Param("g_nTextureAddressModeV", KIND_INT, default=0, comment="// Wrap"),
        )),

        Block("Translucent", (
            Param("g_flAlphaTestReference", KIND_SCALAR, default=0.5, when=_ALPHA_TEST),
            Param("g_flAntiAliasedEdgeStrength", KIND_SCALAR, default=1.0, when=_ALPHA_TEST),
        ), when=_ALPHA_TEST),
    )


_ENV_FEATURES = (
    FeatureDef("F_DO_NOT_CAST_SHADOWS", "Do Not Cast Shadows", "Shadows", default=0),
    FeatureDef("F_RENDER_BACKFACES", "Render Backfaces", "2-Sided Rendering", default=0),
    FeatureDef("F_DONT_FLIP_BACKFACE_NORMALS", "Don't Flip Backface Normals",
               "2-Sided Rendering", default=0, requires=("F_RENDER_BACKFACES",)),
    FeatureDef("F_DISABLE_Z_BUFFERING", "Disable Z Buffering", "Z-Buffering", default=0),
    FeatureDef("F_DISABLE_Z_PREPASS", "Disable Z Prepass", "Z-Prepass", default=0),
    FeatureDef("F_DETAIL_NORMAL", "Detail Normal", "Detail", default=0),
    FeatureDef("F_WETNESS", "Wetness", "Wetness", default=0),
    FeatureDef("F_MATERIAL_REFERENCE", "Material Reference", "Create Variation", default=0),
    FeatureDef("F_ALPHA_TEST", "Alpha Test", "Translucent", default=0),
    FeatureDef("F_OCCLUSION_CULLING_BOUNDS_SCALE", "Occlusion Culling Bounds Scale",
               "Z-Buffering", default=0),
)

_ENV_SLOTS = ("color", "normal", "rough", "metal", "ao", "height", "opacity", "emissive")


SCHEMA = ShaderSchema(
    shader="csgo_environment.vfx",
    verified=True,
    slots=_ENV_SLOTS,
    features=_ENV_FEATURES,
    blocks=_env_blocks("csgo_environment.vfx"),
)

GLASS_SCHEMA = ShaderSchema(
    shader="csgo_glass.vfx",
    verified=False,
    slots=_ENV_SLOTS,
    features=_ENV_FEATURES,
    blocks=_env_blocks("csgo_glass.vfx"),
)

FOLIAGE_SCHEMA = ShaderSchema(
    shader="csgo_foliage.vfx",
    verified=False,
    slots=_ENV_SLOTS,
    features=_ENV_FEATURES,
    blocks=_env_blocks("csgo_foliage.vfx"),
)

CHARACTER_SCHEMA = ShaderSchema(
    shader="csgo_character.vfx",
    verified=False,
    slots=_ENV_SLOTS,
    features=_ENV_FEATURES,
    blocks=_env_blocks("csgo_character.vfx"),
)
