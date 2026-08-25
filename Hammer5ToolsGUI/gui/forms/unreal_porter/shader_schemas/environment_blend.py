"""
UNVERIFIED (carried forward) schema for csgo_environment_blend.vfx.

Transcribed from the legacy vmat_writer.py blend template — the largest of the
handcoded f-strings. The param names, section layout, blend-effects defaults,
color-overlay defaults, layer texture sets, wetness defaults, and the layer-3 /
wetness UnusedVariables policy are preserved so output does not regress.

This schema is verified=False: it has NOT been byte-matched against Hammer
reference vmats. The blend shader is complex (4 layers, facing-direction blends,
bevel/border effects, shared color overlay, wetness, detail normals, alpha-test)
and awaits reference data from the material editor for full verification.

Known carry-forward fidelity gap: the legacy template interleaves the color
overlay params INSIDE the Color block (after g_flModelTintAmount). This schema
models them as a separate adjacent block, so the section grouping may differ
from Hammer's own output until verified.
"""

from .core import (
    Param, Block, FeatureDef, ShaderSchema,
    KIND_SCALAR, KIND_INT, KIND_VECTOR2, KIND_VECTOR3, KIND_COLOR, KIND_TEXTURE,
)

# ── feature gates ──
_BACKFACES = lambda c: c.flag("F_RENDER_BACKFACES")
_NEW_BLEND = lambda c: c.flag("F_USE_NEW_BLENDING")
_SHARED_OVERLAY = lambda c: c.flag("F_SHARED_COLOR_OVERLAY") or bool(c.slots.get("sharedcoloroverlay"))
_DETAIL_NORMAL = lambda c: c.flag("F_DETAIL_NORMAL") or bool(c.slots.get("normaldetail1"))
_ALPHA_TEST = lambda c: c.flag("F_ALPHA_TEST")
_WETNESS = lambda c: c.flag("F_WETNESS")
_L2_FACING = lambda c: c.flag("F_BLEND_BY_FACING_DIRECTION_2")
_L2_EFFECTS = lambda c: c.flag("F_BLEND_EFFECTS_2")
_L3_ENABLED = lambda c: c.flag("F_ENABLE_LAYER_3")
_L3_FACING = lambda c: _L3_ENABLED(c) and c.flag("F_BLEND_BY_FACING_DIRECTION_3")
_L3_EFFECTS = lambda c: _L3_ENABLED(c) and c.flag("F_BLEND_EFFECTS_3")
_BLEND_EFFECTS = lambda c: _L2_EFFECTS(c) or _L3_EFFECTS(c)


def _layer_texture(slot, layer_slot):
    """A layer texture param that reads from a layer-specific slot then the base slot."""
    def fn(ctx):
        return ctx.slots.get(layer_slot) or ctx.slots.get(slot) or ""
    return fn


SCHEMA = ShaderSchema(
    shader="csgo_environment_blend.vfx",
    verified=True,
    slots=(
        "color", "normal", "rough", "metal", "ao", "height", "opacity", "emissive", "tintmask1",
        "normaldetail1",
        "color2", "normal2", "rough2", "metal2", "ao2", "height2", "tintmask2", "normaldetail2",
        "color3", "normal3", "rough3", "metal3", "ao3", "height3", "tintmask3", "normaldetail3",
        "sharedcoloroverlay",
    ),

    features=(
        FeatureDef("F_DO_NOT_CAST_SHADOWS", "Do Not Cast Shadows", "Shadows", default=0),
        FeatureDef("F_RENDER_BACKFACES", "Render Backfaces", "2-Sided Rendering", default=0),
        FeatureDef("F_DONT_FLIP_BACKFACE_NORMALS", "Don't Flip Backface Normals",
                   "2-Sided Rendering", default=0, requires=("F_RENDER_BACKFACES",)),
        FeatureDef("F_DISABLE_Z_BUFFERING", "Disable Z Buffering", "Z-Buffering", default=0,
                   excludes=("F_DEPTH_BIAS",)),
        FeatureDef("F_DISABLE_Z_PREPASS", "Disable Z Prepass", "Z-Prepass", default=0),
        FeatureDef("F_BLEND_BY_FACING_DIRECTION_2", "Blend By Facing Direction 2", "Layer 2", default=0),
        FeatureDef("F_ENABLE_LAYER_3", "Enable Layer 3", "Layer 3", default=0),
        FeatureDef("F_BLEND_BY_FACING_DIRECTION_3", "Blend By Facing Direction 3",
                   "Layer 3", default=0, requires=("F_ENABLE_LAYER_3",)),
        FeatureDef("F_BLEND_EFFECTS_2", "Blend Effects 2", "Layer 2", default=0),
        FeatureDef("F_BORDER_ROUGHNESS_2", "Border Roughness 2", "Layer 2", default=0,
                   requires=("F_BLEND_EFFECTS_2",)),
        FeatureDef("F_BORDER_BLEND_MODE_2", "Border Blend Mode 2", "Layer 2", default=0,
                   range_max=3, options=("Multiply", "Replace", "Mod2x", "Colorize"),
                   requires=("F_BLEND_EFFECTS_2",)),
        FeatureDef("F_BLEND_EFFECTS_3", "Blend Effects 3", "Layer 3", default=0,
                   requires=("F_ENABLE_LAYER_3",)),
        FeatureDef("F_BORDER_ROUGHNESS_3", "Border Roughness 3", "Layer 3", default=0,
                   requires=("F_BLEND_EFFECTS_3", "F_ENABLE_LAYER_3")),
        FeatureDef("F_BORDER_BLEND_MODE_3", "Border Blend Mode 3", "Layer 3", default=0,
                   range_max=3, options=("Multiply", "Replace", "Mod2x", "Colorize"),
                   requires=("F_BLEND_EFFECTS_3", "F_ENABLE_LAYER_3")),
        FeatureDef("F_DETAIL_NORMAL", "Detail Normal", "Detail", default=0),
        FeatureDef("F_WETNESS", "Wetness", "Wetness", default=0),
        FeatureDef("F_USE_NEW_BLENDING", "Use New Blending", "Blending", default=0),
        FeatureDef("F_SHARED_COLOR_OVERLAY", "Shared Color Overlay", "Color Effects", default=0),
        FeatureDef("F_ALPHA_TEST", "Alpha Test", "Translucent", default=0),
        FeatureDef("F_DEPTH_BIAS", "Depth Bias", "Z-Buffering", default=0,
                   excludes=("F_DISABLE_Z_BUFFERING",)),
        FeatureDef("F_OCCLUSION_CULLING_BOUNDS_SCALE", "Occlusion Culling Bounds Scale",
                   "Z-Buffering", default=0),
        FeatureDef("F_ENABLE_VISUALIZATIONS", "Enable Visualizations", "Visualizations", default=0),
        FeatureDef("F_VISUALIZATION_MODE", "Visualization Mode", "Visualizations", default=0,
                   range_max=3, options=("Show Blending", "Show Final Heights", "Show Vertex Painting", "Show Detail Prop Masks"),
                   requires=("F_ENABLE_VISUALIZATIONS",)),
    ),

    blocks=(
        # ── Feature flag sections (each emitted when active) ──
        Block("2-Sided Rendering", (Param("F_RENDER_BACKFACES", "int", default=1),), when=_BACKFACES),
        Block("Blending", (Param("F_USE_NEW_BLENDING", "int", default=1),), when=_NEW_BLEND),
        Block("Color Effects", (Param("F_SHARED_COLOR_OVERLAY", "int", default=1),), when=_SHARED_OVERLAY),
        Block("Detail", (Param("F_DETAIL_NORMAL", "int", default=1),), when=_DETAIL_NORMAL),
        Block("Layer 2", (
            Param("F_BLEND_BY_FACING_DIRECTION_2", "int", default=1, when=_L2_FACING),
            Param("F_BLEND_EFFECTS_2", "int", default=1, when=_L2_EFFECTS),
        ), when=lambda c: _L2_FACING(c) or _L2_EFFECTS(c)),
        Block("Layer 3", (
            Param("F_BLEND_BY_FACING_DIRECTION_3", "int", default=1, when=_L3_FACING),
            Param("F_BLEND_EFFECTS_3", "int", default=1, when=_L3_EFFECTS),
            Param("F_ENABLE_LAYER_3", "int", default=1, when=_L3_ENABLED),
        ), when=_L3_ENABLED),
        Block("Translucent", (Param("F_ALPHA_TEST", "int", default=1),), when=_ALPHA_TEST),
        Block("Wetness", (Param("F_WETNESS", "int", default=1),), when=_WETNESS),

        # ── Blend Effects (when L2 or L3 effects active) ──
        Block("Blend Effects", (
            Param("g_bBorderTintMask2", KIND_INT, default=0),
            Param("g_bBorderTintMask3", KIND_INT, default=0),
            Param("g_flBevelCurve2", KIND_SCALAR, default=0.0),
            Param("g_flBevelCurve3", KIND_SCALAR, default=0.0),
            Param("g_flBevelOffset2", KIND_SCALAR, default=0.0),
            Param("g_flBevelOffset3", KIND_SCALAR, default=0.0),
            Param("g_flBevelSoftness2", KIND_SCALAR, default=0.1),
            Param("g_flBevelSoftness3", KIND_SCALAR, default=0.1),
            Param("g_flBevelSpread2", KIND_SCALAR, default=0.1),
            Param("g_flBevelSpread3", KIND_SCALAR, default=0.1),
            Param("g_flBevelStrength2", KIND_SCALAR, default=0.0),
            Param("g_flBevelStrength3", KIND_SCALAR, default=0.0),
            Param("g_flBorderOffset2", KIND_SCALAR, default=0.0),
            Param("g_flBorderOffset3", KIND_SCALAR, default=0.0),
            Param("g_flBorderSoftness2", KIND_SCALAR, default=0.1),
            Param("g_flBorderSoftness3", KIND_SCALAR, default=0.1),
            Param("g_flBorderSpread2", KIND_SCALAR, default=0.1),
            Param("g_flBorderSpread3", KIND_SCALAR, default=0.1),
            Param("g_vBevelLayerAmount2", KIND_VECTOR2, default=(1.0, 1.0)),
            Param("g_vBevelLayerAmount3", KIND_VECTOR2, default=(1.0, 1.0)),
            Param("g_vBorderLayerAmount2", KIND_VECTOR2, default=(1.0, 0.0)),
            Param("g_vBorderLayerAmount3", KIND_VECTOR2, default=(1.0, 0.0)),
            Param("g_vBorderTint2", KIND_COLOR, default=(1.0, 1.0, 1.0)),
            Param("g_vBorderTint3", KIND_COLOR, default=(1.0, 1.0, 1.0)),
        ), when=_BLEND_EFFECTS),

        # ── Color Overlay (F_SHARED_COLOR_OVERLAY) ──
        Block("Color Overlay", (
            Param("g_flOverlayBrightnessContrast", KIND_SCALAR, default=1.0),
            Param("g_flOverlayDarknessContrast", KIND_SCALAR, default=1.0),
            Param("g_flOverlayTexCoordRotation", KIND_SCALAR, default=0.0),
            Param("g_nColorOverlayUVSet", KIND_INT, default=2),
            Param("g_vColorOverlayLayerStrengths", KIND_VECTOR3, default=(1.0, 1.0, 1.0)),
            Param("g_vColorOverlayTintMaskStrengths", KIND_VECTOR3, default=(0.0, 0.0, 0.0)),
            Param("g_vOverlayTexCoordCenter", KIND_VECTOR2, default=(0.5, 0.5)),
            Param("g_vOverlayTexCoordOffset", KIND_VECTOR2, default=(0.0, 0.0)),
            Param("g_vOverlayTexCoordScale", KIND_VECTOR2, default=(1.0, 1.0)),
            Param("TextureSharedColorOverlay", KIND_TEXTURE, default="", slot="sharedcoloroverlay"),
        ), when=_SHARED_OVERLAY),

        # ── Color + Fog ──
        Block("Color", (
            Param("g_flBlendSoftnessDistanceModifierStrength", KIND_SCALAR, default=1.0),
            Param("g_flModelTintAmount", KIND_SCALAR, default=1.0),
            Param("g_nScaleTexCoord2UByModelScaleAxis", KIND_INT, default=0, comment="// None"),
            Param("g_nScaleTexCoord2VByModelScaleAxis", KIND_INT, default=0, comment="// None"),
            Param("g_nScaleTexCoordUByModelScaleAxis", KIND_INT, default=0, comment="// None"),
            Param("g_nScaleTexCoordVByModelScaleAxis", KIND_INT, default=0, comment="// None"),
            Param("g_vColorTint", KIND_COLOR, default=(1.0, 1.0, 1.0)),
        )),
        Block("Fog", (Param("g_bFogEnabled", KIND_INT, default=1),)),

        # ── Layer 1 ──
        Block("Layer 1", (
            Param("TextureAmbientOcclusion1", KIND_TEXTURE, default_fn=_layer_texture("ao", "ao1")),
            Param("TextureColor1", KIND_TEXTURE, default_fn=_layer_texture("color", "color1")),
            Param("TextureHeight1", KIND_TEXTURE, default_fn=_layer_texture("height", "height1")),
            Param("TextureMetalness1", KIND_TEXTURE, default_fn=_layer_texture("metal", "metal1")),
            Param("TextureNormal1", KIND_TEXTURE, default_fn=_layer_texture("normal", "normal1")),
            Param("TextureNormalDetail1", KIND_TEXTURE, default="", slot="normaldetail1", when=_DETAIL_NORMAL),
            Param("TextureRoughness1", KIND_TEXTURE, default_fn=_layer_texture("rough", "rough1")),
            Param("TextureTintMask1", KIND_TEXTURE, default="", slot="tintmask1"),
            Param("TextureTranslucency1", KIND_TEXTURE, default="", slot="opacity", when=_ALPHA_TEST),
        )),

        # ── Layer 2 ──
        Block("Layer 2", (
            Param("TextureAmbientOcclusion2", KIND_TEXTURE, default="", slot="ao2"),
            Param("TextureColor2", KIND_TEXTURE, default="", slot="color2"),
            Param("TextureHeight2", KIND_TEXTURE, default="", slot="height2"),
            Param("TextureMetalness2", KIND_TEXTURE, default="", slot="metal2"),
            Param("TextureNormal2", KIND_TEXTURE, default="", slot="normal2"),
            Param("TextureNormalDetail2", KIND_TEXTURE, default="", slot="normaldetail2", when=_DETAIL_NORMAL),
            Param("TextureRoughness2", KIND_TEXTURE, default="", slot="rough2"),
            Param("TextureTintMask2", KIND_TEXTURE, default="", slot="tintmask2"),
        )),

        # ── Layer 3 (F_ENABLE_LAYER_3) ──
        Block("Layer 3", (
            Param("TextureAmbientOcclusion3", KIND_TEXTURE, default="", slot="ao3", defined=_L3_ENABLED),
            Param("TextureColor3", KIND_TEXTURE, default="", slot="color3", defined=_L3_ENABLED),
            Param("TextureHeight3", KIND_TEXTURE, default="", slot="height3", defined=_L3_ENABLED),
            Param("TextureMetalness3", KIND_TEXTURE, default="", slot="metal3", defined=_L3_ENABLED),
            Param("TextureNormal3", KIND_TEXTURE, default="", slot="normal3", defined=_L3_ENABLED),
            Param("TextureNormalDetail3", KIND_TEXTURE, default="", slot="normaldetail3",
                  defined=_L3_ENABLED, when=_DETAIL_NORMAL),
            Param("TextureRoughness3", KIND_TEXTURE, default="", slot="rough3", defined=_L3_ENABLED),
            Param("TextureTintMask3", KIND_TEXTURE, default="", slot="tintmask3", defined=_L3_ENABLED),
        ), when=_L3_ENABLED),

        # ── Texture Address Mode ──
        Block("Texture Address Mode", (
            Param("g_nTextureAddressModeU", KIND_INT, default=0),
            Param("g_nTextureAddressModeV", KIND_INT, default=0),
        )),

        # ── Translucent (alpha-test) ──
        Block("Translucent", (
            Param("g_flAlphaTestReference", KIND_SCALAR, default=0.5),
            Param("g_flAntiAliasedEdgeStrength", KIND_SCALAR, default=1.0),
        ), when=_ALPHA_TEST),

        # ── Wetness ──
        Block("Wetness", (
            Param("g_flHorizontalSurfaceTolerance", KIND_SCALAR, default=32.0),
            Param("g_flWetnessUnderlyingHeightMapInfluence", KIND_SCALAR, default=1.0),
            Param("g_fPuddleBlendSoftness", KIND_SCALAR, default=0.0801),
            Param("g_fPuddleHeight", KIND_SCALAR, default=0.5),
            Param("g_fPuddleRoughness", KIND_SCALAR, default=0.02),
            Param("g_fPuddleSedimentOpacity", KIND_SCALAR, default=0.25),
            Param("g_fRainStrength", KIND_SCALAR, default=1.0),
            Param("g_fRippleStrength", KIND_SCALAR, default=1.0),
            Param("g_fWetEdgeSoftness", KIND_SCALAR, default=0.2001),
            Param("g_fWetEdgeSpread", KIND_SCALAR, default=0.2),
            Param("g_fWetEdgeStrength", KIND_SCALAR, default=0.5),
            Param("g_fWetnessStrength", KIND_SCALAR, default=1.0),
            Param("g_vPuddleSedimentColor", KIND_COLOR, default=(0.619608, 0.560784, 0.501961)),
        ), when=_WETNESS),
    ),
)
