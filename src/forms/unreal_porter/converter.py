import os
import re
from PySide6.QtCore import QThread, Signal
from ._worker_base import CancellableWorker
from .texture_utils import unpack_rma, convert_to_tga, is_metallic, unpack_orh
from .vmat_writer import write_vmat
from .bridge_client import UnrealBridge, BridgeError
from .material_converter import strip_ue_asset_folders
from .vmdl_writer import strip_ue_prefix

_SUFFIX_MAP = {
    "ALB": "ALB", "BC": "ALB", "D": "ALB", "COLOR": "ALB", "DIFFUSE": "ALB", "BASECOLOR": "ALB", "ALBEDO": "ALB", "C": "ALB", "B": "ALB", "A": "ALB",
    "NRM": "NRM", "N": "NRM", "NORMAL": "NRM", "NORM": "NRM",
    "RMA": "RMA", "ORM": "ORM", "MASK": "RMA", "PACKED": "RMA",
    "RMAH": "RMAH", "ORMH": "ORMH", "ORH": "ORH",
    "ROUGH": "ROUGH", "R": "ROUGH", "ROUGHNESS": "ROUGH",
    "METAL": "METAL", "M": "METAL", "METALLIC": "METAL", "MET": "METAL",
    "AO": "AO", "OCCLUSION": "AO",
    "HEIGHT": "HEIGHT", "H": "HEIGHT", "DISP": "HEIGHT", "DISPLACEMENT": "HEIGHT",
}

def scan_and_group(input_dir):
    """
    Scans a directory recursively for image files (PNG, TGA, JPG, JPEG) and groups them by base name.
    """
    groups = {}
    if not os.path.exists(input_dir):
        return groups

    valid_exts = (".png", ".tga", ".jpg", ".jpeg")
    for root, _dirs, files in os.walk(input_dir):
        for file in files:
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
            
            groups[base_name][canonical_suffix] = os.path.join(root, file)
            
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
            out_name = strip_ue_prefix(base_name).strip("_")
            if not out_name:
                out_name = base_name.lower()
            
            sample_file = next(iter(suffixes.values())) if suffixes else ""
            rel_sub = os.path.dirname(os.path.relpath(sample_file, self.input_dir)).replace("\\", "/").lower() if sample_file else ""
            if rel_sub and rel_sub != ".":
                # Drop UE asset-type folders (Game, Textures, Materials, …) —
                # Source 2 keeps a material and its textures flat in one folder,
                # it doesn't mirror UE's per-asset-type subfolder layout.
                rel_sub = strip_ue_asset_folders(rel_sub)
                item_rel_path = f"materials/{rel_sub}" if rel_sub else base_rel_path
            else:
                item_rel_path = base_rel_path

            dest_dir = os.path.join(self.output_dir, item_rel_path)
            os.makedirs(dest_dir, exist_ok=True)
            
            try:
                has_rma = "RMA" in suffixes
                has_orm = "ORM" in suffixes
                has_rmah = "RMAH" in suffixes
                has_ormh = "ORMH" in suffixes
                has_orh = "ORH" in suffixes
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

                if not has_alb and not has_nrm and not has_rough and not has_rma and not has_orm and not has_orh:
                    raise Exception("Missing identifiable color/normal/mask textures")

                slots = {}
                
                def format_vmat_path(path):
                    return path.lower().replace("\\", "/")

                if has_alb:
                    slots["color"] = format_vmat_path(f"{item_rel_path}/{out_name}_color.tga")
                    convert_to_tga(suffixes["ALB"], dest_dir, f"{out_name}_color")
                
                if has_nrm:
                    slots["normal"] = format_vmat_path(f"{item_rel_path}/{out_name}_normal.tga")
                    convert_to_tga(suffixes["NRM"], dest_dir, f"{out_name}_normal")

                if has_rmah or has_ormh:
                    src = suffixes.get("RMAH") or suffixes.get("ORMH")
                    is_orm = "ORMH" in suffixes
                    res = unpack_rma(src, dest_dir, out_name, has_height=True, is_orm=is_orm)
                    if res:
                        slots["rough"] = format_vmat_path(f"{item_rel_path}/{out_name}_rough.tga")
                        slots["metal"] = format_vmat_path(f"{item_rel_path}/{out_name}_metal.tga")
                        slots["ao"] = format_vmat_path(f"{item_rel_path}/{out_name}_ao.tga")
                        slots["height"] = format_vmat_path(f"{item_rel_path}/{out_name}_height.tga")
                elif has_rma or has_orm:
                    src = suffixes.get("RMA") or suffixes.get("ORM")
                    is_orm = "ORM" in suffixes
                    res = unpack_rma(src, dest_dir, out_name, has_height=False, is_orm=is_orm)
                    if res:
                        slots["rough"] = format_vmat_path(f"{item_rel_path}/{out_name}_rough.tga")
                        slots["metal"] = format_vmat_path(f"{item_rel_path}/{out_name}_metal.tga")
                        slots["ao"] = format_vmat_path(f"{item_rel_path}/{out_name}_ao.tga")
                elif has_orh:
                    src = suffixes.get("ORH")
                    res = unpack_orh(src, dest_dir, out_name)
                    if res:
                        slots["rough"] = format_vmat_path(f"{item_rel_path}/{out_name}_rough.tga")
                        slots["ao"] = format_vmat_path(f"{item_rel_path}/{out_name}_ao.tga")
                        slots["height"] = format_vmat_path(f"{item_rel_path}/{out_name}_height.tga")
                else:
                    if has_rough:
                        slots["rough"] = format_vmat_path(f"{item_rel_path}/{out_name}_rough.tga")
                        convert_to_tga(suffixes["ROUGH"], dest_dir, f"{out_name}_rough")
                    if has_metal:
                        slots["metal"] = format_vmat_path(f"{item_rel_path}/{out_name}_metal.tga")
                        convert_to_tga(suffixes["METAL"], dest_dir, f"{out_name}_metal")
                    if has_ao:
                        slots["ao"] = format_vmat_path(f"{item_rel_path}/{out_name}_ao.tga")
                        convert_to_tga(suffixes["AO"], dest_dir, f"{out_name}_ao")
                    if has_height:
                        slots["height"] = format_vmat_path(f"{item_rel_path}/{out_name}_height.tga")
                        convert_to_tga(suffixes["HEIGHT"], dest_dir, f"{out_name}_height")
                
                if slots.get("metal"):
                    metal_local_path = os.path.join(dest_dir, f"{out_name}_metal.tga")
                    if not is_metallic(metal_local_path):
                        slots["metal"] = None

                vmat_name = f"{out_name}.vmat"
                vmat_path = os.path.join(dest_dir, vmat_name)
                write_vmat(vmat_path, slots)
                
                created.append(base_name)
                missing = []
                if "color" not in slots:
                    missing.append("color")
                if "normal" not in slots:
                    missing.append("normal")
                if "rough" not in slots:
                    missing.append("roughness")
                if "metal" not in slots:
                    missing.append("metalness")
                if "ao" not in slots:
                    missing.append("ao")
                
                msg = "Success"
                if missing:
                    msg += f" (missing: {', '.join(missing)})"
                self.file_done.emit(base_name, True, msg)
            except Exception as e:
                skipped.append((base_name, str(e)))
                self.file_done.emit(base_name, False, str(e))
                
        self.finished.emit(created, skipped)


# The one shader used when nothing else is known. Not a guess about the
# material — just a definite, stated default.
FALLBACK_SHADER = "csgo_environment.vfx"


def seed_shader_for(master_name: str, mat_flags: dict = None) -> str:
    """The shader a *newly discovered* Master Material starts out mapped to.

    SEEDING ONLY. This runs once, when a master is first seen, to fill in its
    entry in the saved shader remap table — which is then written to
    shader_swap.kv3, shown in the Materials tab, and editable. Conversion never
    calls this: it reads the saved table and nothing else, so the shader a
    material converts with is always one that is written down and visible.

    Guessing at conversion time is what this replaced; a material silently
    converting with a shader nobody chose is indistinguishable from a remap
    being ignored, and cost a long time to track down.
    """
    name_lower = master_name.lower()
    flags = mat_flags or {}
    domain = flags.get("domain", "")

    if domain == "MD_DeferredDecal" or "decal" in name_lower or "overlay" in name_lower:
        return "csgo_static_overlay.vfx"
    if any(k in name_lower for k in ("foliage", "leaf", "leaves", "grass", "tree", "plant", "vegetation", "bark")):
        return "csgo_foliage.vfx"
    if any(k in name_lower for k in ("glass", "window", "translucent", "transparent")):
        return "csgo_glass.vfx"
    if any(k in name_lower for k in ("character", "skin", "hero")):
        return "csgo_character.vfx"
    return FALLBACK_SHADER


def get_master_material_name(mat_data: dict, mat_key: str = "") -> str:
    """Extract clean Master Material name from dump_material data or mat_key."""
    parent = (mat_data or {}).get("parent")
    if parent:
        base = os.path.basename(parent).split(".", 1)[0]
        if base and base.lower() not in ("material", "materialinstanceconstant"):
            return base
    if mat_key:
        return os.path.basename(mat_key).split(".", 1)[0]
    mat_path = (mat_data or {}).get("material", "")
    if mat_path:
        return os.path.basename(mat_path).split(".", 1)[0]
    return "M_Master_Default"


def save_material_swaps_kv3(output_dir: str, swaps: dict, slot_mappings: dict = None,
                            param_mappings: dict = None, feature_flags: dict = None,
                            blend_modes: dict = None):
    """Saves Master Material -> CS2 Shader swaps, slot mappings, param
    mappings, feature flags, and blend modes into hammer5tools/unrealporter/shader_swap.kv3 in output_dir."""
    if not output_dir or not os.path.isdir(output_dir):
        return
    file_path = os.path.join(output_dir, "hammer5tools", "unrealporter", "shader_swap.kv3")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    lines = [
        "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->",
        "{",
        "\tmaster_material_shader_swaps = ",
        "\t{",
    ]
    for master_name, shader_name in sorted(swaps.items()):
        lines.append(f'\t\t"{master_name}" = "{shader_name}"')
    lines.append("\t}")

    import json
    if slot_mappings:
        lines.append("\tmaster_material_slot_mappings = ")
        lines.append("\t{")
        for master_name, mappings in sorted(slot_mappings.items()):
            if not mappings:
                continue
            lines.append(f'\t\t"{master_name}" = ')
            lines.append("\t\t{")
            for param, slot in sorted(mappings.items()):
                if slot is None:
                    slot_str = "null"
                elif isinstance(slot, (dict, list)):
                    slot_str = json.dumps(json.dumps(slot))
                else:
                    slot_str = f'"{slot}"'
                lines.append(f'\t\t\t"{param}" = {slot_str}')
            lines.append("\t\t}")
        lines.append("\t}")

    if param_mappings:
        lines.append("\tmaster_material_param_mappings = ")
        lines.append("\t{")
        for master_name, mappings in sorted(param_mappings.items()):
            if not mappings:
                continue
            lines.append(f'\t\t"{master_name}" = ')
            lines.append("\t\t{")
            for param, target in sorted(mappings.items()):
                lines.append(f'\t\t\t"{param}" = "{target}"')
            lines.append("\t\t}")
        lines.append("\t}")

    if feature_flags:
        lines.append("\tmaster_material_feature_flags = ")
        lines.append("\t{")
        for master_name, flags in sorted(feature_flags.items()):
            if not flags:
                continue
            lines.append(f'\t\t"{master_name}" = ')
            lines.append("\t\t{")
            for f_key, f_val in sorted(flags.items()):
                lines.append(f'\t\t\t"{f_key}" = "{f_val}"')
            lines.append("\t\t}")
        lines.append("\t}")

    if blend_modes:
        lines.append("\tmaster_material_blend_modes = ")
        lines.append("\t{")
        for master_name, bm in sorted(blend_modes.items()):
            lines.append(f'\t\t"{master_name}" = {int(bm)}')
        lines.append("\t}")

    lines.append("}")
    lines.append("")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception:
        pass


def load_material_swaps_kv3(output_dir: str) -> tuple:
    """Reads Master Material -> CS2 Shader swaps, slot mappings, param
    mappings, feature flags, and blend modes from hammer5tools/unrealporter/shader_swap.kv3 if it exists.
    Returns: (swaps_dict, slot_mappings_dict, param_mappings_dict, feature_flags_dict, blend_modes_dict)
    """
    swaps, slot_mappings, param_mappings, feature_flags, blend_modes = {}, {}, {}, {}, {}
    if not output_dir:
        return swaps, slot_mappings, param_mappings, feature_flags, blend_modes
    file_path = os.path.join(output_dir, "hammer5tools", "unrealporter", "shader_swap.kv3")
    if not os.path.isfile(file_path):
        legacy_path = os.path.join(output_dir, "hammer5tools_ue_converter_material_swaps.kv3")
        if os.path.isfile(legacy_path):
            file_path = legacy_path
        else:
            return swaps, slot_mappings, param_mappings, feature_flags, blend_modes

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        import re
        section = None
        current_master = None
        for line in lines:
            line_s = line.strip()
            if "master_material_shader_swaps" in line_s:
                section = "shaders"
                continue
            elif "master_material_slot_mappings" in line_s:
                section = "slots"
                continue
            elif "master_material_param_mappings" in line_s:
                section = "params"
                continue
            elif "master_material_feature_flags" in line_s:
                section = "flags"
                continue
            elif "master_material_blend_modes" in line_s:
                section = "blend_modes"
                continue

            if section == "shaders":
                m = re.search(r'"([^"]+)"\s*=\s*"([^"]+)"', line_s)
                if m:
                    swaps[m.group(1)] = m.group(2)
            elif section == "blend_modes":
                m = re.search(r'"([^"]+)"\s*=\s*(\d+)', line_s)
                if m:
                    try:
                        blend_modes[m.group(1)] = int(m.group(2))
                    except ValueError:
                        pass
            elif section in ("slots", "params", "flags"):
                if section == "slots":
                    target = slot_mappings
                elif section == "params":
                    target = param_mappings
                else:
                    target = feature_flags

                m_master = re.search(r'^\s*"([^"]+)"\s*=\s*\{?\s*$', line_s)
                if m_master:
                    current_master = m_master.group(1)
                    if current_master not in target:
                        target[current_master] = {}
                else:
                    m_param = re.search(r'^\s*"([^"]+)"\s*=\s*(.+)$', line_s)
                    if m_param and current_master:
                        param_name = m_param.group(1)
                        raw_val = m_param.group(2).strip().rstrip(",")
                        if raw_val == "null":
                            parsed_val = None
                        else:
                            clean_val = raw_val
                            if clean_val.startswith('"') and clean_val.endswith('"') and len(clean_val) >= 2:
                                clean_val = clean_val[1:-1].replace('\\"', '"').replace("\\\\", "\\")
                            if (clean_val.startswith("{") and clean_val.endswith("}")) or (clean_val.startswith("[") and clean_val.endswith("]")):
                                try:
                                    import json
                                    parsed_val = json.loads(clean_val)
                                except Exception:
                                    try:
                                        import ast
                                        parsed_val = ast.literal_eval(clean_val)
                                    except Exception:
                                        parsed_val = clean_val
                            else:
                                parsed_val = clean_val
                        target[current_master][param_name] = parsed_val
    except Exception:
        pass
    return swaps, slot_mappings, param_mappings, feature_flags, blend_modes


def apply_saved_swaps(groups: dict, output_dir: str) -> dict:
    """Overlay an addon's saved shader / slot / param / feature flag choices onto scanned groups.

    The scan itself is a property of the UE project, so it gets cached in the
    project's analysis manifest. These choices are a property of the *addon*
    being ported into, so they are re-applied on top whenever groups are
    adopted — otherwise switching addon would silently carry the other one's
    shader picks along.
    """
    if not output_dir or not groups:
        return groups
    res = load_material_swaps_kv3(output_dir)
    saved_swaps, saved_slot_mappings, saved_param_mappings = res[0], res[1], res[2]
    saved_feature_flags = res[3] if len(res) > 3 else {}
    saved_blend_modes = res[4] if len(res) > 4 else {}

    for name, info in groups.items():
        if saved_swaps.get(name):
            info["shader"] = saved_swaps[name]
        if saved_slot_mappings.get(name):
            info["slot_overrides"] = saved_slot_mappings[name]
        if saved_param_mappings.get(name):
            info["param_overrides"] = saved_param_mappings[name]
        if saved_feature_flags.get(name):
            info["feature_flags"] = saved_feature_flags[name]
        if saved_blend_modes.get(name):
            info["blend_mode"] = saved_blend_modes[name]
    return groups


def scan_master_materials(project_dir: str, bulk_dir: str = None, bridge=None, output_dir: str = None, log_cb=None, progress_cb=None) -> dict:
    """
    Scans project materials and groups them by Master Material.
    Returns: { master_mat_name: { "shader": predicted_shader, "instances": [(mi_stem, mi_path, mat_data)], "count": N, "textures": {...}, "slot_overrides": {...} } }
    """
    groups = {}
    # Masters that had no saved entry and got one seeded this scan. Reported and
    # persisted below, so the saved table is complete before any conversion runs.
    seeded = {}
    if output_dir:
        res = load_material_swaps_kv3(output_dir)
        saved_swaps, saved_slot_mappings, saved_param_mappings = res[0], res[1], res[2]
        saved_feature_flags = res[3] if len(res) > 3 else {}
        saved_blend_modes = res[4] if len(res) > 4 else {}
    else:
        saved_swaps, saved_slot_mappings, saved_param_mappings = {}, {}, {}
        saved_feature_flags, saved_blend_modes = {}, {}

    if bridge and bridge.is_available():
        try:
            if log_cb:
                log_cb("Listing project material assets via CUE4Parse bridge...", "info")
            mat_keys = bridge.list_materials()
            total = len(mat_keys)
            if log_cb:
                log_cb(f"Found {total} potential material asset(s) under project.", "info")

            for i, key in enumerate(mat_keys):
                if progress_cb:
                    progress_cb(i + 1, total)
                if not key.lower().endswith(".uasset"):
                    continue
                path = key[:-len(".uasset")]
                try:
                    mat_data = bridge.dump_material(path)
                except Exception as e:
                    if log_cb:
                        log_cb(f"  Skipped {os.path.basename(path)}: {e}", "warn")
                    continue

                master_name = get_master_material_name(mat_data, path)
                stem = os.path.basename(path)
                if master_name not in groups:
                    shader = saved_swaps.get(master_name)
                    if not shader:
                        shader = seed_shader_for(master_name, mat_data.get("flags"))
                        seeded[master_name] = shader
                    groups[master_name] = {
                        "shader": shader,
                        "instances": [],
                        "textures": {},
                        "slot_overrides": saved_slot_mappings.get(master_name, {}),
                        "param_overrides": saved_param_mappings.get(master_name, {}),
                        "feature_flags": saved_feature_flags.get(master_name, {}),
                        "blend_mode": saved_blend_modes.get(master_name, 0),
                    }
                    if log_cb:
                        log_cb(f"Discovered Master Material: {master_name} (target CS2 shader: {shader})", "info")

                groups[master_name]["instances"].append((stem, path, mat_data))
                for p_name, p_path in (mat_data.get("textures") or {}).items():
                    if p_name not in groups[master_name]["textures"]:
                        groups[master_name]["textures"][p_name] = p_path
        except Exception as e:
            if log_cb:
                log_cb(f"Bridge material scan failed: {e}", "error")

    if not groups and bulk_dir and os.path.isdir(bulk_dir):
        if log_cb:
            log_cb(f"Scanning bulk export directory for textures: {bulk_dir}", "info")
        raw_groups = scan_and_group(bulk_dir)
        total = len(raw_groups)
        for i, (base_name, suffixes) in enumerate(raw_groups.items()):
            if progress_cb:
                progress_cb(i + 1, total)
            master_name = strip_ue_prefix(base_name)
            master_name = f"M_{master_name.title()}" if master_name else "M_Master"
            if master_name not in groups:
                shader = saved_swaps.get(master_name)
                if not shader:
                    shader = seed_shader_for(master_name)
                    seeded[master_name] = shader
                groups[master_name] = {
                    "shader": shader,
                    "instances": [],
                    "textures": {},
                    "slot_overrides": saved_slot_mappings.get(master_name, {}),
                    "param_overrides": saved_param_mappings.get(master_name, {}),
                    "feature_flags": saved_feature_flags.get(master_name, {}),
                    "blend_mode": saved_blend_modes.get(master_name, 0),
                }
            groups[master_name]["instances"].append((base_name, base_name, {"suffixes": suffixes}))

    for master_name in groups:
        groups[master_name]["count"] = len(groups[master_name]["instances"])

    # Write the seeded entries out now, so from this point the saved table
    # covers every master and conversion never has to invent one. Without this
    # the defaults live only in memory and a master that was never opened in the
    # Materials tab would have no saved shader to convert with.
    if seeded and output_dir:
        save_material_swaps_kv3(
            output_dir,
            {name: info["shader"] for name, info in groups.items()},
            slot_mappings={n: i.get("slot_overrides") or {} for n, i in groups.items()},
            param_mappings={n: i.get("param_overrides") or {} for n, i in groups.items()},
            feature_flags={n: i.get("feature_flags") or {} for n, i in groups.items()},
            blend_modes={n: i.get("blend_mode") or 0 for n, i in groups.items()},
        )
    if log_cb:
        if seeded:
            log_cb(
                f"Shader remapping — {len(seeded)} new Master Material(s) given a starting "
                f"shader and saved to shader_swap.kv3; change any of them in the Materials tab: "
                + ", ".join(f"{n} -> {s}" for n, s in sorted(seeded.items())),
                "info",
            )
        log_cb(f"Material scan complete: {len(groups)} Master Material group(s) discovered.", "success")

    return groups


class MasterMaterialConvertWorker(CancellableWorker):
    progress = Signal(int, int)          # current, total
    file_done = Signal(str, bool, str)   # name, success, message
    finished = Signal(list, list)        # created, skipped

    def __init__(self, output_dir, bulk_dir, master_groups, slot_overrides=None, parent=None,
                 strip_prefix=True, tex_format="tga", invert_y_normal=True):
        super().__init__(parent)
        self.output_dir = output_dir
        self.bulk_dir = bulk_dir
        self.master_groups = master_groups  # { master_name: { "shader": str, "instances": [...], "slot_overrides": {...}, "enabled": bool } }
        self.strip_prefix = strip_prefix
        self.tex_format = tex_format
        self.invert_y_normal = invert_y_normal

    def run(self):
        from .material_converter import convert_material, process_material_textures, get_texture_index

        # Save user shader swaps, slot mappings, and param mappings into KV3 in output_dir
        swaps_to_save = {name: data.get("shader", "csgo_environment.vfx")
                         for name, data in self.master_groups.items() if data.get("enabled", True)}
        slot_mappings_to_save = {name: data.get("slot_overrides", {})
                                 for name, data in self.master_groups.items() if data.get("enabled", True) and data.get("slot_overrides")}
        param_mappings_to_save = {name: data.get("param_overrides", {})
                                  for name, data in self.master_groups.items() if data.get("enabled", True) and data.get("param_overrides")}
        feature_flags_to_save = {name: data.get("feature_flags", {})
                                 for name, data in self.master_groups.items() if data.get("enabled", True) and data.get("feature_flags")}
        blend_modes_to_save = {name: data.get("blend_mode", 0)
                               for name, data in self.master_groups.items() if data.get("enabled", True) and data.get("blend_mode")}
        save_material_swaps_kv3(self.output_dir, swaps_to_save, slot_mappings_to_save, param_mappings_to_save, feature_flags_to_save, blend_modes_to_save)

        tex_index = get_texture_index(self.bulk_dir)
        total_instances = sum(len(g.get("instances", [])) for g in self.master_groups.values() if g.get("enabled", True))
        created, skipped = [], []
        processed = 0

        for master_name, group_data in self.master_groups.items():
            if not group_data.get("enabled", True):
                continue
            shader = group_data.get("shader", "csgo_environment.vfx")
            instances = group_data.get("instances", [])
            master_slot_overrides = group_data.get("slot_overrides", {})
            master_param_overrides = group_data.get("param_overrides", {})
            master_feature_flags = group_data.get("feature_flags", {})
            master_blend_mode = group_data.get("blend_mode", 0)

            for stem, path, mat_data in instances:
                if self.is_cancelled:
                    self.finished.emit(created, skipped)
                    return
                processed += 1
                self.progress.emit(processed, total_instances)
                try:
                    res = convert_material(
                        mat_data, self.bulk_dir, self.output_dir,
                        shader=shader, slot_overrides=master_slot_overrides,
                        tex_index=tex_index, param_overrides=master_param_overrides,
                        strip_prefix=self.strip_prefix,
                        tex_format=self.tex_format,
                        invert_y_normal=self.invert_y_normal,
                        feature_flags=master_feature_flags,
                        blend_mode=master_blend_mode,
                    )
                    created.append(stem)
                    msg = f"Success ({shader})"
                    if getattr(res, "mapped_info", None):
                        msg += f" — mapped: {res.mapped_info}"
                    if res.missing:
                        msg += f" (missing: {', '.join(res.missing)})"
                    self.file_done.emit(stem, True, msg)
                except Exception as e:
                    skipped.append((stem, str(e)))
                    self.file_done.emit(stem, False, str(e))

        self.finished.emit(created, skipped)


UE2SourceWorker = MaterialConvertWorker
