import os
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from PySide6.QtCore import QThread, Signal

from gui.settings.common import get_cs2_path, get_addon_name, get_addon_dir
from gui.editors.assetgroup_maker.matcher import match_folder_assets, AssetGroupItem
from gui.editors.assetgroup_maker.analyzer import (
    analyze_reference_file, resolve_reference_full_path, get_addon_root_from_path
)
from gui.editors.assetgroup_maker.objects import load_hbat_file, get_default_file


class StartProcess(QThread):
    finished = Signal()

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath
        self.stop_thread = False

    def run(self):
        try:
            if not self.filepath or not os.path.isfile(self.filepath):
                return

            data = load_hbat_file(self.filepath)
            perform_batch_processing(
                file_path=self.filepath,
                config_data=data
            )
            self.finished.emit()
        except Exception as e:
            pass

    def stop(self):
        self.stop_thread = True
        self.quit()
        self.wait()


def render_asset_template(
    content_template: str,
    asset_item: AssetGroupItem,
    relative_batch_path: str,
    replacements: Optional[List[Dict[str, str]]] = None,
    skipped_slots: Optional[List[str]] = None,
    material_remaps: Optional[List[Dict[str, str]]] = None,
    batch_directory: Optional[str] = None
) -> str:
    data = content_template
    if skipped_slots is None:
        skipped_slots = []

    # 1. Apply user replacement rules if any
    if replacements:
        if isinstance(replacements, list):
            for rep in replacements:
                if isinstance(rep, dict):
                    old_str = rep.get('from', '')
                    new_str = rep.get('to', '')
                    if old_str:
                        data = data.replace(old_str, new_str)
        elif isinstance(replacements, dict):
            for _, rep_info in replacements.items():
                old, new = rep_info.get('replacement', ['', ''])
                if old:
                    data = data.replace(old, new)

    # 2. Base tokens
    data = data.replace("#$FOLDER_PATH$#", relative_batch_path)
    data = data.replace("#$ASSET_NAME$#", asset_item.name)

    # 3. Slot tokens
    for slot_name, slot_path in asset_item.slots.items():
        if slot_name in skipped_slots:
            continue
        slot_filename = os.path.basename(slot_path)
        slot_base, _ = os.path.splitext(slot_filename)
        data = data.replace(f"#${slot_name.upper()}$#", slot_filename)
        data = data.replace(f"#${slot_name.upper()}_NAME$#", slot_base)
        data = data.replace(f"#${slot_name.upper()}_PATH$#", slot_path.replace('\\', '/'))

    # 4. Handle conditional blocks: <!-- IF SLOT --> ... <!-- ENDIF -->
    def evaluate_conditional(match):
        slot_var = match.group(1).strip().lower()
        block_content = match.group(2)
        if slot_var not in skipped_slots and slot_var in asset_item.slots and asset_item.slots[slot_var]:
            return block_content
        return ""

    data = re.sub(r'<!--\s*IF\s+([A-Za-z0-9_]+)\s*-->([\s\S]*?)<!--\s*ENDIF\s*-->', evaluate_conditional, data)

    # 5. Handle MaterialGroup material remaps if present for .vmdl
    if material_remaps:
        # Determine active materials to remap for this specific asset
        mesh_slot_path = asset_item.slots.get('mesh', '')
        mesh_full = None
        if batch_directory and mesh_slot_path:
            mesh_full = os.path.join(batch_directory, os.path.basename(mesh_slot_path))
            if not os.path.isfile(mesh_full):
                mesh_full = mesh_slot_path if os.path.isabs(mesh_slot_path) and os.path.isfile(mesh_slot_path) else None

        active_fbx_materials = []
        if mesh_full and mesh_full.lower().endswith('.fbx') and os.path.isfile(mesh_full):
            from gui.editors.assetgroup_maker.analyzer import extract_fbx_materials
            active_fbx_materials = extract_fbx_materials(mesh_full)

        remap_dict = {}
        for r in material_remaps:
            f_m = r.get('from', '').strip()
            t_m = r.get('to', '').strip()
            if f_m:
                remap_dict[f_m.lower()] = t_m
                if f_m.lower().endswith('.vmat'):
                    remap_dict[f_m[:-5].lower()] = t_m

        remap_entries = []
        seen_remap_from = set()

        if active_fbx_materials:
            for f_mat in active_fbx_materials:
                f_vmat = f_mat if f_mat.lower().endswith('.vmat') else f"{f_mat}.vmat"
                if f_vmat.lower() in seen_remap_from:
                    continue
                seen_remap_from.add(f_vmat.lower())
                t_mat = remap_dict.get(f_vmat.lower(), remap_dict.get(f_mat.lower(), ""))
                if t_mat:
                    t_mat_clean = t_mat.replace('\\', '/')
                    remap_entries.append(f'\t\t\t\t\t\t\t{{\n\t\t\t\t\t\t\t\tfrom = "{f_vmat}"\n\t\t\t\t\t\t\t\tto = "{t_mat_clean}"\n\t\t\t\t\t\t\t}},')
        else:
            for r in material_remaps:
                f_m = r.get('from', '').strip()
                t_m = r.get('to', '').strip()
                if f_m and t_m:
                    f_m_vmat = f_m if f_m.lower().endswith('.vmat') else f"{f_m}.vmat"
                    if f_m_vmat.lower() in seen_remap_from:
                        continue
                    seen_remap_from.add(f_m_vmat.lower())
                    t_m_clean = t_m.replace('\\', '/')
                    remap_entries.append(f'\t\t\t\t\t\t\t{{\n\t\t\t\t\t\t\t\tfrom = "{f_m_vmat}"\n\t\t\t\t\t\t\t\tto = "{t_m_clean}"\n\t\t\t\t\t\t\t}},')

        if remap_entries:
            remaps_block = "remaps = \n\t\t\t\t\t\t[\n" + "\n".join(remap_entries) + "\n\t\t\t\t\t\t]"
            if re.search(r'remaps\s*=\s*\[[\s\S]*?\]', data):
                data = re.sub(r'remaps\s*=\s*\[[\s\S]*?\]', remaps_block, data)
            if 'use_global_default = true' in data:
                data = data.replace('use_global_default = true', 'use_global_default = false')

    return data


DEFAULT_TEMPLATES = {
    'vmdl': """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc41:version{12fc9d44-453a-4ae4-b4d9-7e2ac0bbd4e0} -->
{
\trootNode = 
\t{
\t\t_class = "RootNode"
\t\tchildren = 
\t\t[
\t\t\t{
\t\t\t\t_class = "MaterialGroupList"
\t\t\t\tchildren = 
\t\t\t\t[
\t\t\t\t\t{
\t\t\t\t\t\t_class = "DefaultMaterialGroup"
\t\t\t\t\t\tname = ""
\t\t\t\t\t\tremaps = [  ]
\t\t\t\t\t\tuse_global_default = true
\t\t\t\t\t\tglobal_default_material = "materials/dev/reflectivity_20b.vmat"
\t\t\t\t\t},
\t\t\t\t]
\t\t\t},
\t\t\t{
\t\t\t\t_class = "RenderMeshList"
\t\t\t\tchildren = 
\t\t\t\t[
\t\t\t\t\t{
\t\t\t\t\t\t_class = "RenderMeshFile"
\t\t\t\t\t\tname = "#$ASSET_NAME$#"
\t\t\t\t\t\tfilename = "#$FOLDER_PATH$#/#$MESH$#"
\t\t\t\t\t\timport_scale = 1.0
\t\t\t\t\t\timport_filter = 
\t\t\t\t\t\t{
\t\t\t\t\t\t\texclude_by_default = false
\t\t\t\t\t\t\texception_list = [  ]
\t\t\t\t\t\t}
\t\t\t\t\t},
\t\t\t\t]
\t\t\t},
<!-- IF COLLISION -->
\t\t\t{
\t\t\t\t_class = "PhysicsShapeList"
\t\t\t\tchildren = 
\t\t\t\t[
\t\t\t\t\t{
\t\t\t\t\t\t_class = "PhysicsHullFile"
\t\t\t\t\t\tname = "#$ASSET_NAME$#"
\t\t\t\t\t\tparent_bone = ""
\t\t\t\t\t\tsurface_prop = "default"
\t\t\t\t\t\tcollision_prop = "default"
\t\t\t\t\t\ttool_material = ""
\t\t\t\t\t\trecenter_on_parent_bone = false
\t\t\t\t\t\toffset_origin = [ 0.0, 0.0, 0.0 ]
\t\t\t\t\t\toffset_angles = [ 0.0, 0.0, 0.0 ]
\t\t\t\t\t\tfilename = "#$FOLDER_PATH$#/#$COLLISION$#"
\t\t\t\t\t\timport_scale = 1.0
\t\t\t\t\t\tfaceMergeAngle = 5.0
\t\t\t\t\t\tmaxHullVertices = 24
\t\t\t\t\t\timport_mode = "HullPerElement"
\t\t\t\t\t\tsmall_element_threshold = 0.0
\t\t\t\t\t\tthin_element_threshold = 0.0
\t\t\t\t\t\toptimization_algorithm = "QEM"
\t\t\t\t\t\timport_filter = 
\t\t\t\t\t\t{
\t\t\t\t\t\t\texclude_by_default = false
\t\t\t\t\t\t\texception_list = [  ]
\t\t\t\t\t\t}
\t\t\t\t\t},
\t\t\t\t]
\t\t\t\tleave_body_collision_unmodified = false
\t\t\t},
<!-- ENDIF -->
\t\t]
\t\tmodel_archetype = ""
\t\tprimary_associated_entity = ""
\t\tanim_graph_name = ""
\t\tdocument_sub_type = "ModelDocSubType_None"
\t}
}
""",
    'vmat': """// THIS FILE IS AUTO-GENERATED

Layer0
{
\tshader "csgo_environment.vfx"

\t//---- Color ----
\tg_flModelTintAmount "1.000"
\tg_nScaleTexCoordUByModelScaleAxis "0"
\tg_nScaleTexCoordVByModelScaleAxis "0"
\tg_vColorTint "[1.000000 1.000000 1.000000 0.000000]"

\t//---- Fog ----
\tg_bFogEnabled "1"

\t//---- Material1 ----
\tg_bSnowLayer1 "0"
\tg_flTexCoordRotation1 "0.000"
\tg_flWetnessDarkeningStrength1 "1.000"
\tg_nUVSet1 "1"
\tg_vTexCoordCenter1 "[0.500 0.500]"
\tg_vTexCoordOffset1 "[0.000 0.000]"
\tg_vTexCoordScale1 "[1.000 1.000]"
<!-- IF AO -->
\tTextureAmbientOcclusion1 "#$FOLDER_PATH$#/#$AO$#"
<!-- ENDIF -->
<!-- IF COLOR -->
\tTextureColor1 "#$FOLDER_PATH$#/#$COLOR$#"
<!-- ENDIF -->
<!-- IF METALNESS -->
\tTextureMetalness1 "#$FOLDER_PATH$#/#$METALNESS$#"
<!-- ENDIF -->
<!-- IF NORMAL -->
\tTextureNormal1 "#$FOLDER_PATH$#/#$NORMAL$#"
<!-- ENDIF -->
<!-- IF ROUGHNESS -->
\tTextureRoughness1 "#$FOLDER_PATH$#/#$ROUGHNESS$#"
<!-- ENDIF -->
<!-- IF TINTMASK -->
\tTextureTintMask1 "#$FOLDER_PATH$#/#$TINTMASK$#"
<!-- ENDIF -->

\t//---- Texture Address Mode ----
\tg_nTextureAddressModeU "0"
\tg_nTextureAddressModeV "0"
}
""",
    'vsndevts': """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
\t"#$ASSET_NAME$#" = 
\t{
\t\ttype = "csgo_mega"
\t\tvsnd_files = 
\t\t[
\t\t\t"#$FOLDER_PATH$#/#$SOUND$#",
\t\t]
\t}
}
""",
    'vsmart': """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
\t_class = "CSmartPropRoot"
\tm_Variables = [  ]
\tm_Children = 
\t[
\t\t{
\t\t\t_class = "CSmartPropElement_Model"
\t\t\tm_sModelName = "#$FOLDER_PATH$#/#$ASSET_NAME$#.vmdl"
\t\t},
\t]
}
"""
}


def perform_batch_processing(
    file_path: str,
    config_data: Optional[Dict[str, Any]] = None,
    process: Optional[Dict] = None,
    preview: bool = False,
    replacements: Optional[Dict] = None,
    content_template: Optional[str] = None
) -> List[str]:
    """
    Executes batch asset generation across all templates configured in config_data.
    Supports both v3 multi-template configs and legacy process configs.
    """
    addon_dir = get_addon_dir()
    addon_root = get_addon_root_from_path(file_path) or addon_dir
    cs2_path = get_cs2_path()
    addon_name = get_addon_name()

    if addon_root:
        base_directory = addon_root
    elif cs2_path and addon_name:
        base_directory = os.path.join(cs2_path, 'content', 'csgo_addons', addon_name)
    else:
        base_directory = os.path.dirname(file_path) if file_path else os.getcwd()

    # Determine batch directory
    subfolder = os.path.splitext(file_path)[0] if file_path else ""
    if subfolder and os.path.isdir(subfolder):
        batch_directory = subfolder
    elif file_path and os.path.isdir(os.path.dirname(file_path)):
        batch_directory = os.path.dirname(file_path)
    else:
        batch_directory = base_directory

    try:
        relative_batch_path = os.path.relpath(batch_directory, base_directory).replace('\\', '/')
    except ValueError:
        relative_batch_path = batch_directory.replace('\\', '/')

    # If config_data not passed, try loading from file or build from legacy args
    if not config_data:
        if file_path and os.path.isfile(file_path):
            config_data = load_hbat_file(file_path)
        elif process:
            config_data = {
                'version': 3,
                'settings': process,
                'templates': [{
                    'id': 'template_0',
                    'extension': process.get('extension', 'vmdl'),
                    'reference': process.get('reference', ''),
                    'replacements': replacements or []
                }]
            }
        else:
            config_data = get_default_file()

    settings = config_data.get('settings', {})
    templates = config_data.get('templates', [])
    if not templates:
        templates = [{'id': 'template_0', 'extension': 'vmdl', 'reference': '', 'replacements': []}]

    ignore_extensions = settings.get('ignore_extensions', '')
    ignore_list = settings.get('ignore_list', '')
    algorithm = int(settings.get('algorithm', 0))
    custom_output_rel = settings.get('custom_output', '').strip()

    # Output directory
    if custom_output_rel and custom_output_rel.lower() != 'relative_path':
        output_directory = os.path.join(base_directory, custom_output_rel) if (base_directory and not os.path.isabs(custom_output_rel)) else custom_output_rel
    else:
        output_directory = batch_directory

    if not os.path.isdir(output_directory):
        try:
            os.makedirs(output_directory, exist_ok=True)
        except Exception as e:
            return []

    created_files: List[str] = []

    for template_info in templates:
        ext = template_info.get('extension', 'vmdl').lower().lstrip('.')
        ref_path = template_info.get('reference', '')
        rep_list = template_info.get('replacements', [])

        ref_full = resolve_reference_full_path(ref_path, context_folder=batch_directory)
        analysis = analyze_reference_file(ref_path, context_folder=batch_directory) if ref_path else None

        # Determine template parameterized content
        tpl_content = content_template
        if not tpl_content:
            if analysis and analysis.template_content:
                tpl_content = analysis.template_content
            elif ref_full and os.path.isfile(ref_full):
                try:
                    with open(ref_full, 'r', encoding='utf-8', errors='replace') as f:
                        tpl_content = f.read()
                except Exception as e:
                    tpl_content = None

        if not tpl_content:
            tpl_content = DEFAULT_TEMPLATES.get(ext, "")

        if not tpl_content:
            continue

        slots_def = analysis.slots if analysis else {}
        if not slots_def:
            if ext == 'vmat':
                slots_def = {'color': {'required': True}}
            else:
                slots_def = {'mesh': {'required': True}}

        tpl_filter_mode = template_info.get('filter_mode') or settings.get('filter_mode', 'exclude')
        tpl_ignore_exts = template_info.get('ignore_extensions')
        if tpl_ignore_exts is None or tpl_ignore_exts == '':
            if tpl_filter_mode == settings.get('filter_mode', 'exclude'):
                tpl_ignore_exts = ignore_extensions
            else:
                tpl_ignore_exts = ''

        tpl_ignore_list = template_info.get('ignore_list')
        if tpl_ignore_list is None or tpl_ignore_list == '':
            tpl_ignore_list = ignore_list

        tpl_skipped_slots = template_info.get('skipped_slots') or []
        tpl_material_remaps = template_info.get('material_remaps')
        if tpl_material_remaps is None and analysis and getattr(analysis, 'material_remaps', None):
            tpl_material_remaps = analysis.material_remaps

        asset_items = match_folder_assets(
            directory=batch_directory,
            slots=slots_def,
            extension=ext,
            ignore_extensions_str=tpl_ignore_exts,
            ignore_list_str=tpl_ignore_list,
            filter_mode=tpl_filter_mode,
            skipped_slots=tpl_skipped_slots,
            algorithm=algorithm,
            template_id=template_info.get('id', 'template_0')
        )

        for item in asset_items:
            output_file_path = os.path.join(output_directory, f"{item.name}.{ext}")

            # Exclude reference file if it already exists on disk in the same output directory
            if ref_full and os.path.isfile(ref_full):
                try:
                    ref_norm = os.path.normpath(os.path.abspath(ref_full)).lower()
                    out_norm = os.path.normpath(os.path.abspath(output_file_path)).lower()
                    if ref_norm == out_norm:
                        continue
                except Exception:
                    pass

            rendered_data = render_asset_template(
                content_template=tpl_content,
                asset_item=item,
                relative_batch_path=relative_batch_path,
                replacements=rep_list,
                skipped_slots=tpl_skipped_slots,
                material_remaps=tpl_material_remaps,
                batch_directory=batch_directory
            )

            try:
                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    f.write(rendered_data)
                created_files.append(output_file_path)
            except Exception as e:
                pass

    return created_files