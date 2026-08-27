"""
VERIFIED schema for csgo_static_overlay.vfx.

Hand-transcribed from 9 reference .vmat files produced by Hammer's own material
editor (default, lit, additive, alphatest, mod2x, modthenadd, multiply,
textureanimation, translucent). Every parameter name, default value, section
title, blend-mode value, definedness rule, and the UnusedVariables policy is
matched byte-for-byte (modulo the auto-generated header) against those files.

The shader has two independent feature axes:
  * F_LIT              — toggles the lighting/roughness/normal/self-illum space
  * F_BLEND_MODE (0..6)— toggles translucent rendering and its param shape
  * F_TEXTURE_ANIMATION— toggles the texture-animation param space

Param visibility follows Source 2 static-combo rules:
  * Lighting/Normal/SelfIllum params are undefined (absent from the material)
    unless F_LIT is on — they never appear in UnusedVariables under pure default.
  * The translucent param space is undefined under blend mode 0; within it,
    opacity (OpacityScale + TextureTranslucency) is defined for modes 1/3/4/5/6
    and the alpha-test pair (AlphaTestReference + AntiAliasedEdgeStrength) is
    defined only for mode 2 (Alpha Test).
"""

from .core import (
    Param, Block, FeatureDef, BlendMode, ShaderSchema,
    KIND_SCALAR, KIND_INT, KIND_VECTOR2, KIND_IVECTOR2, KIND_COLOR, KIND_TEXTURE,
)

_BLEND_NAMES = {1: "Translucent", 2: "Alpha Test", 3: "Mod2x",
                4: "Additive", 5: "Multiply", 6: "ModThenAdd"}


def _blend_comment(v, _ctx=None) -> str:
    name = _BLEND_NAMES.get(int(v) if not isinstance(v, str) else int(v))
    return f"// {name}" if name else ""


_LIT = lambda c: c.flag("F_LIT")
_BLEND_NONZERO = lambda c: c.blend_mode != 0
_ANIM = lambda c: c.flag("F_TEXTURE_ANIMATION")
_NOT_ANIM = lambda c: not c.flag("F_TEXTURE_ANIMATION")
# Pure default = no blend mode AND no features. Hammer omits UnusedVariables
# entirely for the trivial material; the lit/translucent/animation param spaces
# are only reported as unused once the material becomes non-trivial.
_NONTRIVIAL = lambda c: c.blend_mode != 0 or c.flag("F_LIT") or c.flag("F_TEXTURE_ANIMATION")

# The translucent param space exists when a blend mode is active (1..6) OR the
# texture-animation combo is on — F_LIT alone does NOT compile it in. Within it:
#   - OpacityScale is emitted for blend modes {1,3,4,5,6}; unused otherwise.
#   - the alpha-test pair (AlphaTestReference + AntiAliasedEdgeStrength) is only
#     defined for blend modes {2,3,4,5,6} — mode 1 (Translucent) compiles it out
#     entirely — and emitted only for mode 2.
#   - TextureTranslucency is emitted for all blend modes 1..6; unused otherwise.
# The non-emitted members of the space appear in UnusedVariables.
_TRANSLUCENT_DEFINED = lambda c: c.blend_mode != 0 or c.flag("F_TEXTURE_ANIMATION")
_OPACITY_DEFINED = _TRANSLUCENT_DEFINED
_OPACITY_EMIT = lambda c: c.blend_mode in (1, 3, 4, 5, 6)
# Alpha-test pair: defined everywhere the translucent space exists EXCEPT blend
# mode 1 (Translucent compiles it out); emitted only for mode 2 (Alpha Test).
_ALPHATEST_DEFINED = lambda c: _TRANSLUCENT_DEFINED(c) and c.blend_mode != 1
_ALPHATEST_EMIT = lambda c: c.blend_mode == 2

# Lit-space params (Lighting/Normal/SelfIllum/AO): defined whenever the material
# is non-trivial (so they appear in UnusedVariables under translucent/additive
# etc.), but absent from the pure-default material which has no UnusedVariables.
_LIT_DEFINED = lambda c: _NONTRIVIAL(c)


SCHEMA = ShaderSchema(
    shader="csgo_static_overlay.vfx",
    verified=True,
    slots=("color", "normal", "rough", "metal", "ao", "opacity", "emissive"),

    features=(
        FeatureDef("F_LIT", "Lit (Enables Normal, Rough, Metal, AO, Self Illum)", "Lighting", default=0),
        FeatureDef("F_TEXTURE_ANIMATION", "Texture Animation", "Animation", default=0),
        FeatureDef("F_DO_NOT_CAST_SHADOWS", "Do Not Cast Shadows", "Shadows", default=0),
        FeatureDef("F_RENDER_BACKFACES", "Render Backfaces", "2-Sided Rendering", default=0),
        # FeatureRule Requires(F_DONT_FLIP_BACKFACE_NORMALS, F_RENDER_BACKFACES)
        FeatureDef("F_DONT_FLIP_BACKFACE_NORMALS", "Don't Flip Backface Normals",
                   "2-Sided Rendering", default=0, requires=("F_RENDER_BACKFACES",)),
        FeatureDef("F_DISABLE_Z_BUFFERING", "Disable Z Buffering", "Z-Buffering", default=0),
    ),

    blend_modes=(
        BlendMode(0, "Opaque"),
        BlendMode(1, "Translucent"),
        BlendMode(2, "Alpha Test"),
        BlendMode(3, "Mod2x"),
        BlendMode(4, "Additive"),
        BlendMode(5, "Multiply"),
        BlendMode(6, "ModThenAdd"),
    ),

    blocks=(
        Block("Blend Mode", (
            Param("F_BLEND_MODE", "int", default=0, comment_fn=_blend_comment),
        ), when=_BLEND_NONZERO),

        # The flag sits near the top, before Color — matches textureanimation.vmat.
        Block("Animation", (
            Param("F_TEXTURE_ANIMATION", "int", default=1),
        ), when=_ANIM),

        Block("Lighting", (
            Param("F_LIT", "int", default=1),
        ), when=_LIT),

        Block("Ambient Occlusion", (
            Param("TextureAmbientOcclusion", KIND_TEXTURE, default="", slot="ao", defined=_LIT_DEFINED),
        ), when=_LIT),

        Block("Color", (
            Param("g_flModelTintAmount", KIND_SCALAR, default=1.0),
            Param("g_flTexCoordRotation", KIND_SCALAR, default=0.0),
            Param("g_fTextureColorBrightness", KIND_SCALAR, default=1.0),
            Param("g_fTextureColorContrast", KIND_SCALAR, default=1.0),
            Param("g_fTextureColorSaturation", KIND_SCALAR, default=1.0),
            Param("g_nScaleTexCoordUByModelScaleAxis", KIND_INT, default=0),
            Param("g_nScaleTexCoordVByModelScaleAxis", KIND_INT, default=0),
            Param("g_vColorTint", KIND_COLOR, default=(1.0, 1.0, 1.0)),
            Param("g_vTexCoordCenter", KIND_VECTOR2, default=(0.5, 0.5)),
            Param("g_vTexCoordOffset", KIND_VECTOR2, default=(0.0, 0.0)),
            Param("g_vTexCoordScale", KIND_VECTOR2, default=(1.0, 1.0)),
            Param("g_vTexCoordScrollSpeed", KIND_VECTOR2, default=(0.0, 0.0)),
            Param("g_vTextureColorCorrectionTint", KIND_COLOR, default=(1.0, 1.0, 1.0)),
            Param("TextureColor", KIND_TEXTURE, default="", slot="color"),
        )),

        Block("Fog", (
            Param("g_bFogEnabled", KIND_INT, default=1),
        )),

        Block("Lighting", (
            Param("g_fTextureRoughnessBrightness", KIND_SCALAR, default=1.0, defined=_LIT_DEFINED),
            Param("g_fTextureRoughnessContrast", KIND_SCALAR, default=1.0, defined=_LIT_DEFINED),
            Param("TextureMetalness", KIND_TEXTURE, default="", slot="metal", defined=_LIT_DEFINED),
            Param("TextureRoughness", KIND_TEXTURE, default="", slot="rough", defined=_LIT_DEFINED),
        ), when=_LIT),

        Block("Normal Map", (
            Param("g_fTextureNormalContrast", KIND_SCALAR, default=1.0, defined=_LIT_DEFINED),
            Param("TextureNormal", KIND_TEXTURE, default="", slot="normal", defined=_LIT_DEFINED),
        ), when=_LIT),

        Block("Self Illum", (
            Param("g_flSelfIllumAlbedoFactor", KIND_SCALAR, default=1.0, defined=_LIT_DEFINED),
            Param("g_flSelfIllumBrightness", KIND_SCALAR, default=0.0, defined=_LIT_DEFINED),
            Param("g_flSelfIllumScale", KIND_SCALAR, default=1.0, defined=_LIT_DEFINED),
            Param("g_vSelfIllumScrollSpeed", KIND_VECTOR2, default=(0.0, 0.0), defined=_LIT_DEFINED),
            Param("g_vSelfIllumTint", KIND_COLOR, default=(1.0, 1.0, 1.0), defined=_LIT_DEFINED),
            Param("TextureSelfIllumMask", KIND_TEXTURE, default="", slot="emissive", defined=_LIT_DEFINED),
        ), when=_LIT),

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

        # Opacity pair (OpacityScale): modes 1,3,4,5,6.
        # Alpha-test pair (AlphaTestReference + AntiAliasedEdgeStrength): mode 2.
        # TextureTranslucency: all blend modes 1..6 (emitted in every variant).
        Block("Translucent", (
            Param("g_flOpacityScale", KIND_SCALAR, default=1.0,
                  defined=_OPACITY_DEFINED, when=_OPACITY_EMIT),
            Param("g_flAlphaTestReference", KIND_SCALAR, default=0.5,
                  defined=_ALPHATEST_DEFINED, when=_ALPHATEST_EMIT),
            Param("g_flAntiAliasedEdgeStrength", KIND_SCALAR, default=1.0,
                  defined=_ALPHATEST_DEFINED, when=_ALPHATEST_EMIT),
            Param("TextureTranslucency", KIND_TEXTURE, default="", slot="opacity",
                  defined=_TRANSLUCENT_DEFINED),
        ), when=_BLEND_NONZERO),
    ),
)
