import os

def write_vmat(
    output_path: str,
    slots: dict,
    shader: str = "csgo_environment.vfx",
    color_tint=None,
    roughness_scale: float = 1.0,
    metalness_scale: float = 1.0,
    extra_params: dict = None,
    alpha_test_ref: float = None,
    render_backfaces: bool = False,
    extra_scalars: dict = None,
    extra_vectors: dict = None,
):
    """
    Writes a Source 2 .vmat file based on the provided texture slots and shader parameters.
    slots = {
        "color": "materials/path/name_color.tga",
        "normal": "materials/path/name_normal.tga",
        "rough": "materials/path/name_rough.tga",
        "metal": "materials/path/name_metal.tga" or None,
        "ao": "materials/path/name_ao.tga",
        "height": "materials/path/name_height.tga" or None,
        "trans": "materials/path/name_trans.tga" or None,   # cutout mask
    }

    Pass `alpha_test_ref` (e.g. 0.5, or ~0.33 for thick foliage cards) together with
    a "trans" slot to emit the alpha-test block. Without it a cutout mesh - grass,
    leaves, netting - renders as an opaque quad, which is what every foliage
    material in a stock conversion does. `render_backfaces` is almost always wanted
    alongside it, since cutout foliage is modelled as single-sided cards.

    Get the mask from texture_utils.extract_alpha(); it declines to split a
    channel that is a blend mask rather than a shape mask.

    `extra_scalars` ({g_flName: float}) and `extra_vectors` ({g_vName: (r,g,b)})
    emit authored scalar/vector params (e.g. a UE emissive intensity migrated to a
    Source 2 scalar) alongside the slot-driven ones. They are typed, unlike the
    stringly-typed `extra_params`, which quotes its values verbatim.
    """
    color_tint_str = (
        f"[{color_tint[0]:.6f} {color_tint[1]:.6f} {color_tint[2]:.6f} 0.000000]"
        if color_tint and len(color_tint) >= 3
        else "[1.000000 1.000000 1.000000 0.000000]"
    )

    metal_line = (
        f'\tTextureMetalness1 "{slots["metal"]}"\n'
        if slots.get("metal")
        else f'\tTextureMetalness1 "[{metalness_scale:.6f} {metalness_scale:.6f} {metalness_scale:.6f} 0.000000]"\n'
    )
    height_line = (
        f'\tTextureHeight1 "{slots["height"]}"\n'
        if slots.get("height")
        else '\tTextureHeight1 "[0.500000 0.500000 0.500000 0.000000]"\n'
    )

    ao_line = f'\tTextureAmbientOcclusion1 "{slots["ao"]}"\n' if slots.get("ao") else '\tTextureAmbientOcclusion1 "materials/default/default_ao.tga"\n'
    color_line = f'\tTextureColor1 "{slots["color"]}"\n' if slots.get("color") else '\tTextureColor1 "materials/default/default_color.tga"\n'
    normal_line = f'\tTextureNormal1 "{slots["normal"]}"\n' if slots.get("normal") else '\tTextureNormal1 "materials/default/default_normal.tga"\n'
    rough_line = (
        f'\tTextureRoughness1 "{slots["rough"]}"\n'
        if slots.get("rough")
        else f'\tTextureRoughness1 "[{roughness_scale:.6f} {roughness_scale:.6f} {roughness_scale:.6f} 0.000000]"\n'
    )

    extra_lines = ""
    if extra_params:
        for k, v in extra_params.items():
            extra_lines += f'\t{k} "{v}"\n'
    # Typed scalar/vector params from the param-mapping UI: floats are quoted
    # as-is, vectors are wrapped in Source 2's "[r g b a]" literal form.
    if extra_scalars:
        for k, v in extra_scalars.items():
            extra_lines += f'\t{k} "{float(v):.6f}"\n'
    if extra_vectors:
        for k, v in extra_vectors.items():
            if v and len(v) >= 3:
                extra_lines += f'\t{k} "[{v[0]:.6f} {v[1]:.6f} {v[2]:.6f} 0.000000]"\n'

    if shader == "csgo_static_overlay.vfx" or shader == "csgo_static_overlay":
        has_lit = bool(extra_params and extra_params.get("F_LIT") in ("1", 1, True))
        tex_color = slots.get("color") or slots.get("TextureColor") or ""
        tex_ao = slots.get("ao") or slots.get("TextureAmbientOcclusion") or ""
        tex_metal = slots.get("metal") or slots.get("TextureMetalness") or ""
        tex_rough = slots.get("rough") or slots.get("TextureRoughness") or ""
        tex_normal = slots.get("normal") or slots.get("TextureNormal") or ""
        tex_emissive = slots.get("emissive") or slots.get("TextureSelfIllumMask") or ""

        if has_lit:
            content = f"""// THIS FILE IS AUTO-GENERATED

Layer0
{{
\tshader "csgo_static_overlay.vfx"

\t//---- Lighting ----
\tF_LIT 1

\t//---- Ambient Occlusion ----
\tTextureAmbientOcclusion "{tex_ao}"

\t//---- Color ----
\tg_flModelTintAmount "1.000"
\tg_flTexCoordRotation "0.000"
\tg_fTextureColorBrightness "1.000"
\tg_fTextureColorContrast "1.000"
\tg_fTextureColorSaturation "1.000"
\tg_nScaleTexCoordUByModelScaleAxis "0"
\tg_nScaleTexCoordVByModelScaleAxis "0"
\tg_vColorTint "{color_tint_str}"
\tg_vTexCoordCenter "[0.500 0.500]"
\tg_vTexCoordOffset "[0.000 0.000]"
\tg_vTexCoordScale "[1.000 1.000]"
\tg_vTexCoordScrollSpeed "[0.000 0.000]"
\tg_vTextureColorCorrectionTint "[1.000000 1.000000 1.000000 0.000000]"
\tTextureColor "{tex_color}"

\t//---- Fog ----
\tg_bFogEnabled "1"

\t//---- Lighting ----
\tg_fTextureRoughnessBrightness "1.000"
\tg_fTextureRoughnessContrast "1.000"
\tTextureMetalness "{tex_metal}"
\tTextureRoughness "{tex_rough}"

\t//---- Normal Map ----
\tg_fTextureNormalContrast "1.000"
\tTextureNormal "{tex_normal}"

\t//---- Self Illum ----
\tg_flSelfIllumAlbedoFactor "1.000"
\tg_flSelfIllumBrightness "0.000"
\tg_flSelfIllumScale "1.000"
\tg_vSelfIllumScrollSpeed "[0.000 0.000]"
\tg_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"
\tTextureSelfIllumMask "{tex_emissive}"

\t//---- Texture Address Mode ----
\tg_nTextureAddressModeU "0"
\tg_nTextureAddressModeV "0"


\tVariableState
\t{{
\t\t"Color"
\t\t{{
\t\t\t"Color Correction" 0
\t\t}}
\t\t"Fog"
\t\t{{
\t\t}}
\t\t"Texture Address Mode"
\t\t{{
\t\t}}
\t}}
}}
"""
        else:
            content = f"""// THIS FILE IS AUTO-GENERATED

Layer0
{{
\tshader "csgo_static_overlay.vfx"

\t//---- Color ----
\tg_flModelTintAmount "1.000"
\tg_flTexCoordRotation "0.000"
\tg_fTextureColorBrightness "1.000"
\tg_fTextureColorContrast "1.000"
\tg_fTextureColorSaturation "1.000"
\tg_nScaleTexCoordUByModelScaleAxis "0" // None
\tg_nScaleTexCoordVByModelScaleAxis "0" // None
\tg_vColorTint "{color_tint_str}"
\tg_vTexCoordCenter "[0.500 0.500]"
\tg_vTexCoordOffset "[0.000 0.000]"
\tg_vTexCoordScale "[1.000 1.000]"
\tg_vTexCoordScrollSpeed "[0.000 0.000]"
\tg_vTextureColorCorrectionTint "[1.000000 1.000000 1.000000 0.000000]"
\tTextureColor "{tex_color}"

\t//---- Fog ----
\tg_bFogEnabled "1"

\t//---- Texture Address Mode ----
\tg_nTextureAddressModeU "0" // Wrap
\tg_nTextureAddressModeV "0" // Wrap


\tVariableState
\t{{
\t}}
}}
"""
    elif shader == "csgo_effects.vfx" or shader == "csgo_effects":
        has_backfaces = render_backfaces or bool(extra_params and extra_params.get("F_RENDER_BACKFACES") in ("1", 1, True))
        has_depth_feather = bool(extra_params and extra_params.get("F_DEPTH_FEATHER") in ("1", 1, True)) or any(k in (extra_scalars or {}) for k in ("g_flFeatherDistance", "g_flFeatherFalloff"))
        has_tint_mask = bool(slots.get("tintmask") or slots.get("TextureTintMask")) or bool(extra_params and extra_params.get("F_TINT_MASK") in ("1", 1, True))
        has_additive = bool(extra_params and extra_params.get("F_ADDITIVE_BLEND") in ("1", 1, True))
        has_disable_z = bool(extra_params and extra_params.get("F_DISABLE_Z_BUFFERING") in ("1", 1, True))

        flag_items = []
        if has_backfaces:
            flag_items.append("\t//---- 2-Sided Rendering ----\n\tF_RENDER_BACKFACES 1")
        if has_depth_feather:
            flag_items.append("\t//---- Depth Feather ----\n\tF_DEPTH_FEATHER 1")
        if has_tint_mask:
            flag_items.append("\t//---- Per-Instance Tint Mask ----\n\tF_TINT_MASK 1")
        if has_additive:
            flag_items.append("\t//---- Translucent ----\n\tF_ADDITIVE_BLEND 1")
        if has_disable_z:
            flag_items.append("\t//---- Z-Buffering ----\n\tF_DISABLE_Z_BUFFERING 1")
        flag_str = ("\n\n".join(flag_items) + "\n\n") if flag_items else ""

        color_boost = (extra_scalars or {}).get("g_flColorBoost", "1.000")
        if isinstance(color_boost, (int, float)): color_boost = f"{float(color_boost):.3f}"
        scroll_speed = (extra_vectors or {}).get("g_vTexCoordScrollSpeed")
        scroll_str = f"[{scroll_speed[0]:.3f} {scroll_speed[1]:.3f}]" if (scroll_speed and len(scroll_speed) >= 2) else "[0.000 0.000]"
        tex_color = slots.get("color") or slots.get("TextureColor") or ""
        tex_tintmask = slots.get("tintmask") or slots.get("TextureTintMask") or ""

        color_block = f"""\t//---- Color ----
\tg_flColorBoost "{color_boost}"
\tg_vColorTint "{color_tint_str}"
\tg_vTexCoordScrollSpeed "{scroll_str}"
\tTextureColor "{tex_color}"
"""
        if has_tint_mask:
            color_block += f'\tTextureTintMask "{tex_tintmask}"\n'

        feather_block = ""
        if has_depth_feather:
            f_dist = (extra_scalars or {}).get("g_flFeatherDistance", "0.000")
            f_falloff = (extra_scalars or {}).get("g_flFeatherFalloff", "1.000")
            if isinstance(f_dist, (int, float)): f_dist = f"{float(f_dist):.3f}"
            if isinstance(f_falloff, (int, float)): f_falloff = f"{float(f_falloff):.3f}"
            feather_block = f"""\n\t//---- Depth Feather ----
\tg_flFeatherDistance "{f_dist}"
\tg_flFeatherFalloff "{f_falloff}"
"""

        fade_dist = (extra_scalars or {}).get("g_flFadeDistance", "1.000")
        fade_falloff = (extra_scalars or {}).get("g_flFadeFalloff", "1.000")
        fade_max = (extra_scalars or {}).get("g_flFadeMax", "1.000")
        fade_min = (extra_scalars or {}).get("g_flFadeMin", "0.000")
        if isinstance(fade_dist, (int, float)): fade_dist = f"{float(fade_dist):.3f}"
        if isinstance(fade_falloff, (int, float)): fade_falloff = f"{float(fade_falloff):.3f}"
        if isinstance(fade_max, (int, float)): fade_max = f"{float(fade_max):.3f}"
        if isinstance(fade_min, (int, float)): fade_min = f"{float(fade_min):.3f}"

        fade_block = f"""\n\t//---- Distance Fade ----
\tg_flFadeDistance "{fade_dist}"
\tg_flFadeFalloff "{fade_falloff}"
\tg_flFadeMax "{fade_max}"
\tg_flFadeMin "{fade_min}"
"""

        fog_val = (extra_params or {}).get("g_bFogEnabled", "1")
        fog_block = f"""\n\t//---- Fog ----
\tg_bFogEnabled "{fog_val}"
"""

        fres_exp = (extra_scalars or {}).get("g_flFresnelExponent", "2.700")
        fres_falloff = (extra_scalars or {}).get("g_flFresnelFalloff", "1.000")
        fres_max = (extra_scalars or {}).get("g_flFresnelMax", "1.000")
        fres_min = (extra_scalars or {}).get("g_flFresnelMin", "0.000")
        if isinstance(fres_exp, (int, float)): fres_exp = f"{float(fres_exp):.3f}"
        if isinstance(fres_falloff, (int, float)): fres_falloff = f"{float(fres_falloff):.3f}"
        if isinstance(fres_max, (int, float)): fres_max = f"{float(fres_max):.3f}"
        if isinstance(fres_min, (int, float)): fres_min = f"{float(fres_min):.3f}"

        fresnel_block = f"""\n\t//---- Fresnel ----
\tg_flFresnelExponent "{fres_exp}"
\tg_flFresnelFalloff "{fres_falloff}"
\tg_flFresnelMax "{fres_max}"
\tg_flFresnelMin "{fres_min}"
"""

        m1_pan = (extra_vectors or {}).get("g_vMask1PanSpeed")
        m1_pan_str = f"[{m1_pan[0]:.3f} {m1_pan[1]:.3f}]" if (m1_pan and len(m1_pan) >= 2) else "[0.000 0.000]"
        m1_scale = (extra_vectors or {}).get("g_vMask1Scale")
        m1_scale_str = f"[{m1_scale[0]:.3f} {m1_scale[1]:.3f}]" if (m1_scale and len(m1_scale) >= 2) else "[1.000 1.000]"
        tex_m1 = slots.get("mask1") or slots.get("TextureMask1") or ""

        m2_pan = (extra_vectors or {}).get("g_vMask2PanSpeed")
        m2_pan_str = f"[{m2_pan[0]:.3f} {m2_pan[1]:.3f}]" if (m2_pan and len(m2_pan) >= 2) else "[0.000 0.000]"
        m2_scale = (extra_vectors or {}).get("g_vMask2Scale")
        m2_scale_str = f"[{m2_scale[0]:.3f} {m2_scale[1]:.3f}]" if (m2_scale and len(m2_scale) >= 2) else "[1.000 1.000]"
        tex_m2 = slots.get("mask2") or slots.get("TextureMask2") or ""

        m3_pan = (extra_vectors or {}).get("g_vMask3PanSpeed")
        m3_pan_str = f"[{m3_pan[0]:.3f} {m3_pan[1]:.3f}]" if (m3_pan and len(m3_pan) >= 2) else "[0.000 0.000]"
        m3_scale = (extra_vectors or {}).get("g_vMask3Scale")
        m3_scale_str = f"[{m3_scale[0]:.3f} {m3_scale[1]:.3f}]" if (m3_scale and len(m3_scale) >= 2) else "[1.000 1.000]"
        tex_m3 = slots.get("mask3") or slots.get("TextureMask3") or ""

        mask_blocks = f"""\n\t//---- Mask 1 ----
\tg_vMask1PanSpeed "{m1_pan_str}"
\tg_vMask1Scale "{m1_scale_str}"
\tTextureMask1 "{tex_m1}"

\t//---- Mask 2 ----
\tg_vMask2PanSpeed "{m2_pan_str}"
\tg_vMask2Scale "{m2_scale_str}"
\tTextureMask2 "{tex_m2}"

\t//---- Mask 3 ----
\tg_vMask3PanSpeed "{m3_pan_str}"
\tg_vMask3Scale "{m3_scale_str}"
\tTextureMask3 "{tex_m3}"
"""

        addr_u = (extra_params or {}).get("g_nTextureAddressModeU", "0")
        addr_v = (extra_params or {}).get("g_nTextureAddressModeV", "0")
        addr_block = f"""\n\t//---- Texture Address Mode ----
\tg_nTextureAddressModeU "{addr_u}"
\tg_nTextureAddressModeV "{addr_v}"
"""

        opac_scale = (extra_scalars or {}).get("g_flOpacityScale", "1.000")
        if isinstance(opac_scale, (int, float)): opac_scale = f"{float(opac_scale):.3f}"
        tex_trans = slots.get("opacity") or slots.get("trans") or slots.get("TextureTranslucency") or ""
        trans_block = f"""\n\t//---- Translucent ----
\tg_flOpacityScale "{opac_scale}"
\tTextureTranslucency "{tex_trans}"
"""

        unused_lines = []
        if not has_depth_feather:
            unused_lines.append('\t\t"g_flFeatherDistance" "0"')
            unused_lines.append('\t\t"g_flFeatherFalloff" "1"')
        if not has_tint_mask:
            unused_lines.append('\t\t"TextureTintMask" ""')

        unused_block = ""
        if unused_lines:
            unused_block = "\n\tUnusedVariables\n\t{\n" + "\n".join(unused_lines) + "\n\t}\n"

        content = f"""// THIS FILE IS AUTO-GENERATED

Layer0
{{
\tshader "csgo_effects.vfx"

{flag_str}{color_block}{feather_block}{fade_block}{fog_block}{fresnel_block}{mask_blocks}{addr_block}{trans_block}{unused_block}}}
"""
    elif shader == "csgo_environment_blend.vfx" or shader == "csgo_environment_blend":
        extra_p = extra_params or {}
        has_layer3 = bool(extra_p.get("F_ENABLE_LAYER_3") in ("1", 1, True)) or any(k.endswith("3") for k in slots) or any("3" in str(k) for k in (extra_scalars or {})) or any("3" in str(k) for k in (extra_vectors or {}))
        has_layer2_facing = bool(extra_p.get("F_BLEND_BY_FACING_DIRECTION_2") in ("1", 1, True))
        has_layer3_facing = has_layer3 and bool(extra_p.get("F_BLEND_BY_FACING_DIRECTION_3") in ("1", 1, True))
        has_layer2_effects = bool(extra_p.get("F_BLEND_EFFECTS_2") in ("1", 1, True))
        has_layer3_effects = has_layer3 and bool(extra_p.get("F_BLEND_EFFECTS_3") in ("1", 1, True))
        has_backfaces = bool(extra_p.get("F_RENDER_BACKFACES") in ("1", 1, True)) or render_backfaces
        has_use_new_blending = bool(extra_p.get("F_USE_NEW_BLENDING") in ("1", 1, True))
        has_shared_overlay = bool(extra_p.get("F_SHARED_COLOR_OVERLAY") in ("1", 1, True)) or bool(slots.get("sharedcoloroverlay"))
        has_detail_normal = bool(extra_p.get("F_DETAIL_NORMAL") in ("1", 1, True)) or bool(slots.get("normaldetail1"))
        has_alpha_test = bool(extra_p.get("F_ALPHA_TEST") in ("1", 1, True)) or (alpha_test_ref is not None)
        has_wetness = bool(extra_p.get("F_WETNESS") in ("1", 1, True))

        flag_sections = []
        if has_backfaces:
            flag_sections.append("\t//---- 2-Sided Rendering ----\n\tF_RENDER_BACKFACES 1")
        if has_use_new_blending:
            flag_sections.append("\t//---- Blending ----\n\tF_USE_NEW_BLENDING 1")
        if has_shared_overlay:
            flag_sections.append("\t//---- Color Effects ----\n\tF_SHARED_COLOR_OVERLAY 1")
        if has_detail_normal:
            flag_sections.append("\t//---- Detail ----\n\tF_DETAIL_NORMAL 1")

        l2_flags = []
        if has_layer2_facing: l2_flags.append("\tF_BLEND_BY_FACING_DIRECTION_2 1")
        if has_layer2_effects: l2_flags.append("\tF_BLEND_EFFECTS_2 1")
        if l2_flags:
            flag_sections.append("\t//---- Layer 2 ----\n" + "\n".join(l2_flags))

        l3_flags = []
        if has_layer3_facing: l3_flags.append("\tF_BLEND_BY_FACING_DIRECTION_3 1")
        if has_layer3_effects: l3_flags.append("\tF_BLEND_EFFECTS_3 1")
        if has_layer3: l3_flags.append("\tF_ENABLE_LAYER_3 1")
        if l3_flags:
            flag_sections.append("\t//---- Layer 3 ----\n" + "\n".join(l3_flags))

        if has_alpha_test:
            flag_sections.append("\t//---- Translucent ----\n\tF_ALPHA_TEST 1")
        if has_wetness:
            flag_sections.append("\t//---- Wetness ----\n\tF_WETNESS 1")

        flag_str = ("\n\n".join(flag_sections) + "\n\n") if flag_sections else ""

        blend_effects_block = ""
        if has_layer2_effects or has_layer3_effects:
            blend_effects_block = f"""\t//---- Blend Effects ----
\tg_bBorderTintMask2 "0"
\tg_bBorderTintMask3 "0"
\tg_flBevelCurve2 "0.000"
\tg_flBevelCurve3 "0.000"
\tg_flBevelOffset2 "0.000"
\tg_flBevelOffset3 "0.000"
\tg_flBevelSoftness2 "0.100"
\tg_flBevelSoftness3 "0.100"
\tg_flBevelSpread2 "0.100"
\tg_flBevelSpread3 "0.100"
\tg_flBevelStrength2 "0.000"
\tg_flBevelStrength3 "0.000"
\tg_flBorderOffset2 "0.000"
\tg_flBorderOffset3 "0.000"
\tg_flBorderSoftness2 "0.100"
\tg_flBorderSoftness3 "0.100"
\tg_flBorderSpread2 "0.100"
\tg_flBorderSpread3 "0.100"
\tg_vBevelLayerAmount2 "[1.000 1.000]"
\tg_vBevelLayerAmount3 "[1.000 1.000]"
\tg_vBorderLayerAmount2 "[1.000 0.000]"
\tg_vBorderLayerAmount3 "[1.000 0.000]"
\tg_vBorderTint2 "[1.000000 1.000000 1.000000 0.000000]"
\tg_vBorderTint3 "[1.000000 1.000000 1.000000 0.000000]"

"""

        color_overlay_block = ""
        if has_shared_overlay:
            tex_overlay = slots.get("sharedcoloroverlay") or ""
            color_overlay_block = f"""\tg_flOverlayBrightnessContrast "1.000"
\tg_flOverlayDarknessContrast "1.000"
\tg_flOverlayTexCoordRotation "0.000"
\tg_nColorOverlayUVSet "2"
\tg_vColorOverlayLayerStrengths "[1.000 1.000 1.000]"
\tg_vColorOverlayTintMaskStrengths "[0.000 0.000 0.000]"
\tg_vOverlayTexCoordCenter "[0.500 0.500]"
\tg_vOverlayTexCoordOffset "[0.000 0.000]"
\tg_vOverlayTexCoordScale "[1.000 1.000]"
\tTextureSharedColorOverlay "{tex_overlay}"
"""

        color_block = f"""\t//---- Color ----
\tg_flBlendSoftnessDistanceModifierStrength "1.000"
\tg_flModelTintAmount "1.000"
{color_overlay_block}\tg_nScaleTexCoord2UByModelScaleAxis "0" // None
\tg_nScaleTexCoord2VByModelScaleAxis "0" // None
\tg_nScaleTexCoordUByModelScaleAxis "0" // None
\tg_nScaleTexCoordVByModelScaleAxis "0" // None
\tg_vColorTint "{color_tint_str}"

\t//---- Fog ----
\tg_bFogEnabled "1"

"""

        l1_color = slots.get("color1") or slots.get("color") or ""
        l1_normal = slots.get("normal1") or slots.get("normal") or ""
        l1_rough = slots.get("rough1") or slots.get("rough") or ""
        l1_metal = slots.get("metal1") or slots.get("metal") or ""
        l1_ao = slots.get("ao1") or slots.get("ao") or ""
        l1_height = slots.get("height1") or slots.get("height") or ""
        l1_mask = slots.get("tintmask1") or ""
        l1_detail = slots.get("normaldetail1") or ""
        l1_trans = slots.get("opacity") or slots.get("trans") or ""

        l1_lines = f"""\t//---- Layer 1 ----
\tTextureAmbientOcclusion1 "{l1_ao}"
\tTextureColor1 "{l1_color}"
\tTextureHeight1 "{l1_height}"
\tTextureMetalness1 "{l1_metal}"
\tTextureNormal1 "{l1_normal}"
"""
        if has_detail_normal:
            l1_lines += f'\tTextureNormalDetail1 "{l1_detail}"\n'
        l1_lines += f'\tTextureRoughness1 "{l1_rough}"\n\tTextureTintMask1 "{l1_mask}"\n'
        if has_alpha_test:
            l1_lines += f'\tTextureTranslucency1 "{l1_trans}"\n'

        l2_color = slots.get("color2") or ""
        l2_normal = slots.get("normal2") or ""
        l2_rough = slots.get("rough2") or ""
        l2_metal = slots.get("metal2") or ""
        l2_ao = slots.get("ao2") or ""
        l2_height = slots.get("height2") or ""
        l2_mask = slots.get("tintmask2") or ""
        l2_detail = slots.get("normaldetail2") or ""

        l2_lines = f"""
\t//---- Layer 2 ----
\tTextureAmbientOcclusion2 "{l2_ao}"
\tTextureColor2 "{l2_color}"
\tTextureHeight2 "{l2_height}"
\tTextureMetalness2 "{l2_metal}"
\tTextureNormal2 "{l2_normal}"
"""
        if has_detail_normal:
            l2_lines += f'\tTextureNormalDetail2 "{l2_detail}"\n'
        l2_lines += f'\tTextureRoughness2 "{l2_rough}"\n\tTextureTintMask2 "{l2_mask}"\n'

        l3_lines = ""
        if has_layer3:
            l3_color = slots.get("color3") or ""
            l3_normal = slots.get("normal3") or ""
            l3_rough = slots.get("rough3") or ""
            l3_metal = slots.get("metal3") or ""
            l3_ao = slots.get("ao3") or ""
            l3_height = slots.get("height3") or ""
            l3_mask = slots.get("tintmask3") or ""
            l3_detail = slots.get("normaldetail3") or ""

            l3_lines = f"""
\t//---- Layer 3 ----
\tTextureAmbientOcclusion3 "{l3_ao}"
\tTextureColor3 "{l3_color}"
\tTextureHeight3 "{l3_height}"
\tTextureMetalness3 "{l3_metal}"
\tTextureNormal3 "{l3_normal}"
"""
            if has_detail_normal:
                l3_lines += f'\tTextureNormalDetail3 "{l3_detail}"\n'
            l3_lines += f'\tTextureRoughness3 "{l3_rough}"\n\tTextureTintMask3 "{l3_mask}"\n'

        trans_block = ""
        if has_alpha_test:
            ref_val = f"{alpha_test_ref:.3f}" if alpha_test_ref is not None else "0.500"
            trans_block = f"""
\t//---- Translucent ----
\tg_flAlphaTestReference "{ref_val}"
\tg_flAntiAliasedEdgeStrength "1.000"
"""

        wetness_block = ""
        if has_wetness:
            wetness_block = f"""
\t//---- Wetness ----
\tg_flHorizontalSurfaceTolerance "32.000"
\tg_flWetnessUnderlyingHeightMapInfluence "1.000"
\tg_fPuddleBlendSoftness "0.0801"
\tg_fPuddleHeight "0.500"
\tg_fPuddleRoughness "0.020"
\tg_fPuddleSedimentOpacity "0.250"
\tg_fRainStrength "1.000"
\tg_fRippleStrength "1.000"
\tg_fWetEdgeSoftness "0.2001"
\tg_fWetEdgeSpread "0.200"
\tg_fWetEdgeStrength "0.500"
\tg_fWetnessStrength "1.000"
\tg_vPuddleSedimentColor "[0.619608 0.560784 0.501961 0.000000]"
"""

        unused_lines = []
        if not has_layer3:
            unused_lines.extend([
                '\t\t"TextureAmbientOcclusion3" ""',
                '\t\t"TextureColor3" ""',
                '\t\t"TextureHeight3" ""',
                '\t\t"TextureMetalness3" ""',
                '\t\t"TextureNormal3" ""',
                '\t\t"TextureRoughness3" ""',
                '\t\t"TextureTintMask3" ""',
            ])
        if not has_wetness:
            unused_lines.extend([
                '\t\t"g_bPuddlesOnVerticalSurfaces" "0"',
                '\t\t"g_bWetnessUseHeightmapAdjustments" "0"',
                '\t\t"g_fPuddleSedimentHeight" "0.9"',
                '\t\t"g_fPuddleStrength" "1"',
            ])

        unused_block = ""
        if unused_lines:
            unused_block = "\n\tUnusedVariables\n\t{\n" + "\n".join(unused_lines) + "\n\t}\n"

        addr_block = """
\t//---- Texture Address Mode ----
\tg_nTextureAddressModeU "0"
\tg_nTextureAddressModeV "0"
"""

        content = f"""// THIS FILE IS AUTO-GENERATED

Layer0
{{
\tshader "{shader}"

{flag_str}{blend_effects_block}{color_block}{l1_lines}{l2_lines}{l3_lines}{addr_block}{trans_block}{wetness_block}{unused_block}}}
"""
    else:
        # Feature flags sit directly under the shader line; their scalar companions go
        # at the bottom. This is the layout Hammer's own material editor writes.
        alpha_test = alpha_test_ref is not None and slots.get("trans")
        flag_lines = ""
        if alpha_test:
            flag_lines += "\n\t//---- Translucent ----\n\tF_ALPHA_TEST 1\n"
        if render_backfaces:
            flag_lines += "\n\t//---- Faces ----\n\tF_RENDER_BACKFACES 1\n"

        trans_line = f'\tTextureTranslucency1 "{slots["trans"]}"\n' if alpha_test else ""
        alpha_tail = (
            f'\n\t//---- Translucent ----\n'
            f'\tg_flAlphaTestReference "{alpha_test_ref:.3f}"\n'
            f'\tg_flAntiAliasedEdgeStrength "1.000"\n'
            if alpha_test else ""
        )

        content = f"""// THIS FILE IS AUTO-GENERATED

Layer0
{{
\tshader "{shader}"
{flag_lines}
\t//---- Color ----
\tg_flModelTintAmount "1.000"
\tg_nScaleTexCoordUByModelScaleAxis "0" // None
\tg_nScaleTexCoordVByModelScaleAxis "0" // None
\tg_vColorTint "{color_tint_str}"

\t//---- Fog ----
\tg_bFogEnabled "1"

\t//---- Material1 ----
\tg_bSnowLayer1 "0"
\tg_flTexCoordRotation1 "0.000"
\tg_flWetnessDarkeningStrength1 "1.000"
\tg_nUVSet1 "1" // UV1
\tg_vTexCoordCenter1 "[0.500 0.500]"
\tg_vTexCoordOffset1 "[0.000 0.000]"
\tg_vTexCoordScale1 "[1.000 1.000]"
{ao_line}{color_line}{height_line}{metal_line}{normal_line}{rough_line}\tTextureTintMask1 "materials/default/default_mask.tga"
{trans_line}{extra_lines}
\t//---- Texture Address Mode ----
\tg_nTextureAddressModeU "0" // Wrap
\tg_nTextureAddressModeV "0" // Wrap
{alpha_tail}}}
"""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


def write_decal_vmat(
    output_path: str,
    slots: dict,
    color_tint=None,
):
    """
    Writes a Source 2 decal .vmat using csgo_static_overlay.vfx.

    Matches Hammer's own blank-material template for this shader exactly (a
    material editor's freshly-created csgo_static_overlay.vfx material, param
    names and all) — an earlier version of this function used g_tColor/g_tNormal/
    g_tAmbientOcclusion/g_tMetalness/F_BLEND_MODE, which came from decompiling a
    *compiled* .vmat_c and reading its internal runtime parameter names; those do
    not match the *source* .vmat authoring names Hammer actually writes, so
    materials built that way loaded with an empty TextureColor. There is no
    separate normal/AO/metalness slot in Hammer's default template for this
    shader, so the decal is color-only; the shape comes from TextureColor's
    alpha channel (material_converter composites the UE Opacity mask into it).

    slots = {"color": "materials/path/name_color.tga"}  # RGBA, alpha = decal shape
    """
    color_tint_str = (
        f"[{color_tint[0]:.6f} {color_tint[1]:.6f} {color_tint[2]:.6f} 0.000000]"
        if color_tint and len(color_tint) >= 3
        else "[1.000000 1.000000 1.000000 0.000000]"
    )
    color_path = slots.get("color") or ""

    content = f"""// THIS FILE IS AUTO-GENERATED

Layer0
{{
\tshader "csgo_static_overlay.vfx"

\t//---- Color ----
\tg_flModelTintAmount "1.000"
\tg_flTexCoordRotation "0.000"
\tg_fTextureColorBrightness "1.000"
\tg_fTextureColorContrast "1.000"
\tg_fTextureColorSaturation "1.000"
\tg_nScaleTexCoordUByModelScaleAxis "0" // None
\tg_nScaleTexCoordVByModelScaleAxis "0" // None
\tg_vColorTint "{color_tint_str}"
\tg_vTexCoordCenter "[0.500 0.500]"
\tg_vTexCoordOffset "[0.000 0.000]"
\tg_vTexCoordScale "[1.000 1.000]"
\tg_vTexCoordScrollSpeed "[0.000 0.000]"
\tg_vTextureColorCorrectionTint "[1.000000 1.000000 1.000000 0.000000]"
\tTextureColor "{color_path}"

\t//---- Fog ----
\tg_bFogEnabled "1"

\t//---- Texture Address Mode ----
\tg_nTextureAddressModeU "0" // Wrap
\tg_nTextureAddressModeV "0" // Wrap
}}
"""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
