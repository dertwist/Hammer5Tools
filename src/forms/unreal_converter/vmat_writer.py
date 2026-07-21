import os

def write_vmat(
    output_path: str,
    slots: dict,
    shader: str = "csgo_environment.vfx",
    color_tint=None,
    roughness_scale: float = 1.0,
    metalness_scale: float = 1.0,
    extra_params: dict = None,
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
    }
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

    content = f"""// THIS FILE IS AUTO-GENERATED

Layer0
{{
\tshader "{shader}"

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
{extra_lines}
\t//---- Texture Address Mode ----
\tg_nTextureAddressModeU "0" // Wrap
\tg_nTextureAddressModeV "0" // Wrap
}}
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
