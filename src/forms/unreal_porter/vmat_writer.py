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

    if shader == "csgo_environment_blend.vfx" or shader == "csgo_environment_blend":
        has_layer2 = any(k.endswith("2") for k in slots) or any("2" in str(k) for k in (extra_scalars or {})) or any("2" in str(k) for k in (extra_vectors or {}))
        has_layer3 = any(k.endswith("3") for k in slots) or any("3" in str(k) for k in (extra_scalars or {})) or any("3" in str(k) for k in (extra_vectors or {}))
        has_layer4 = any(k.endswith("4") for k in slots) or any("4" in str(k) for k in (extra_scalars or {})) or any("4" in str(k) for k in (extra_vectors or {}))

        blend_flags = []
        if has_layer2 or (extra_params and "F_BLEND_EFFECTS_2" in extra_params):
            blend_flags.append("\n\t//---- Layer 2 ----\n\tF_BLEND_EFFECTS_2 1\n")
        if has_layer3 or (extra_params and "F_ENABLE_LAYER_3" in extra_params):
            blend_flags.append("\n\t//---- Layer 3 ----\n\tF_ENABLE_LAYER_3 1\n")
        if has_layer4 or (extra_params and "F_ENABLE_LAYER_4" in extra_params):
            blend_flags.append("\n\t//---- Layer 4 ----\n\tF_ENABLE_LAYER_4 1\n")
        flag_str = "".join(blend_flags)

        l1_color = slots.get("color1") or slots.get("color") or "materials/default/default_color.tga"
        l1_normal = slots.get("normal1") or slots.get("normal") or "materials/default/default_normal.tga"
        l1_rough = slots.get("rough1") or slots.get("rough") or "materials/default/default_rough.tga"
        l1_metal = slots.get("metal1") or slots.get("metal") or "materials/default/default_metal.tga"
        l1_ao = slots.get("ao1") or slots.get("ao") or "materials/default/default_ao.tga"
        l1_height = slots.get("height1") or slots.get("height") or "materials/default/default_height.tga"

        l1_lines = f"""\t//---- Layer 1 ----
\tg_bModelTint1 "0"
\tg_flHeightMapScale1 "1.000"
\tg_flHeightMapZeroPoint1 "0.500"
\tg_nVertexColorMode1 "0"
\tTextureAmbientOcclusion1 "{l1_ao}"
\tTextureColor1 "{l1_color}"
\tTextureHeight1 "{l1_height}"
\tTextureMetalness1 "{l1_metal}"
\tTextureNormal1 "{l1_normal}"
\tTextureRoughness1 "{l1_rough}"
"""
        l2_lines = ""
        if has_layer2:
            l2_color = slots.get("color2", "materials/default/default_color.tga")
            l2_normal = slots.get("normal2", "materials/default/default_normal.tga")
            l2_rough = slots.get("rough2", "materials/default/default_rough.tga")
            l2_metal = slots.get("metal2", "materials/default/default_metal.tga")
            l2_ao = slots.get("ao2", "materials/default/default_ao.tga")
            l2_height = slots.get("height2", "materials/default/default_height.tga")
            l2_lines = f"""\t//---- Layer 2 ----
\tg_flBlendSoftness2 "0.100"
\tg_flHeightMapScale2 "1.000"
\tg_flHeightMapZeroPoint2 "0.500"
\tTextureAmbientOcclusion2 "{l2_ao}"
\tTextureColor2 "{l2_color}"
\tTextureHeight2 "{l2_height}"
\tTextureMetalness2 "{l2_metal}"
\tTextureNormal2 "{l2_normal}"
\tTextureRoughness2 "{l2_rough}"
"""
        l3_lines = ""
        if has_layer3:
            l3_color = slots.get("color3", "materials/default/default_color.tga")
            l3_normal = slots.get("normal3", "materials/default/default_normal.tga")
            l3_rough = slots.get("rough3", "materials/default/default_rough.tga")
            l3_metal = slots.get("metal3", "materials/default/default_metal.tga")
            l3_ao = slots.get("ao3", "materials/default/default_ao.tga")
            l3_height = slots.get("height3", "materials/default/default_height.tga")
            l3_lines = f"""\t//---- Layer 3 ----
\tg_flBlendSoftness3 "0.100"
\tg_flHeightMapScale3 "1.000"
\tg_flHeightMapZeroPoint3 "0.500"
\tTextureAmbientOcclusion3 "{l3_ao}"
\tTextureColor3 "{l3_color}"
\tTextureHeight3 "{l3_height}"
\tTextureMetalness3 "{l3_metal}"
\tTextureNormal3 "{l3_normal}"
\tTextureRoughness3 "{l3_rough}"
"""
        l4_lines = ""
        if has_layer4:
            l4_color = slots.get("color4", "materials/default/default_color.tga")
            l4_normal = slots.get("normal4", "materials/default/default_normal.tga")
            l4_rough = slots.get("rough4", "materials/default/default_rough.tga")
            l4_metal = slots.get("metal4", "materials/default/default_metal.tga")
            l4_ao = slots.get("ao4", "materials/default/default_ao.tga")
            l4_height = slots.get("height4", "materials/default/default_height.tga")
            l4_lines = f"""\t//---- Layer 4 ----
\tg_flBlendSoftness4 "0.100"
\tg_flHeightMapScale4 "1.000"
\tg_flHeightMapZeroPoint4 "0.500"
\tTextureAmbientOcclusion4 "{l4_ao}"
\tTextureColor4 "{l4_color}"
\tTextureHeight4 "{l4_height}"
\tTextureMetalness4 "{l4_metal}"
\tTextureNormal4 "{l4_normal}"
\tTextureRoughness4 "{l4_rough}"
"""

        mat_layers = ""
        ml_refs = []
        for i in range(1, 5):
            ref = slots.get(f"material_layer_{i}") or (extra_params or {}).get(f"MaterialLayerReference_{i}")
            if ref:
                ml_refs.append(f'\t\tMaterialLayerReference_{i} "{ref}"')
        if ml_refs:
            mat_layers = "\n\t// Material Layer References\n\tMaterialLayers\n\t{\n" + "\n".join(ml_refs) + "\n\t}\n"

        content = f"""// THIS FILE IS AUTO-GENERATED

Layer0
{{
\tshader "{shader}"
{flag_str}
\t//---- Color ----
\tg_flModelTintAmount "1.000"
\tg_nScaleTexCoordUByModelScaleAxis "0" // None
\tg_nScaleTexCoordVByModelScaleAxis "0" // None
\tg_vColorTint "{color_tint_str}"

\t//---- Fog ----
\tg_bFogEnabled "1"

{l1_lines}{l2_lines}{l3_lines}{l4_lines}{extra_lines}
\t//---- Texture Address Mode ----
\tg_nTextureAddressModeU "0" // Wrap
\tg_nTextureAddressModeV "0" // Wrap
{mat_layers}}}
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
