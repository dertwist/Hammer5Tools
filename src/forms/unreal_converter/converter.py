import os
import re
from PySide6.QtCore import QThread, Signal
from .texture_utils import unpack_rma, convert_to_tga, is_metallic
from .vmat_writer import write_vmat
from .bridge_client import UnrealBridge, BridgeError

_SUFFIX_MAP = {
    "ALB": "ALB", "BC": "ALB", "D": "ALB", "COLOR": "ALB", "DIFFUSE": "ALB", "BASECOLOR": "ALB", "ALBEDO": "ALB",
    "NRM": "NRM", "N": "NRM", "NORMAL": "NRM", "NORM": "NRM",
    "RMA": "RMA", "ORM": "ORM", "MASK": "RMA", "PACKED": "RMA",
    "RMAH": "RMAH", "ORMH": "ORMH",
    "ROUGH": "ROUGH", "R": "ROUGH", "ROUGHNESS": "ROUGH",
    "METAL": "METAL", "M": "METAL", "METALLIC": "METAL", "MET": "METAL",
    "AO": "AO", "OCCLUSION": "AO",
    "HEIGHT": "HEIGHT", "H": "HEIGHT", "DISP": "HEIGHT", "DISPLACEMENT": "HEIGHT",
}

def scan_and_group(input_dir):
    """
    Scans a directory for image files (PNG, TGA, JPG, JPEG) and groups them by base name.
    """
    groups = {}
    if not os.path.exists(input_dir):
        return groups

    valid_exts = (".png", ".tga", ".jpg", ".jpeg")
    for file in os.listdir(input_dir):
        if not file.lower().endswith(valid_exts):
            continue
        
        # Skip LUT/RVT prefixes
        if file.startswith(("LUT_", "RVT_")):
            continue

        parts = file.rsplit("_", 1)
        if len(parts) < 2:
            continue
            
        base_name = parts[0]
        raw_suffix = parts[1].rsplit(".", 1)[0].upper()
        canonical_suffix = _SUFFIX_MAP.get(raw_suffix)
        if not canonical_suffix:
            continue
        
        if base_name not in groups:
            groups[base_name] = {}
        
        groups[base_name][canonical_suffix] = os.path.join(input_dir, file)
        
    return groups

class MaterialConvertWorker(QThread):
    progress = Signal(int, int)          # current, total
    file_done = Signal(str, bool, str)   # name, success, message
    finished = Signal(list, list)        # created, skipped

    def __init__(self, input_dir, output_dir, materials_relative_path, selected_groups, parent=None):
        super().__init__(parent)
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.materials_path = materials_relative_path.replace("\\", "/").strip("/")
        self.selected_groups = selected_groups # Dict of base_name -> files

    def run(self):
        total = len(self.selected_groups)
        created, skipped = [], []
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        if self.materials_path.lower().startswith("materials/"):
            base_rel_path = self.materials_path
        else:
            base_rel_path = f"materials/{self.materials_path}" if self.materials_path else "materials"
        
        base_rel_path = base_rel_path.lower().strip("/")

        for i, (base_name, suffixes) in enumerate(self.selected_groups.items()):
            self.progress.emit(i + 1, total)
            out_name = base_name.lower()
            
            try:
                has_rma = "RMA" in suffixes
                has_orm = "ORM" in suffixes
                has_rmah = "RMAH" in suffixes
                has_ormh = "ORMH" in suffixes
                has_alb = "ALB" in suffixes
                has_nrm = "NRM" in suffixes
                has_rough = "ROUGH" in suffixes
                has_metal = "METAL" in suffixes
                has_ao = "AO" in suffixes
                has_height = "HEIGHT" in suffixes
                has_rgba = "RGBA" in suffixes
                
                if has_rgba:
                    self.file_done.emit(base_name, False, "RGBA texture detected. Skipping (unsupported custom packed mask).")
                    skipped.append((base_name, "RGBA unsupported"))
                    continue

                if not has_alb and not has_nrm and not has_rough and not has_rma and not has_orm:
                    raise Exception("Missing identifiable color/normal/mask textures")

                slots = {}
                
                def format_vmat_path(path):
                    return path.lower().replace("\\", "/")

                if has_alb:
                    slots["color"] = format_vmat_path(f"{base_rel_path}/{out_name}_color.tga")
                    convert_to_tga(suffixes["ALB"], self.output_dir, f"{out_name}_color")
                
                if has_nrm:
                    slots["normal"] = format_vmat_path(f"{base_rel_path}/{out_name}_normal.tga")
                    convert_to_tga(suffixes["NRM"], self.output_dir, f"{out_name}_normal")

                if has_rmah or has_ormh:
                    src = suffixes.get("RMAH") or suffixes.get("ORMH")
                    is_orm = "ORMH" in suffixes
                    res = unpack_rma(src, self.output_dir, out_name, has_height=True, is_orm=is_orm)
                    if res:
                        slots["rough"] = format_vmat_path(f"{base_rel_path}/{out_name}_rough.tga")
                        slots["metal"] = format_vmat_path(f"{base_rel_path}/{out_name}_metal.tga")
                        slots["ao"] = format_vmat_path(f"{base_rel_path}/{out_name}_ao.tga")
                        slots["height"] = format_vmat_path(f"{base_rel_path}/{out_name}_height.tga")
                elif has_rma or has_orm:
                    src = suffixes.get("RMA") or suffixes.get("ORM")
                    is_orm = "ORM" in suffixes
                    res = unpack_rma(src, self.output_dir, out_name, has_height=False, is_orm=is_orm)
                    if res:
                        slots["rough"] = format_vmat_path(f"{base_rel_path}/{out_name}_rough.tga")
                        slots["metal"] = format_vmat_path(f"{base_rel_path}/{out_name}_metal.tga")
                        slots["ao"] = format_vmat_path(f"{base_rel_path}/{out_name}_ao.tga")
                else:
                    if has_rough:
                        slots["rough"] = format_vmat_path(f"{base_rel_path}/{out_name}_rough.tga")
                        convert_to_tga(suffixes["ROUGH"], self.output_dir, f"{out_name}_rough")
                    if has_metal:
                        slots["metal"] = format_vmat_path(f"{base_rel_path}/{out_name}_metal.tga")
                        convert_to_tga(suffixes["METAL"], self.output_dir, f"{out_name}_metal")
                    if has_ao:
                        slots["ao"] = format_vmat_path(f"{base_rel_path}/{out_name}_ao.tga")
                        convert_to_tga(suffixes["AO"], self.output_dir, f"{out_name}_ao")
                    if has_height:
                        slots["height"] = format_vmat_path(f"{base_rel_path}/{out_name}_height.tga")
                        convert_to_tga(suffixes["HEIGHT"], self.output_dir, f"{out_name}_height")
                
                if slots.get("metal"):
                    metal_local_path = os.path.join(self.output_dir, f"{out_name}_metal.tga")
                    if not is_metallic(metal_local_path):
                        slots["metal"] = None

                vmat_name = f"{out_name}.vmat"
                vmat_path = os.path.join(self.output_dir, vmat_name)
                write_vmat(vmat_path, slots)
                
                created.append(base_name)
                self.file_done.emit(base_name, True, "Success")
            except Exception as e:
                skipped.append((base_name, str(e)))
                self.file_done.emit(base_name, False, str(e))
                
        self.finished.emit(created, skipped)


UE2SourceWorker = MaterialConvertWorker
