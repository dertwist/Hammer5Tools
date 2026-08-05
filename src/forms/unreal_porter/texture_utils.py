import os
from PIL import Image

def unpack_rma(rma_path: str, output_dir: str, base_name: str, has_height: bool = False, is_orm: bool = False):
    """
    Unpacks an Unreal RMA or ORM texture into separate TGA maps.
    RMA: R -> Roughness, G -> Metalness, B -> AO
    ORM: R -> AO, G -> Roughness, B -> Metalness
    A -> Height (if has_height is True)
    """
    try:
        img = Image.open(rma_path).convert("RGBA")
        ch_r, ch_g, ch_b, ch_a = img.split()

        if is_orm:
            rough_ch, metal_ch, ao_ch = ch_g, ch_b, ch_r
        else:
            rough_ch, metal_ch, ao_ch = ch_r, ch_g, ch_b

        rough_path = os.path.join(output_dir, f"{base_name}_rough.tga")
        metal_path = os.path.join(output_dir, f"{base_name}_metal.tga")
        ao_path = os.path.join(output_dir, f"{base_name}_ao.tga")

        rough_ch.convert("L").save(rough_path)
        metal_ch.convert("L").save(metal_path)
        ao_ch.convert("L").save(ao_path)

        height_path = None
        if has_height:
            height_path = os.path.join(output_dir, f"{base_name}_height.tga")
            ch_a.convert("L").save(height_path)

        return {
            "rough": rough_path,
            "metal": metal_path,
            "ao": ao_path,
            "height": height_path
        }
    except Exception as e:
        print(f"Error unpacking RMA/ORM: {e}")
        return None

def unpack_orh(orh_path: str, output_dir: str, base_name: str):
    """
    Unpacks an Unreal ORH texture into separate TGA maps.
    ORH: R -> AO, G -> Roughness, B -> Height
    """
    try:
        img = Image.open(orh_path).convert("RGBA")
        ch_r, ch_g, ch_b, ch_a = img.split()

        ao_path = os.path.join(output_dir, f"{base_name}_ao.tga")
        rough_path = os.path.join(output_dir, f"{base_name}_rough.tga")
        height_path = os.path.join(output_dir, f"{base_name}_height.tga")

        ch_r.convert("L").save(ao_path)
        ch_g.convert("L").save(rough_path)
        ch_b.convert("L").save(height_path)

        return {
            "ao": ao_path,
            "rough": rough_path,
            "height": height_path
        }
    except Exception as e:
        print(f"Error unpacking ORH: {e}")
        return None

def extract_alpha(color_path: str, out_path: str, mid_band=(32, 223), max_mid=0.10, min_off=0.02):
    """
    Splits the alpha channel of an RGBA colour map out into its own 8-bit TGA,
    for use as csgo_environment's TextureTranslucency slot.

    Only does so when the alpha reads as a *cutout* mask. UE packs two different
    things into that channel: a shape mask (bimodal - a pixel is on or off, this
    is what alpha-test wants) and a blend/detail mask (a gradient, used to drive
    a layer blend). Running alpha-test off a blend mask punches holes in solid
    geometry, so a channel with more than `max_mid` of its pixels sitting in the
    middle of the range is rejected, as is one with nothing meaningfully cut out.

    Returns the written path, or None if the channel isn't a cutout mask.
    """
    try:
        img = Image.open(color_path)
        if img.mode != "RGBA":
            return None
        alpha = img.getchannel("A")
        lo, hi = alpha.getextrema()
        if lo == hi:
            return None                       # constant - nothing to extract

        hist = alpha.histogram()
        total = sum(hist)
        off = sum(hist[:mid_band[0]]) / total
        mid = sum(hist[mid_band[0]:mid_band[1] + 1]) / total
        if mid > max_mid or off < min_off:
            return None                       # blend/detail mask, not a shape

        alpha.save(out_path)
        return out_path
    except Exception as e:
        print(f"Error extracting alpha from {color_path}: {e}")
        return None


def invert_y_normal(img_or_path):
    """
    Inverts the Green (Y) channel of a normal map image.
    Unreal Engine uses DirectX normal maps (Green = Y-), while Source 2
    uses OpenGL normal maps (Green = Y+).
    Accepts either a PIL Image object or a file path string. Returns a PIL Image object.
    """
    if isinstance(img_or_path, str):
        img = Image.open(img_or_path)
    else:
        img = img_or_path

    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")

    bands = list(img.split())
    # Green channel (Y axis) is at index 1
    bands[1] = bands[1].point(lambda x: 255 - x)
    return Image.merge(img.mode, bands)


def convert_to_tga(input_path: str, output_dir: str, new_suffix: str, invert_y: bool = False, ext: str = "tga"):
    """
    Converts an image to target format with a new suffix, optionally inverting Y normal.
    """
    try:
        img = Image.open(input_path).convert("RGBA")
        if invert_y:
            img = invert_y_normal(img)
        output_name = f"{new_suffix}.{ext}"
        output_path = os.path.join(output_dir, output_name)
        img.save(output_path)
        return output_path
    except Exception as e:
        print(f"Error converting texture: {e}")
        return None

def is_metallic(metal_map_path: str):
    """
    Heuristic to check if a metalness map is actually metallic.
    """
    try:
        img = Image.open(metal_map_path).convert("L")
        # Check mean value
        stat = img.getextrema() # Not enough, let's use mean
        # For simplicity, let's just check if there's any significant white
        # Or just use the mean.
        import numpy as np
        data = np.array(img)
        mean_val = np.mean(data)
        return mean_val > 10 # 10/255 threshold as suggested
    except:
        return False
