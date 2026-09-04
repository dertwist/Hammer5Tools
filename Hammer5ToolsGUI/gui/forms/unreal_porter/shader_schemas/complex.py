"""
Schema definition for csgo_complex.vfx.

Derived from VRF reconstructed csgo_complex shader (Source 2 Viewer).
Defines complete feature list, sections, feature rules (Requires, Allow1, ChildOf),
texture slots, and parameter blocks.
"""

from .core import (
    Param, Block, FeatureDef, ShaderSchema,
    KIND_SCALAR, KIND_INT, KIND_VECTOR2, KIND_IVECTOR2, KIND_COLOR, KIND_TEXTURE,
)

_ALPHA_OR_TRANS = lambda c: c.flag("F_ALPHA_TEST") or c.flag("F_TRANSLUCENT")
_BACKFACES = lambda c: c.flag("F_RENDER_BACKFACES")
_SELF_ILLUM = lambda c: c.flag("F_SELF_ILLUM")
_DETAIL = lambda c: c.flag_enum("F_DETAIL_TEXTURE") != 0
_ANIM = lambda c: c.flag("F_TEXTURE_ANIMATION")
_TINT_MASK = lambda c: c.flag("F_TINT_MASK")

COMPLEX_FEATURES = (
    FeatureDef("F_DO_NOT_CAST_SHADOWS", "Do Not Cast Shadows", "Shadows", default=0),
    FeatureDef("F_RENDER_BACKFACES", "Render Backfaces", "2-Sided Rendering", default=0),
    FeatureDef("F_DONT_FLIP_BACKFACE_NORMALS", "Don't Flip Backface Normals",
               "2-Sided Rendering", default=0, requires=("F_RENDER_BACKFACES",)),
    FeatureDef("F_DISABLE_Z_BUFFERING", "Disable Z Buffering", "Z-Buffering", default=0,
               excludes=("F_DEPTH_BIAS",)),
    FeatureDef("F_DISABLE_Z_PREPASS", "Disable Z Prepass", "Z-Prepass", default=0),
    FeatureDef("F_ALPHA_TEST", "Alpha Test", "Translucent", default=0,
               excludes=("F_TRANSLUCENT",)),
    FeatureDef("F_TRANSLUCENT", "Translucent", "Translucent", default=0,
               excludes=("F_ALPHA_TEST", "F_DO_NOT_CAST_SHADOWS")),
    FeatureDef("F_ADDITIVE_BLEND", "Additive Blend", "Translucent", default=0,
               requires=("F_TRANSLUCENT",),
               excludes=("F_ANISOTROPIC_GLOSS", "F_DETAIL_TEXTURE", "F_METALNESS_TEXTURE", "F_TRANSMISSIVE_BACKFACE_NDOTL")),
    FeatureDef("F_TINT_MASK", "Per-Instance Tint Mask", "Per-Instance Tint Mask", default=0),
    FeatureDef("F_ANISOTROPIC_GLOSS", "Anisotropic Gloss", "PBR", default=0,
               excludes=("F_ADDITIVE_BLEND", "F_DETAIL_TEXTURE", "F_CLOTH_SHADING", "F_DECAL_TEXTURE")),
    FeatureDef("F_SELF_ILLUM", "Self Illum", "PBR", default=0,
               excludes=("F_DETAIL_TEXTURE", "F_DECAL_TEXTURE")),
    FeatureDef("F_DETAIL_TEXTURE", "Detail Texture", "Detail Texture", default=0,
               range_max=4, options=("None", "Mod2X", "Overlay", "Normals", "Overlay and Normals"),
               excludes=("F_SELF_ILLUM", "F_ANISOTROPIC_GLOSS", "F_ADDITIVE_BLEND", "F_TRANSMISSIVE_BACKFACE_NDOTL")),
    FeatureDef("F_METALNESS_TEXTURE", "Metalness Texture", "PBR", default=0,
               excludes=("F_ADDITIVE_BLEND", "F_CLOTH_SHADING")),
    FeatureDef("F_SECONDARY_UV", "Secondary UV", "Secondary UV", default=0),
    FeatureDef("F_TEXTURE_ANIMATION", "Texture Animation", "Animation", default=0,
               excludes=("F_PRE_BAKED_VERTEX_ANIMATION", "F_DECAL_TEXTURE")),
    FeatureDef("F_TEXTURE_ANIMATION_MODE", "Texture Animation Mode", "Animation", default=0,
               range_max=2, options=("Sequential", "Random", "Scripted"),
               requires=("F_TEXTURE_ANIMATION",)),
    FeatureDef("F_PRE_BAKED_VERTEX_ANIMATION", "Pre-Baked Vertex Animation", "Animation", default=0,
               excludes=("F_TEXTURE_ANIMATION", "F_TRANSMISSIVE_BACKFACE_NDOTL", "F_DECAL_TEXTURE")),
    FeatureDef("F_TRANSMISSIVE_BACKFACE_NDOTL", "Transmissive Backface NdotL", "PBR", default=0,
               excludes=("F_DETAIL_TEXTURE", "F_PRE_BAKED_VERTEX_ANIMATION", "F_ADDITIVE_BLEND", "F_DECAL_TEXTURE")),
    FeatureDef("F_USE_ALBEDO_FOR_TRANSMISSIVE", "Use Albedo For Transmissive", "PBR", default=0,
               child_of=("F_TRANSMISSIVE_BACKFACE_NDOTL",)),
    FeatureDef("F_DISABLE_TRANSMISSIVE_SHADOWS", "Disable Transmissive Shadows", "PBR", default=0,
               child_of=("F_TRANSMISSIVE_BACKFACE_NDOTL",)),
    FeatureDef("F_CLOTH_SHADING", "Cloth Shading", "PBR", default=0,
               excludes=("F_ANISOTROPIC_GLOSS", "F_METALNESS_TEXTURE", "F_DECAL_TEXTURE")),
    FeatureDef("F_DECAL_TEXTURE", "Decal Texture", "Decal Texture", default=0,
               excludes=("F_ANISOTROPIC_GLOSS", "F_SELF_ILLUM", "F_TEXTURE_ANIMATION", "F_PRE_BAKED_VERTEX_ANIMATION", "F_TRANSMISSIVE_BACKFACE_NDOTL", "F_CLOTH_SHADING")),
    FeatureDef("F_DECAL_BLEND_MODE", "Decal Blend Mode", "Decal Blend Mode", default=0,
               child_of=("F_DECAL_TEXTURE",)),
    FeatureDef("F_PAINT_VERTEX_COLORS", "Paint Vertex Colors", "Vertex Color", default=0),
    FeatureDef("F_DEPTH_BIAS", "Depth Bias", "Z-Buffering", default=0,
               excludes=("F_DISABLE_Z_BUFFERING",)),
    FeatureDef("F_OCCLUSION_CULLING_BOUNDS_SCALE", "Occlusion Culling Bounds Scale", "Z-Buffering", default=0),
    FeatureDef("F_IGNORE_FACE_NORMALS_FOR_LIGHTING", "Ignore Face Normals For Lighting", "Lightmapping", default=0),
)

COMPLEX_SLOTS = ("color", "normal", "rough", "metal", "ao", "height", "opacity", "emissive", "tintmask", "detail", "decal")

COMPLEX_BLOCKS = (
    Block("2-Sided Rendering", (
        Param("F_RENDER_BACKFACES", "int", default=1),
    ), when=_BACKFACES),

    # The flag sits near the top, before Color — matches textureanimation.vmat.
    Block("Animation", (
        Param("F_TEXTURE_ANIMATION", "int", default=1),
    ), when=_ANIM),

    Block("Color", (
        Param("g_flModelTintAmount", KIND_SCALAR, default=1.0),
        Param("g_flTexCoordRotation", KIND_SCALAR, default=0.0),
        Param("g_nScaleTexCoordUByModelScaleAxis", KIND_INT, default=0),
        Param("g_nScaleTexCoordVByModelScaleAxis", KIND_INT, default=0),
        Param("g_vColorTint", KIND_COLOR, default=(1.0, 1.0, 1.0)),
        Param("g_vTexCoordCenter", KIND_VECTOR2, default=(0.5, 0.5)),
        Param("g_vTexCoordOffset", KIND_VECTOR2, default=(0.0, 0.0)),
        Param("g_vTexCoordScale", KIND_VECTOR2, default=(1.0, 1.0)),
        Param("g_vTexCoordScrollSpeed", KIND_VECTOR2, default=(0.0, 0.0)),
        Param("TextureColor", KIND_TEXTURE, default="materials/default/default_color.tga", slot="color"),
    )),

    Block("Fog", (
        Param("g_bFogEnabled", KIND_INT, default=1),
    )),

    Block("Lighting", (
        Param("TextureAmbientOcclusion", KIND_TEXTURE, default="materials/default/default_ao.tga", slot="ao"),
        Param("TextureMetalness", KIND_TEXTURE, default="materials/default/default_metal.tga", slot="metal"),
        Param("TextureNormal", KIND_TEXTURE, default="materials/default/default_normal.tga", slot="normal"),
        Param("TextureRoughness", KIND_TEXTURE, default="materials/default/default_rough.tga", slot="rough"),
    )),

    Block("Self Illum", (
        Param("g_flSelfIllumAlbedoFactor", KIND_SCALAR, default=1.0),
        Param("g_flSelfIllumBrightness", KIND_SCALAR, default=0.0),
        Param("g_flSelfIllumScale", KIND_SCALAR, default=1.0),
        Param("g_vSelfIllumScrollSpeed", KIND_VECTOR2, default=(0.0, 0.0)),
        Param("g_vSelfIllumTint", KIND_COLOR, default=(1.0, 1.0, 1.0)),
        Param("TextureSelfIllumMask", KIND_TEXTURE, default="", slot="emissive"),
    ), when=_SELF_ILLUM),

    Block("Detail Texture", (
        Param("g_bUseSecondaryUvForDetailTexture", KIND_INT, default=1),
        Param("g_flDetailTexCoordRotation", KIND_SCALAR, default=0.0),
        Param("g_vDetailTexCoordOffset", KIND_VECTOR2, default=(0.0, 0.0)),
        Param("g_vDetailTexCoordScale", KIND_VECTOR2, default=(1.0, 1.0)),
        Param("TextureDetail", KIND_TEXTURE, default="", slot="detail"),
    ), when=_DETAIL),

    Block("Texture Address Mode", (
        Param("g_nTextureAddressModeU", KIND_INT, default=0),
        Param("g_nTextureAddressModeV", KIND_INT, default=0),
    )),

    Block("Texture Animation", (
        Param("g_flAnimationFrame", KIND_SCALAR, default=0.0, defined=_ANIM),
        Param("g_flAnimationTimeOffset", KIND_SCALAR, default=0.0, defined=_ANIM),
        Param("g_flAnimationTimePerFrame", KIND_SCALAR, default=0.1, defined=_ANIM),
        Param("g_nNumAnimationCells", KIND_INT, default=1, defined=_ANIM),
        Param("g_vAnimationGrid", KIND_IVECTOR2, default=(1, 1), defined=_ANIM),
    ), when=_ANIM),

    Block("Translucent", (
        Param("F_ALPHA_TEST", "int", default=1, when=lambda c: c.flag("F_ALPHA_TEST")),
        Param("F_TRANSLUCENT", "int", default=1, when=lambda c: c.flag("F_TRANSLUCENT")),
        Param("g_flAlphaTestReference", KIND_SCALAR, default=0.5),
        Param("g_flAntiAliasedEdgeStrength", KIND_SCALAR, default=1.0),
        Param("TextureTranslucency", KIND_TEXTURE, default="", slot="opacity"),
    ), when=_ALPHA_OR_TRANS),
)

SCHEMA = ShaderSchema(
    shader="csgo_complex.vfx",
    verified=True,
    slots=COMPLEX_SLOTS,
    features=COMPLEX_FEATURES,
    blocks=COMPLEX_BLOCKS,
)
