import os
import re
from PySide6.QtCore import QThread, Signal
from .texture_utils import unpack_rma, convert_to_tga, is_metallic
from .vmat_writer import write_vmat

def scan_and_group(input_dir):
    """
    Scans a directory for PNG files and groups them by base name.
    """
    groups = {}
    if not os.path.exists(input_dir):
        return groups

    for file in os.listdir(input_dir):
        if not file.lower().endswith(".png"):
            continue
        
        # Skip certain prefixes as suggested
        if file.startswith(("LUT_", "RVT_", "T_")):
            continue

        # Strip suffix after last underscore
        parts = file.rsplit("_", 1)
        if len(parts) < 2:
            continue
            
        base_name = parts[0]
        suffix = parts[1].split(".")[0].upper()
        
        if base_name not in groups:
            groups[base_name] = {}
        
        groups[base_name][suffix] = os.path.join(input_dir, file)
        
    return groups

class UE2SourceWorker(QThread):
    progress = Signal(int, int)          # current, total
    file_done = Signal(str, bool, str)   # name, success, message
    finished = Signal(list, list)        # created, skipped

    def __init__(self, input_dir, output_dir, materials_relative_path, selected_groups, parent=None):
        super().__init__(parent)
        self.input_dir = input_dir
        self.output_dir = output_dir
        # Ensure materials_path is clean
        self.materials_path = materials_relative_path.replace("\\", "/").strip("/")
        self.selected_groups = selected_groups # Dict of base_name -> files

    def run(self):
        total = len(self.selected_groups)
        created, skipped = [], []
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Determine the base path inside the VMAT
        # If the input starts with materials/, use it as is, otherwise prefix it.
        if self.materials_path.lower().startswith("materials/"):
            base_rel_path = self.materials_path
        else:
            base_rel_path = f"materials/{self.materials_path}"
        
        # Source 2 usually expects lowercase paths in VMATs
        base_rel_path = base_rel_path.lower()

        for i, (base_name, suffixes) in enumerate(self.selected_groups.items()):
            self.progress.emit(i + 1, total)
            # Use lowercase for all output files and internal VMAT paths
            out_name = base_name.lower()
            
            try:
                # 1. Determine what we have
                has_rma = "RMA" in suffixes
                has_rmah = "RMAH" in suffixes
                has_alb = "ALB" in suffixes
                has_nrm = "NRM" in suffixes
                has_rgba = "RGBA" in suffixes
                
                if has_rgba:
                    self.file_done.emit(base_name, False, "RGBA texture detected. Skipping (unsupported custom packed mask).")
                    skipped.append((base_name, "RGBA unsupported"))
                    continue

                if not has_alb and not has_nrm:
                    raise Exception("Missing both ALB and NRM textures")

                slots = {}
                
                # Source 2 usually expects lowercase, forward slash paths relative to materials/
                def format_vmat_path(path):
                    return path.lower().replace("\\", "/")

                # 2. Process textures
                if has_alb:
                    slots["color"] = format_vmat_path(f"{base_rel_path}/{out_name}_color.tga")
                    convert_to_tga(suffixes["ALB"], self.output_dir, f"{out_name}_color")
                
                if has_nrm:
                    slots["normal"] = format_vmat_path(f"{base_rel_path}/{out_name}_normal.tga")
                    convert_to_tga(suffixes["NRM"], self.output_dir, f"{out_name}_normal")
                
                if has_rmah:
                    res = unpack_rma(suffixes["RMAH"], self.output_dir, out_name, has_height=True)
                    if res:
                        slots["rough"] = format_vmat_path(f"{base_rel_path}/{out_name}_rough.tga")
                        slots["metal"] = format_vmat_path(f"{base_rel_path}/{out_name}_metal.tga")
                        slots["ao"] = format_vmat_path(f"{base_rel_path}/{out_name}_ao.tga")
                        slots["height"] = format_vmat_path(f"{base_rel_path}/{out_name}_height.tga")
                elif has_rma:
                    res = unpack_rma(suffixes["RMA"], self.output_dir, out_name, has_height=False)
                    if res:
                        slots["rough"] = format_vmat_path(f"{base_rel_path}/{out_name}_rough.tga")
                        slots["metal"] = format_vmat_path(f"{base_rel_path}/{out_name}_metal.tga")
                        slots["ao"] = format_vmat_path(f"{base_rel_path}/{out_name}_ao.tga")
                
                # 3. Metalness heuristic
                if slots.get("metal"):
                    metal_local_path = os.path.join(self.output_dir, f"{out_name}_metal.tga")
                    if not is_metallic(metal_local_path):
                        slots["metal"] = None # Will result in inline zero vector
                
                # 4. Write VMAT
                vmat_name = f"{out_name}.vmat"
                vmat_path = os.path.join(self.output_dir, vmat_name)
                write_vmat(vmat_path, slots)
                
                created.append(base_name)
                self.file_done.emit(base_name, True, "Success")
            except Exception as e:
                skipped.append((base_name, str(e)))
                self.file_done.emit(base_name, False, str(e))
                
        self.finished.emit(created, skipped)
