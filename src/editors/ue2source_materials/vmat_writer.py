import os

def write_vmat(output_path: str, slots: dict):
    """
    Writes a Source 2 .vmat file based on the provided texture slots.
    slots = {
        "color": "materials/path/name_color.tga",
        "normal": "materials/path/name_normal.tga",
        "rough": "materials/path/name_rough.tga",
        "metal": "materials/path/name_metal.tga" or None,
        "ao": "materials/path/name_ao.tga",
        "height": "materials/path/name_height.tga" or None,
    }
    """
    metal_line = (
        f'\tTextureMetalness1 "{slots["metal"]}"\n'
        if slots.get("metal")
        else '\tTextureMetalness1 "[0.000000 0.000000 0.000000 0.000000]"\n'
    )
    height_line = (
        f'\tTextureHeight1 "{slots["height"]}"\n'
        if slots.get("height")
        else '\tTextureHeight1 "[0.500000 0.500000 0.500000 0.000000]"\n'
    )
    
    # Ensure default AO if missing
    ao_line = f'\tTextureAmbientOcclusion1 "{slots["ao"]}"\n' if slots.get("ao") else '\tTextureAmbientOcclusion1 "materials/default/default_ao.tga"\n'
    color_line = f'\tTextureColor1 "{slots["color"]}"\n' if slots.get("color") else '\tTextureColor1 "materials/default/default_color.tga"\n'
    normal_line = f'\tTextureNormal1 "{slots["normal"]}"\n' if slots.get("normal") else '\tTextureNormal1 "materials/default/default_normal.tga"\n'
    rough_line = f'\tTextureRoughness1 "{slots["rough"]}"\n' if slots.get("rough") else '\tTextureRoughness1 "materials/default/default_rough.tga"\n'

    content = f"""// THIS FILE IS AUTO-GENERATED

Layer0
{{
\tshader "csgo_environment.vfx"

\t//---- Color ----
\tg_flModelTintAmount "1.000"
\tg_nScaleTexCoordUByModelScaleAxis "0" // None
\tg_nScaleTexCoordVByModelScaleAxis "0" // None
\tg_vColorTint "[1.000000 1.000000 1.000000 0.000000]"

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

\t//---- Texture Address Mode ----
\tg_nTextureAddressModeU "0" // Wrap
\tg_nTextureAddressModeV "0" // Wrap
}}
"""
    with open(output_path, "w") as f:
        f.write(content)
