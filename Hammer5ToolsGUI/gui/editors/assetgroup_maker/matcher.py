import os
import re
import fnmatch
from typing import Dict, List, Optional, Set, Tuple, Any
from gui.settings.common import get_addon_dir

from core.bridge import CoreBridge


class AssetGroupItem:
    """Represents a grouped target asset with multiple matched slot files."""

    def __init__(
        self,
        name: str,
        relative_folder: str = "",
        template_id: str = "template_0",
        extension: str = "vmdl",
        template_label: str = ""
    ):
        self.name = name
        self.relative_folder = relative_folder
        self.template_id = template_id
        self.extension = extension
        self.template_label = template_label or f".{extension}"
        self.slots: Dict[str, str] = {}
        self.available_candidates: List[str] = []
        self.status: str = "ready"  # "ready", "warning", "error"
        self.status_message: str = "Ready"
        self.target_output: str = f"{name}.{extension}"

    def get_slot_filename(self, slot_name: str) -> str:
        path = self.slots.get(slot_name, "")
        return os.path.basename(path) if path else ""

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'folder': self.relative_folder,
            'template_id': self.template_id,
            'extension': self.extension,
            'template_label': self.template_label,
            'slots': self.slots,
            'status': self.status,
            'status_message': self.status_message,
            'target_output': self.target_output
        }


def strip_known_affixes(base_name: str, source_extension: str = "") -> str:
    return CoreBridge.instance().normalize_assetgroup_name(base_name, source_extension)


def strip_known_suffix(base_name: str) -> str:
    return strip_known_affixes(base_name)


def parse_filter_entries(filter_str: str) -> List[str]:
    """Parse a comma-separated list of extensions/patterns, handling leading/trailing spaces and stripping dots."""
    if not filter_str:
        return []
    return [e.strip() for e in filter_str.split(',') if e.strip()]


def matches_filter_entry(file_name: str, entry: str) -> bool:
    """
    Checks if a filename matches an entry which can be:
    - An extension: 'vmdl', '.vmdl', 'png', 'fbx'
    - A prefix pattern: 'phys_', 'temp_', 'draft_'
    - A wildcard glob: '*_backup*', 'draft*', '*.png', '*color*'
    - A suffix pattern: '_phys', '_col', '_color'
    - A substring / token in base name or file name (e.g. 'color', 'normal', 'fbx', 'phys')
    """
    fn_lower = file_name.lower().strip()
    entry_lower = entry.lower().strip()
    if not entry_lower:
        return False

    base, ext = os.path.splitext(fn_lower)
    clean_ext = ext.lstrip('.')

    # 1. Exact extension match (e.g. "vmdl", ".vmdl", "png", "fbx")
    if entry_lower == clean_ext or entry_lower == ext or entry_lower.lstrip('.') == clean_ext:
        return True

    # 2. Glob wildcard match (e.g. "*_backup*", "*.fbx", "temp_*", "*color*")
    if '*' in entry_lower or '?' in entry_lower:
        if fnmatch.fnmatch(fn_lower, entry_lower):
            return True

    # 3. Prefix pattern (e.g. "phys_", "temp_", "col_")
    if entry_lower.endswith('_') or entry_lower.endswith('-'):
        if fn_lower.startswith(entry_lower) or base.startswith(entry_lower):
            return True

    # 4. Suffix pattern (e.g. "_phys", "_col", "_color")
    if entry_lower.startswith('_') or entry_lower.startswith('-'):
        if base.endswith(entry_lower):
            return True

    # 5. Base name exact or substring match (e.g. "color", "normal", "phys", "bark")
    if entry_lower == base or entry_lower in base or entry_lower in fn_lower:
        return True

    return False


def is_file_ignored(
    file_name: str,
    ignore_extensions: List[str],
    ignore_patterns: List[str],
    filter_mode: str = "exclude"
) -> bool:
    """
    Determines if a file should be ignored based on entries and filter mode.
    - filter_mode == "exclude": returns True if the file matches any ignore entry.
    - filter_mode == "include": returns True if the file does NOT match any entry.
    """
    all_entries = [e for e in (ignore_extensions + ignore_patterns) if e]
    if not all_entries:
        return False

    matches_any = any(matches_filter_entry(file_name, entry) for entry in all_entries)

    if filter_mode.lower() == "include":
        return not matches_any
    else:
        return matches_any


def match_folder_assets(
    directory: str,
    slots: Dict[str, Dict],
    extension: str = "vmdl",
    ignore_extensions_str: str = "",
    ignore_list_str: str = "",
    filter_mode: str = "exclude",
    skipped_slots: Optional[List[str]] = None,
    algorithm: int = 0,
    template_id: str = "template_0",
    template_label: str = ""
) -> List[AssetGroupItem]:
    ignore_extensions = parse_filter_entries(ignore_extensions_str)
    ignore_patterns = parse_filter_entries(ignore_list_str)
    if skipped_slots is None:
        skipped_slots = []

    addon_dir = get_addon_dir()
    rel_folder = directory
    if addon_dir and os.path.isabs(directory):
        try:
            rel_folder = os.path.relpath(directory, addon_dir).replace('\\', '/')
        except ValueError:
            rel_folder = directory.replace('\\', '/')

    if not os.path.isdir(directory):
        return []

    ext_norm = extension.lower().strip('.')

    # Collect folder candidates for slot browsing
    folder_candidates: List[str] = []
    for root, _, files in os.walk(directory):
        for f in files:
            folder_candidates.append(os.path.join(root, f))

    # Strict source file extensions per template type
    valid_source_exts = {
        'vmdl': {'fbx', 'obj', 'dmx', 'smd'},
        'vmat': {'tga', 'png', 'jpg', 'jpeg', 'exr', 'hdr', 'psd', 'tif', 'tiff'},
        'vsndevts': {'wav', 'mp3', 'ogg', 'flac'},
        'vsmart': {'vmdl', 'vsmart', 'fbx'},
    }.get(ext_norm, None)

    relevant_files: List[Tuple[str, str]] = []
    for root, _, files in os.walk(directory):
        for f in files:
            full_p = os.path.join(root, f)
            _, f_ext = os.path.splitext(f)
            clean_f_ext = f_ext.lstrip('.').lower()

            # Enforce valid extension for this template type
            if valid_source_exts is not None and clean_f_ext not in valid_source_exts:
                continue

            # Always exclude files matching ignore patterns (e.g. temp_*, draft_*, *backup*, .git*)
            if ignore_patterns:
                if any(matches_filter_entry(f, p) for p in ignore_patterns):
                    continue

            # In exclude mode, also discard files matching ignore_extensions
            if filter_mode == "exclude" and ignore_extensions:
                if any(matches_filter_entry(f, e) for e in ignore_extensions):
                    continue

            relevant_files.append((f, full_p))

    # If no valid source files exist for this template type, return empty results
    if not relevant_files:
        return []

    # Group source files by asset root name
    asset_groups: Dict[str, List[Tuple[str, str]]] = {}
    for fname, fpath in relevant_files:
        base, source_extension = os.path.splitext(fname)
        root_name = CoreBridge.instance().normalize_assetgroup_name(base, source_extension, algorithm)

        if not root_name:
            root_name = base

        asset_groups.setdefault(root_name, []).append((fname, fpath))

    # In include mode, keep groups where either the group name or at least one companion file matches an include entry
    if filter_mode == "include" and ignore_extensions:
        filtered_groups = {}
        for group_name, group_files in asset_groups.items():
            group_matches = any(matches_filter_entry(group_name, entry) for entry in ignore_extensions)
            file_matches = any(
                any(matches_filter_entry(fname, entry) for entry in ignore_extensions)
                for fname, _ in group_files
            )
            if group_matches or file_matches:
                filtered_groups[group_name] = group_files
        asset_groups = filtered_groups

    results: List[AssetGroupItem] = []

    for asset_name, group_files in sorted(asset_groups.items()):
        item = AssetGroupItem(
            name=asset_name,
            relative_folder=rel_folder,
            template_id=template_id,
            extension=ext_norm,
            template_label=template_label
        )
        item.target_output = f"{asset_name}.{ext_norm}"
        item.available_candidates = folder_candidates

        assigned_files: Set[str] = set()

        for fname, fpath in group_files:
            base, ext = os.path.splitext(fname)
            b_lower = base.lower()

            if ext_norm == 'vmat':
                # Material slot assignments
                if any(s in b_lower for s in ('_color', '_albedo', '_basecolor', '_c', '_diffuse', '_bc', '_alb', '_d')):
                    item.slots['color'] = fpath
                    assigned_files.add(fname)
                elif any(s in b_lower for s in ('_normal', '_norm', '_n', '_nrm')):
                    item.slots['normal'] = fpath
                    assigned_files.add(fname)
                elif any(s in b_lower for s in ('_rough', '_roughness', '_r')):
                    item.slots['roughness'] = fpath
                    assigned_files.add(fname)
                elif any(s in b_lower for s in ('_ao', '_ambient', '_occlusion')):
                    item.slots['ao'] = fpath
                    assigned_files.add(fname)
                elif any(s in b_lower for s in ('_metal', '_metallic', '_metalness', '_m')):
                    item.slots['metalness'] = fpath
                    assigned_files.add(fname)
                elif any(s in b_lower for s in ('_orm', '_rma', '_arm', '_srmh', '_srm', '_packed', '_masks', '_mask')):
                    item.slots['orm'] = fpath
                    assigned_files.add(fname)
                elif any(s in b_lower for s in ('_height', '_disp', '_displacement', '_h')):
                    item.slots['height'] = fpath
                    assigned_files.add(fname)
                elif any(s in b_lower for s in ('_emissive', '_emission', '_emi', '_selfillum')):
                    item.slots['emissive'] = fpath
                    assigned_files.add(fname)
                elif any(s in b_lower for s in ('_opacity', '_opac', '_alpha', '_trans', '_translucency')):
                    item.slots['opacity'] = fpath
                    assigned_files.add(fname)
                elif any(s in b_lower for s in ('_tintmask', '_tint')):
                    item.slots['tintmask'] = fpath
                    assigned_files.add(fname)
                elif any(s in b_lower for s in ('_blendmask', '_blend_mask')):
                    item.slots['blendmask'] = fpath
                    assigned_files.add(fname)
            else:
                # ModelDoc / SmartProp slot assignments
                # 1. Collision Hull
                if b_lower.startswith(('phys_', 'col_', 'hull_', 'physics_', 'collision_')) or any(
                    s in b_lower for s in ('_phys', '_col', '_hull', '_collision', '_physics')
                ):
                    item.slots['collision'] = fpath
                    assigned_files.add(fname)
                # 2. LODs
                elif b_lower.startswith(('lod1_', 'lod_1_')) or '_lod1' in b_lower or '_lod_1' in b_lower:
                    item.slots['lod1'] = fpath
                    assigned_files.add(fname)
                elif b_lower.startswith(('lod2_', 'lod_2_')) or '_lod2' in b_lower or '_lod_2' in b_lower:
                    item.slots['lod2'] = fpath
                    assigned_files.add(fname)
                elif b_lower.startswith(('lod3_', 'lod_3_')) or '_lod3' in b_lower or '_lod_3' in b_lower:
                    item.slots['lod3'] = fpath
                    assigned_files.add(fname)

        # Fallback slot bindings from packed ORM if individual maps not found
        if 'orm' in item.slots:
            if 'roughness' not in item.slots:
                item.slots['roughness'] = item.slots['orm']
            if 'metalness' not in item.slots:
                item.slots['metalness'] = item.slots['orm']
            if 'ao' not in item.slots:
                item.slots['ao'] = item.slots['orm']

        # Remaining files -> Primary Render Mesh or Texture
        remaining = [f for f in group_files if f[0] not in assigned_files]
        if remaining:
            exact = next((f for f in remaining if os.path.splitext(f[0])[0].lower() == asset_name.lower()), None)
            primary_file = exact[1] if exact else remaining[0][1]
            if ext_norm == 'vmat':
                if 'color' not in item.slots:
                    item.slots['color'] = primary_file
            else:
                item.slots['mesh'] = primary_file
                item.slots['model'] = primary_file
        elif 'mesh' not in item.slots and group_files:
            if ext_norm == 'vmat':
                if 'color' not in item.slots:
                    item.slots['color'] = group_files[0][1]
            else:
                item.slots['mesh'] = group_files[0][1]

        _evaluate_item_status(item, slots, skipped_slots=skipped_slots)
        results.append(item)

    return results


def match_multi_template_folder_assets(
    directory: str,
    templates: List[Dict[str, Any]],
    settings: Optional[Dict[str, Any]] = None,
    analyzed_slots_map: Optional[Dict[str, Dict[str, Any]]] = None
) -> List[AssetGroupItem]:
    """
    Scans a folder and matches assets across all configured templates using
    each template's specific ignore/filter settings, skipped slots, and slots definition.
    """
    if not settings:
        settings = {}
    global_ignore_extensions = settings.get('ignore_extensions', '')
    global_ignore_list = settings.get('ignore_list', '')
    global_filter_mode = settings.get('filter_mode', 'exclude')
    algorithm = int(settings.get('algorithm', 0))

    if not analyzed_slots_map:
        analyzed_slots_map = {}

    all_results: List[AssetGroupItem] = []

    for idx, template_info in enumerate(templates):
        template_id = template_info.get('id', f'template_{idx}')
        ext = template_info.get('extension', 'vmdl').lower().strip('.')
        ref_path = template_info.get('reference', '')

        tpl_filter_mode = template_info.get('filter_mode') or global_filter_mode
        tpl_ignore_exts = template_info.get('ignore_extensions')
        if tpl_ignore_exts is None or tpl_ignore_exts == '':
            if tpl_filter_mode == global_filter_mode:
                tpl_ignore_exts = global_ignore_extensions
            else:
                tpl_ignore_exts = ''

        tpl_ignore_list = template_info.get('ignore_list')
        if tpl_ignore_list is None or tpl_ignore_list == '':
            tpl_ignore_list = global_ignore_list

        tpl_filter_mode = template_info.get('filter_mode') or global_filter_mode
        tpl_skipped_slots = template_info.get('skipped_slots') or []

        slots_def = analyzed_slots_map.get(template_id, {})
        if not slots_def and ref_path:
            from gui.editors.assetgroup_maker.analyzer import analyze_reference_file
            analysis = analyze_reference_file(ref_path)
            slots_def = analysis.slots

        if not slots_def:
            if ext == 'vmdl':
                slots_def = {'mesh': {'label': 'Render Mesh', 'required': True}}
            elif ext == 'vmat':
                slots_def = {'color': {'label': 'Color Map', 'required': True}}
            elif ext == 'vsndevts':
                slots_def = {'sound': {'label': 'Audio File', 'required': True}}
            elif ext == 'vsmart':
                slots_def = {'model': {'label': 'Model Asset', 'required': True}}
            else:
                slots_def = {'mesh': {'label': 'Source Asset', 'required': True}}

        ref_base_to_skip = None
        if ref_path:
            from gui.editors.assetgroup_maker.analyzer import resolve_reference_full_path
            ref_full = resolve_reference_full_path(ref_path, context_folder=directory)
            if ref_full and os.path.isfile(ref_full):
                try:
                    ref_dir = os.path.dirname(os.path.normpath(os.path.abspath(ref_full))).lower()
                    scanned_dir = os.path.normpath(os.path.abspath(directory)).lower()
                    if ref_dir == scanned_dir:
                        ref_base_to_skip = os.path.splitext(os.path.basename(ref_full))[0].lower()
                except Exception:
                    pass

        type_label = {
            'vmdl': 'ModelDoc (.vmdl)',
            'vmat': 'Material (.vmat)',
            'vsndevts': 'Sound Event (.vsndevts)',
            'vsmart': 'SmartProp (.vsmart)'
        }.get(ext, f"Unknown (.{ext})")

        items = match_folder_assets(
            directory=directory,
            slots=slots_def,
            extension=ext,
            ignore_extensions_str=tpl_ignore_exts,
            ignore_list_str=tpl_ignore_list,
            filter_mode=tpl_filter_mode,
            skipped_slots=tpl_skipped_slots,
            algorithm=algorithm,
            template_id=template_id,
            template_label=type_label
        )

        if ref_base_to_skip:
            items = [it for it in items if it.name.lower() != ref_base_to_skip]

        all_results.extend(items)

    return all_results


def _evaluate_item_status(item: AssetGroupItem, slots_def: Dict[str, Dict], skipped_slots: Optional[List[str]] = None):
    if skipped_slots is None:
        skipped_slots = []

    missing_required = []
    warnings = []

    for slot_key, slot_info in slots_def.items():
        if slot_key in skipped_slots:
            continue

        is_required = slot_info.get('required', False)
        fallback = slot_info.get('fallback', '')

        if slot_key not in item.slots:
            if fallback and fallback in item.slots and fallback not in skipped_slots:
                item.slots[slot_key] = item.slots[fallback]
                warnings.append(f"{slot_key}: using fallback ({fallback})")
            elif is_required:
                missing_required.append(slot_key)

    if missing_required:
        item.status = "error"
        item.status_message = f"Missing required slot(s): {', '.join(missing_required)}"
    elif warnings:
        item.status = "warning"
        item.status_message = "; ".join(warnings)
    else:
        item.status = "ready"
        item.status_message = "Ready"
