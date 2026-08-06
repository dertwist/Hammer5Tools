"""
CS2 Shader Schema definitions, metadata, and dependency rules.

Centralizes shader names, valid texture slots, scalar/vector/switch parameter
targets, feature flag dependency constraints, and .vmat default configurations.
"""

from typing import List, Tuple, Dict, Any

SHADERS = [
    "csgo_environment.vfx",
    "csgo_environment_blend.vfx",
    "csgo_effects.vfx",
    "csgo_static_overlay.vfx",
    "csgo_foliage.vfx",
    "csgo_glass.vfx",
    "csgo_character.vfx",
    "complex.vfx",
]

# Shader -> list of valid texture slots
SHADER_SLOTS = {
    "csgo_environment.vfx": [
        "color", "normal", "rough", "metal", "ao", "height", "opacity", "emissive"
    ],
    "csgo_effects.vfx": [
        "color", "opacity", "tintmask", "mask1", "mask2", "mask3"
    ],
    "csgo_glass.vfx": [
        "color", "normal", "rough", "metal", "ao", "opacity", "emissive"
    ],
    "csgo_foliage.vfx": [
        "color", "normal", "rough", "metal", "ao", "opacity", "emissive"
    ],
    "csgo_character.vfx": [
        "color", "normal", "rough", "metal", "ao", "opacity", "emissive"
    ],
    "csgo_static_overlay.vfx": [
        "color", "normal", "rough", "metal", "opacity"
    ],
    "csgo_environment_blend.vfx": [
        "color", "normal", "rough", "metal", "ao", "height", "opacity", "emissive", "tintmask1", "normaldetail1",
        "color2", "normal2", "rough2", "metal2", "ao2", "height2", "tintmask2", "normaldetail2",
        "color3", "normal3", "rough3", "metal3", "ao3", "height3", "tintmask3", "normaldetail3",
        "color4", "normal4", "rough4", "metal4", "ao4", "height4",
        "sharedcoloroverlay",
    ],
    "complex.vfx": [
        "color", "normal", "rough", "metal", "ao", "opacity", "emissive"
    ],
}

# Feature flag prerequisite rules for Source 2 shaders
FEATURE_DEPENDENCIES = {
    "csgo_environment_blend.vfx": {
        "F_DONT_FLIP_BACKFACE_NORMALS": ["F_RENDER_BACKFACES"],
        "F_BLEND_BY_FACING_DIRECTION_3": ["F_ENABLE_LAYER_3"],
        "F_BLEND_EFFECTS_3": ["F_ENABLE_LAYER_3"],
        "F_BORDER_ROUGHNESS_2": ["F_BLEND_EFFECTS_2"],
        "F_BORDER_BLEND_MODE_2": ["F_BLEND_EFFECTS_2"],
        "F_BORDER_ROUGHNESS_3": ["F_BLEND_EFFECTS_3", "F_ENABLE_LAYER_3"],
        "F_BORDER_BLEND_MODE_3": ["F_BLEND_EFFECTS_3", "F_ENABLE_LAYER_3"],
        "F_VISUALIZATION_MODE": ["F_ENABLE_VISUALIZATIONS"],
    },
    "csgo_effects.vfx": {
        "F_DONT_FLIP_BACKFACE_NORMALS": ["F_RENDER_BACKFACES"],
    },
}

SCALAR_TARGETS = [
    ("(skip)", ""),
    ("Roughness scale (Layer 1)", "g_flRoughnessScale"),
    ("Metalness scale (Layer 1)", "g_flMetalnessScale"),
    ("Model tint amount", "g_flModelTintAmount"),
    ("Blend softness distance modifier strength", "g_flBlendSoftnessDistanceModifierStrength"),
    ("HeightMap scale (Layer 1)", "g_flHeightMapScale1"),
    ("HeightMap zero point (Layer 1)", "g_flHeightMapZeroPoint1"),
    ("HeightMap scale (Layer 2)", "g_flHeightMapScale2"),
    ("HeightMap zero point (Layer 2)", "g_flHeightMapZeroPoint2"),
    ("HeightMap scale (Layer 3)", "g_flHeightMapScale3"),
    ("HeightMap zero point (Layer 3)", "g_flHeightMapZeroPoint3"),
    ("Blend softness (Layer 2)", "g_flBlendSoftness2"),
    ("Blend softness (Layer 3)", "g_flBlendSoftness3"),
    ("Color replace (Layer 2)", "g_flColorReplace2"),
    ("Color replace (Layer 3)", "g_flColorReplace3"),
    ("Color overlay (Layer 2)", "g_flColorOverlay2"),
    ("Color overlay (Layer 3)", "g_flColorOverlay3"),
    ("Normal replace (Layer 2)", "g_flNormalReplace2"),
    ("Normal replace (Layer 3)", "g_flNormalReplace3"),
    ("Normal combine (Layer 2)", "g_flNormalCombine2"),
    ("Normal combine (Layer 3)", "g_flNormalCombine3"),
    ("Roughness replace (Layer 2)", "g_flRoughnessReplace2"),
    ("Roughness replace (Layer 3)", "g_flRoughnessReplace3"),
    ("Roughness combine (Layer 2)", "g_flRoughnessCombine2"),
    ("Roughness combine (Layer 3)", "g_flRoughnessCombine3"),
    ("Metalness replace (Layer 2)", "g_flMetalnessReplace2"),
    ("Metalness replace (Layer 3)", "g_flMetalnessReplace3"),
    ("Metalness combine (Layer 2)", "g_flMetalnessCombine2"),
    ("Metalness combine (Layer 3)", "g_flMetalnessCombine3"),
    ("AO replace (Layer 2)", "g_flAOReplace2"),
    ("AO replace (Layer 3)", "g_flAOReplace3"),
    ("AO combine (Layer 2)", "g_flAOCombine2"),
    ("AO combine (Layer 3)", "g_flAOCombine3"),
    ("Mask with height (Layer 2)", "g_flMaskWithHeight2"),
    ("Mask with height (Layer 3)", "g_flMaskWithHeight3"),
    ("Underlying heightmap influence (Layer 2)", "g_flUnderlyingHeightMapInfluence2"),
    ("Underlying heightmap influence (Layer 3)", "g_flUnderlyingHeightMapInfluence3"),
    ("Tint mask brightness (Layer 1)", "g_fTintMaskBrightness1"),
    ("Tint mask contrast (Layer 1)", "g_fTintMaskContrast1"),
    ("Tint mask brightness (Layer 2)", "g_fTintMaskBrightness2"),
    ("Tint mask contrast (Layer 2)", "g_fTintMaskContrast2"),
    ("Tint mask brightness (Layer 3)", "g_fTintMaskBrightness3"),
    ("Tint mask contrast (Layer 3)", "g_fTintMaskContrast3"),
    ("Border spread (Layer 2)", "g_flBorderSpread2"),
    ("Border spread (Layer 3)", "g_flBorderSpread3"),
    ("Border softness (Layer 2)", "g_flBorderSoftness2"),
    ("Border softness (Layer 3)", "g_flBorderSoftness3"),
    ("Border offset (Layer 2)", "g_flBorderOffset2"),
    ("Border offset (Layer 3)", "g_flBorderOffset3"),
    ("Border roughness (Layer 2)", "g_fBorderRoughness2"),
    ("Border roughness (Layer 3)", "g_fBorderRoughness3"),
    ("Bevel strength (Layer 2)", "g_flBevelStrength2"),
    ("Bevel strength (Layer 3)", "g_flBevelStrength3"),
    ("Bevel softness (Layer 2)", "g_flBevelSoftness2"),
    ("Bevel softness (Layer 3)", "g_flBevelSoftness3"),
    ("Bevel curve (Layer 2)", "g_flBevelCurve2"),
    ("Bevel curve (Layer 3)", "g_flBevelCurve3"),
    ("Bevel spread (Layer 2)", "g_flBevelSpread2"),
    ("Bevel spread (Layer 3)", "g_flBevelSpread3"),
    ("Bevel offset (Layer 2)", "g_flBevelOffset2"),
    ("Bevel offset (Layer 3)", "g_flBevelOffset3"),
    ("Overlay brightness contrast", "g_flOverlayBrightnessContrast"),
    ("Overlay darkness contrast", "g_flOverlayDarknessContrast"),
    ("Overlay texcoord rotation", "g_flOverlayTexCoordRotation"),
    ("Texture brightness (Layer 1)", "g_fTextureColorBrightness1"),
    ("Texture contrast (Layer 1)", "g_fTextureColorContrast1"),
    ("Texture saturation (Layer 1)", "g_fTextureColorSaturation1"),
    ("Texture brightness (Layer 2)", "g_fTextureColorBrightness2"),
    ("Texture contrast (Layer 2)", "g_fTextureColorContrast2"),
    ("Texture saturation (Layer 2)", "g_fTextureColorSaturation2"),
    ("Texture brightness (Layer 3)", "g_fTextureColorBrightness3"),
    ("Texture contrast (Layer 3)", "g_fTextureColorContrast3"),
    ("Texture saturation (Layer 3)", "g_fTextureColorSaturation3"),
    ("Texture roughness brightness (Layer 2)", "g_fTextureRoughnessBrightness2"),
    ("Texture roughness contrast (Layer 2)", "g_fTextureRoughnessContrast2"),
    ("Texture roughness brightness (Layer 3)", "g_fTextureRoughnessBrightness3"),
    ("Texture roughness contrast (Layer 3)", "g_fTextureRoughnessContrast3"),
    ("Alpha test reference", "g_flAlphaTestReference"),
    ("Texcoord rotation (Layer 1)", "g_flTexCoordRotation1"),
    ("Texcoord rotation (Layer 2)", "g_flTexCoordRotation2"),
    ("Wetness darkening (Layer 1)", "g_flWetnessDarkeningStrength1"),
    ("Horizontal surface tolerance (Wetness)", "g_flHorizontalSurfaceTolerance"),
    ("Wetness underlying heightmap influence (Wetness)", "g_flWetnessUnderlyingHeightMapInfluence"),
    ("Puddle strength (Wetness)", "g_fPuddleStrength"),
    ("Puddle height (Wetness)", "g_fPuddleHeight"),
    ("Puddle sediment height (Wetness)", "g_fPuddleSedimentHeight"),
    ("Puddle sediment opacity (Wetness)", "g_fPuddleSedimentOpacity"),
    ("Puddle roughness (Wetness)", "g_fPuddleRoughness"),
    ("Puddle blend softness (Wetness)", "g_fPuddleBlendSoftness"),
    ("Wet edge strength (Wetness)", "g_fWetEdgeStrength"),
    ("Wet edge spread (Wetness)", "g_fWetEdgeSpread"),
    ("Wet edge softness (Wetness)", "g_fWetEdgeSoftness"),
    ("Wetness strength (Wetness)", "g_fWetnessStrength"),
    ("Rain strength (Wetness)", "g_fRainStrength"),
    ("Ripple strength (Wetness)", "g_fRippleStrength"),
    ("Color boost (Effects)", "g_flColorBoost"),
    ("Feather distance (Effects)", "g_flFeatherDistance"),
    ("Feather falloff (Effects)", "g_flFeatherFalloff"),
    ("Fade distance (Effects)", "g_flFadeDistance"),
    ("Fade falloff (Effects)", "g_flFadeFalloff"),
    ("Fade max (Effects)", "g_flFadeMax"),
    ("Fade min (Effects)", "g_flFadeMin"),
    ("Fresnel exponent (Effects)", "g_flFresnelExponent"),
    ("Fresnel falloff (Effects)", "g_flFresnelFalloff"),
    ("Fresnel max (Effects)", "g_flFresnelMax"),
    ("Fresnel min (Effects)", "g_flFresnelMin"),
    ("Opacity scale (Effects)", "g_flOpacityScale"),
]

VECTOR_TARGETS = [
    ("(skip)", ""),
    ("Color tint / Model tint (g_vColorTint)", "g_vColorTint"),
    ("Texture color tint (Layer 1)", "g_vTextureColorTint1"),
    ("Texture color tint (Layer 2)", "g_vTextureColorTint2"),
    ("Texture color tint (Layer 3)", "g_vTextureColorTint3"),
    ("Facing direction (Layer 2)", "g_vFacingDirection2"),
    ("Facing direction (Layer 3)", "g_vFacingDirection3"),
    ("Border tint (Layer 2)", "g_vBorderTint2"),
    ("Border tint (Layer 3)", "g_vBorderTint3"),
    ("Bevel layer amount (Layer 2)", "g_vBevelLayerAmount2"),
    ("Bevel layer amount (Layer 3)", "g_vBevelLayerAmount3"),
    ("Border layer amount (Layer 2)", "g_vBorderLayerAmount2"),
    ("Border layer amount (Layer 3)", "g_vBorderLayerAmount3"),
    ("Color overlay layer strengths", "g_vColorOverlayLayerStrengths"),
    ("Color overlay tint mask strengths", "g_vColorOverlayTintMaskStrengths"),
    ("Overlay texcoord center", "g_vOverlayTexCoordCenter"),
    ("Overlay texcoord offset", "g_vOverlayTexCoordOffset"),
    ("Overlay texcoord scale", "g_vOverlayTexCoordScale"),
    ("Puddle sediment color (Wetness)", "g_vPuddleSedimentColor"),
    ("Texcoord scale (Layer 1)", "g_vTexCoordScale1"),
    ("Texcoord scale (Layer 2)", "g_vTexCoordScale2"),
    ("Texcoord scale (Layer 3)", "g_vTexCoordScale3"),
    ("Texcoord offset (Layer 1)", "g_vTexCoordOffset1"),
    ("Texcoord offset (Layer 2)", "g_vTexCoordOffset2"),
    ("Texcoord center (Layer 1)", "g_vTexCoordCenter1"),
    ("AO levels (Layer 1)", "g_vAmbientOcclusionLevels1"),
    ("AO levels (Layer 2)", "g_vAmbientOcclusionLevels2"),
    ("AO levels (Layer 3)", "g_vAmbientOcclusionLevels3"),
    ("Texcoord scroll speed (Effects)", "g_vTexCoordScrollSpeed"),
    ("Mask 1 pan speed (Effects)", "g_vMask1PanSpeed"),
    ("Mask 1 scale (Effects)", "g_vMask1Scale"),
    ("Mask 2 pan speed (Effects)", "g_vMask2PanSpeed"),
    ("Mask 2 scale (Effects)", "g_vMask2Scale"),
    ("Mask 3 pan speed (Effects)", "g_vMask3PanSpeed"),
    ("Mask 3 scale (Effects)", "g_vMask3Scale"),
]

SWITCH_TARGETS = [
    ("(skip)", ""),
    ("Alpha test", "F_ALPHA_TEST"),
    ("Render backfaces", "F_RENDER_BACKFACES"),
    ("Do not cast shadows", "F_DO_NOT_CAST_SHADOWS"),
    ("Don't flip backface normals", "F_DONT_FLIP_BACKFACE_NORMALS"),
    ("Disable Z-buffering", "F_DISABLE_Z_BUFFERING"),
    ("Disable Z-prepass", "F_DISABLE_Z_PREPASS"),
    ("Blend by facing direction (Layer 2)", "F_BLEND_BY_FACING_DIRECTION_2"),
    ("Enable Layer 3", "F_ENABLE_LAYER_3"),
    ("Blend by facing direction (Layer 3)", "F_BLEND_BY_FACING_DIRECTION_3"),
    ("Enable Blend Effects (Layer 2)", "F_BLEND_EFFECTS_2"),
    ("Enable Blend Effects (Layer 3)", "F_BLEND_EFFECTS_3"),
    ("Border roughness (Layer 2)", "F_BORDER_ROUGHNESS_2"),
    ("Border roughness (Layer 3)", "F_BORDER_ROUGHNESS_3"),
    ("Detail normal", "F_DETAIL_NORMAL"),
    ("Wetness", "F_WETNESS"),
    ("Use new blending", "F_USE_NEW_BLENDING"),
    ("Shared color overlay", "F_SHARED_COLOR_OVERLAY"),
    ("Depth bias", "F_DEPTH_BIAS"),
    ("Occlusion culling bounds scale", "F_OCCLUSION_CULLING_BOUNDS_SCALE"),
    ("Enable visualizations", "F_ENABLE_VISUALIZATIONS"),
    ("Fog enabled", "g_bFogEnabled"),
    ("Model tint (Layer 1)", "g_bModelTint1"),
    ("Model tint (Layer 2)", "g_bModelTint2"),
    ("Model tint (Layer 3)", "g_bModelTint3"),
    ("Border tint mask (Layer 2)", "g_bBorderTintMask2"),
    ("Border tint mask (Layer 3)", "g_bBorderTintMask3"),
    ("Snow layer (Layer 1)", "g_bSnowLayer1"),
    ("Snow layer (Layer 2)", "g_bSnowLayer2"),
    ("Snow layer (Layer 3)", "g_bSnowLayer3"),
    ("Depth feather (Effects)", "F_DEPTH_FEATHER"),
    ("Tint mask (Effects)", "F_TINT_MASK"),
    ("Additive blend (Effects)", "F_ADDITIVE_BLEND"),
    ("Disable Z-buffering (Effects)", "F_DISABLE_Z_BUFFERING"),
    ("Lit (Static Overlay)", "F_LIT"),
]


def get_slots_for_shader(shader: str = None, feature_flags: dict = None) -> List[str]:
    """Return the list of valid vmat texture slots for the specified CS2 shader and active feature flags."""
    if not shader:
        return [
            "color", "normal", "rough", "metal", "ao", "height", "opacity", "emissive",
            "color2", "normal2", "rough2", "metal2", "ao2", "height2",
            "color3", "normal3", "rough3", "metal3", "ao3", "height3",
            "color4", "normal4", "rough4", "metal4", "ao4", "height4",
        ]
    shader_low = str(shader).lower().strip()
    if "blend" in shader_low:
        return list(SHADER_SLOTS["csgo_environment_blend.vfx"])
    if "effects" in shader_low:
        return list(SHADER_SLOTS["csgo_effects.vfx"])
    if "overlay" in shader_low or "decal" in shader_low:
        has_lit = bool(feature_flags and str(feature_flags.get("F_LIT", "0")) in ("1", "True", "true"))
        if has_lit:
            return ["color", "normal", "rough", "metal", "ao", "opacity", "emissive"]
        return ["color", "opacity"]
    if "glass" in shader_low:
        return list(SHADER_SLOTS["csgo_glass.vfx"])
    if shader_low in SHADER_SLOTS:
        return list(SHADER_SLOTS[shader_low])
    return list(SHADER_SLOTS["csgo_environment.vfx"])


def get_channel_slots_for_shader(shader: str = None, feature_flags: dict = None) -> List[str]:
    """Return single-channel slots suitable for channel splitting for the specified CS2 shader."""
    slots = get_slots_for_shader(shader, feature_flags=feature_flags)
    return [s for s in slots if not s.startswith("color") and not s.startswith("normal") and s != "emissive"]


def validate_feature_flags(shader: str, active_flags: Dict[str, Any]) -> Dict[str, Any]:
    """Enforce feature flag dependency rules (e.g. auto-enabling prerequisites or stripping invalid flags)."""
    if not shader or not active_flags:
        return active_flags or {}
    shader_low = str(shader).lower().strip()
    key_map = {
        "csgo_environment_blend.vfx": "csgo_environment_blend.vfx"
    }
    rules = FEATURE_DEPENDENCIES.get(key_map.get(shader_low, shader_low))
    if not rules:
        return active_flags

    validated = dict(active_flags)
    # Automatically enforce prerequisite dependencies
    for flag, val in list(validated.items()):
        if str(val) in ("1", "True", "true", "True"):
            prereqs = rules.get(flag, [])
            for req in prereqs:
                if str(validated.get(req, "0")) in ("0", "False", "false", "False"):
                    # Auto-enable prerequisite flag
                    validated[req] = "1"

    # Mutual exclusion check: F_DISABLE_Z_BUFFERING vs F_DEPTH_BIAS
    if str(validated.get("F_DISABLE_Z_BUFFERING", "0")) in ("1", "True", "true"):
        validated["F_DEPTH_BIAS"] = "0"

    return validated


def get_targets_for_shader(shader: str, targets: list) -> List[Tuple[str, str]]:
    """Filter parameter targets list according to the current CS2 shader."""
    if not shader:
        return targets
    shader_low = str(shader).lower().strip()
    is_effects = "effects" in shader_low
    is_blend = "blend" in shader_low

    filtered = []
    for label_text, data in targets:
        if not data:
            filtered.append((label_text, data))
            continue
        is_effects_target = "(Effects)" in label_text
        is_layer_target = any(lbl in label_text for lbl in ("Layer 2", "Layer 3", "Layer 4"))

        if is_effects:
            if is_effects_target or not is_layer_target:
                filtered.append((label_text, data))
        elif is_blend:
            if not is_effects_target:
                filtered.append((label_text, data))
        else:
            if not is_effects_target and not is_layer_target:
                filtered.append((label_text, data))
    return filtered
