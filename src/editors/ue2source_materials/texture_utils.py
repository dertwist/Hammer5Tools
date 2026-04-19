import os
from PIL import Image

def unpack_rma(rma_path: str, output_dir: str, base_name: str, has_height: bool = False):
    """
    Unpacks an Unreal RMA (Roughness, Metalness, AO) or RMAH (+Height) texture.
    R -> Roughness
    G -> Metalness
    B -> AO
    A -> Height (if has_height is True)
    """
    try:
        img = Image.open(rma_path).convert("RGBA")
        r, g, b, a = img.split()
        
        rough_path = os.path.join(output_dir, f"{base_name}_rough.tga")
        metal_path = os.path.join(output_dir, f"{base_name}_metal.tga")
        ao_path = os.path.join(output_dir, f"{base_name}_ao.tga")
        
        r.convert("L").save(rough_path)
        g.convert("L").save(metal_path)
        b.convert("L").save(ao_path)
        
        height_path = None
        if has_height:
            height_path = os.path.join(output_dir, f"{base_name}_height.tga")
            a.convert("L").save(height_path)
            
        return {
            "rough": rough_path,
            "metal": metal_path,
            "ao": ao_path,
            "height": height_path
        }
    except Exception as e:
        print(f"Error unpacking RMA: {e}")
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
