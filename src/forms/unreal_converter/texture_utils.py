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

def convert_to_tga(input_path: str, output_dir: str, new_suffix: str):
    """
    Converts a PNG to TGA with a new suffix.
    """
    try:
        base_name = os.path.basename(input_path)
        name_without_ext = os.path.splitext(base_name)[0]
        # Usually we want to strip the Unreal suffix like _ALB
        # But this function just converts and renames.
        
        img = Image.open(input_path).convert("RGBA")
        output_name = f"{new_suffix}.tga"
        output_path = os.path.join(output_dir, output_name)
        img.save(output_path)
        return output_path
    except Exception as e:
        print(f"Error converting to TGA: {e}")
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
