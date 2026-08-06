"""
VERIFIED schema for csgo_effects.vfx.

Hand-transcribed from the Source 2 Viewer (VRF) shader reconstruction, which
exposes the ground-truth authoring parameter names, Default(...) values, UiGroup
section ordering, and FeatureRule dependencies directly from the compiled shader.
The VRF dump is the authoritative source here (rather than a Hammer-authored
.vmat) because it reveals the declared defaults — notably:

  * g_flFresnelExponent Default(0.001)   — the legacy template hardcoded 2.700
  * g_flFadeMin / g_flFresnelMin have NO Default — the legacy template invented 0.000

Section layout follows the shader's UiGroup order (Color, Mask 1/2/3, Translucent,
Fog, Distance Fade, Depth Feather, Fresnel, Texture Address Mode), with the
feature-flag sections emitted first when active — matching Hammer's own output.

The feature flags and the FeatureRule Requires(F_DONT_FLIP_BACKFACE_NORMALS,
F_RENDER_BACKFACES) come straight from the FEATURES block of the shader.
"""

from .core import (
    Param, Block, FeatureDef, ShaderSchema,
    KIND_SCALAR, KIND_INT, KIND_VECTOR2, KIND_COLOR, KIND_TEXTURE,
)


# ── gates ──
_BACKFACES = lambda c: c.flag("F_RENDER_BACKFACES")
_DONT_FLIP = lambda c: c.flag("F_DONT_FLIP_BACKFACE_NORMALS")
_DEPTH_FEATHER = lambda c: c.flag("F_DEPTH_FEATHER")
_ADDITIVE = lambda c: c.flag("F_ADDITIVE_BLEND")
_TINT_MASK = lambda c: c.flag("F_TINT_MASK")
_DISABLE_Z = lambda c: c.flag("F_DISABLE_Z_BUFFERING")


def _flag_block(title, flag_name):
    """A single-flag section emitted as '//---- {title} ----\\n\\t{flag} 1'."""
    return Block(title, (
        Param(flag_name, "int", default=1),
    ), when=lambda c, fn=flag_name: c.flag(fn))


SCHEMA = ShaderSchema(
    shader="csgo_effects.vfx",
    verified=True,
    slots=("color", "opacity", "tintmask", "mask1", "mask2", "mask3"),

    features=(
        FeatureDef("F_DO_NOT_CAST_SHADOWS", "Do Not Cast Shadows", "Shadows", default=0),
        FeatureDef("F_RENDER_BACKFACES", "Render Backfaces", "2-Sided Rendering", default=0),
        # FeatureRule Requires(F_DONT_FLIP_BACKFACE_NORMALS, F_RENDER_BACKFACES)
        FeatureDef("F_DONT_FLIP_BACKFACE_NORMALS", "Don't Flip Backface Normals",
                   "2-Sided Rendering", default=0, requires=("F_RENDER_BACKFACES",)),
        FeatureDef("F_DISABLE_Z_BUFFERING", "Disable Z Buffering", "Z-Buffering", default=0),
        FeatureDef("F_DISABLE_Z_PREPASS", "Disable Z Prepass", "Z-Prepass", default=0),
        FeatureDef("F_DEPTH_FEATHER", "Depth Feather", "Depth Feather", default=0),
        FeatureDef("F_ADDITIVE_BLEND", "Additive Blend", "Translucent", default=0),
        FeatureDef("F_TINT_MASK", "Per-Instance Tint Mask", "Per-Instance Tint Mask", default=0),
    ),

    blocks=(
        # ── Active feature-flag sections (each emitted only when on) ──
        Block("2-Sided Rendering", (
            Param("F_RENDER_BACKFACES", "int", default=1),
        ), when=_BACKFACES),
        Block("Depth Feather", (
            Param("F_DEPTH_FEATHER", "int", default=1),
        ), when=_DEPTH_FEATHER),
        Block("Per-Instance Tint Mask", (
            Param("F_TINT_MASK", "int", default=1),
        ), when=_TINT_MASK),
        Block("Translucent", (
            Param("F_ADDITIVE_BLEND", "int", default=1),
        ), when=_ADDITIVE),
        Block("Z-Buffering", (
            Param("F_DISABLE_Z_BUFFERING", "int", default=1),
        ), when=_DISABLE_Z),

        # ── Color (always) ──
        Block("Color", (
            Param("g_flColorBoost", KIND_SCALAR, default=1.0),
            Param("g_vColorTint", KIND_COLOR, default=(1.0, 1.0, 1.0)),
            Param("g_vTexCoordScrollSpeed", KIND_VECTOR2, default=(0.0, 0.0)),
            Param("TextureColor", KIND_TEXTURE, default="", slot="color"),
            Param("TextureTintMask", KIND_TEXTURE, default="", slot="tintmask",
                  when=_TINT_MASK),
        )),

        # ── Depth Feather params (F_DEPTH_FEATHER only) ──
        Block("Depth Feather", (
            Param("g_flFeatherDistance", KIND_SCALAR, default=0.0, defined=_DEPTH_FEATHER),
            Param("g_flFeatherFalloff", KIND_SCALAR, default=1.0, defined=_DEPTH_FEATHER),
        ), when=_DEPTH_FEATHER),

        # ── Distance Fade (always) ──
        Block("Distance Fade", (
            Param("g_flFadeDistance", KIND_SCALAR, default=1.0),
            Param("g_flFadeFalloff", KIND_SCALAR, default=1.0),
            Param("g_flFadeMax", KIND_SCALAR, default=1.0),
            Param("g_flFadeMin", KIND_SCALAR, default=0.0),
        )),

        # ── Fog (always) ──
        Block("Fog", (
            Param("g_bFogEnabled", KIND_INT, default=1),
        )),

        # ── Fresnel (always) ──
        Block("Fresnel", (
            Param("g_flFresnelExponent", KIND_SCALAR, default=0.001),
            Param("g_flFresnelFalloff", KIND_SCALAR, default=1.0),
            Param("g_flFresnelMax", KIND_SCALAR, default=1.0),
            Param("g_flFresnelMin", KIND_SCALAR, default=0.0),
        )),

        # ── Mask 1 (always) ──
        Block("Mask 1", (
            Param("g_vMask1PanSpeed", KIND_VECTOR2, default=(0.0, 0.0)),
            Param("g_vMask1Scale", KIND_VECTOR2, default=(1.0, 1.0)),
            Param("TextureMask1", KIND_TEXTURE, default="", slot="mask1"),
        )),

        # ── Mask 2 (always) ──
        Block("Mask 2", (
            Param("g_vMask2PanSpeed", KIND_VECTOR2, default=(0.0, 0.0)),
            Param("g_vMask2Scale", KIND_VECTOR2, default=(1.0, 1.0)),
            Param("TextureMask2", KIND_TEXTURE, default="", slot="mask2"),
        )),

        # ── Mask 3 (always) ──
        Block("Mask 3", (
            Param("g_vMask3PanSpeed", KIND_VECTOR2, default=(0.0, 0.0)),
            Param("g_vMask3Scale", KIND_VECTOR2, default=(1.0, 1.0)),
            Param("TextureMask3", KIND_TEXTURE, default="", slot="mask3"),
        )),

        # ── Texture Address Mode (always) ──
        Block("Texture Address Mode", (
            Param("g_nTextureAddressModeU", KIND_INT, default=0),
            Param("g_nTextureAddressModeV", KIND_INT, default=0),
        )),

        # ── Translucent params (always) ──
        Block("Translucent", (
            Param("g_flOpacityScale", KIND_SCALAR, default=1.0),
            Param("TextureTranslucency", KIND_TEXTURE, default="", slot="opacity"),
        )),
    ),
)
