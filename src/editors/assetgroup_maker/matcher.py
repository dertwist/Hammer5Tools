import os
import re
import fnmatch
from typing import Dict, List, Optional, Set, Tuple
from src.settings.main import get_addon_dir, debug

KNOWN_SUFFIXES = [
    # Collision suffixes
    '_phys', '_col', '_hull', '_collision', '_physics',
    # LOD suffixes
    '_lod0', '_lod1', '_lod2', '_lod3', '_lod4', '_lod_0', '_lod_1', '_lod_2',
    # Render suffixes
    '_render', '_mesh', '_high', '_low',
    # Texture suffixes
    '_color', '_albedo', '_basecolor', '_c', '_diffuse',
    '_normal', '_norm', '_n',
    '_rough', '_roughness', '_r',
    '_ao', '_ambient', '_occlusion',
    '_metal', '_metallic', '_m',
    '_height', '_disp', '_displacement',
    '_mask', '_trans', '_alpha'
]


class AssetGroupItem:
    """Represents a grouped target asset with multiple matched slot files."""

    def __init__(self, name: str, relative_folder: str = ""):
        self.name = name
        self.relative_folder = relative_folder
        self.slots: Dict[str, str] = {}
        self.status: str = "ready"  # "ready", "warning", "error"
        self.status_message: str = "Ready"
        self.target_output: str = ""

    def get_slot_filename(self, slot_name: str) -> str:
        path = self.slots.get(slot_name, "")
        return os.path.basename(path) if path else ""

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'folder': self.relative_folder,
            'slots': self.slots,
            'status': self.status,
            'status_message': self.status_message,
            'target_output': self.target_output
        }


def strip_known_suffix(base_name: str) -> str:
    lower = base_name.lower()
    for suffix in KNOWN_SUFFIXES:
        if lower.endswith(suffix):
            return base_name[:-len(suffix)]
    return base_name


def is_file_ignored(file_name: str, ignore_extensions: List[str], ignore_patterns: List[str]) -> bool:
    _, ext = os.path.splitext(file_name)
    ext = ext.lstrip('.').lower()

    if ext in ignore_extensions:
        return True

    for pattern in ignore_patterns:
        if pattern and fnmatch.fnmatch(file_name.lower(), pattern.lower()):
            return True

    return False


def match_folder_assets(
    directory: str,
    slots: Dict[str, Dict],
    extension: str = "vmdl",
    ignore_extensions_str: str = "",
    ignore_list_str: str = "",
    algorithm: int = 0
) -> List[AssetGroupItem]:
    ignore_extensions = [e.strip().lstrip('.').lower() for e in ignore_extensions_str.split(',') if e.strip()]
    ignore_patterns = [p.strip() for p in ignore_list_str.split(',') if p.strip()]

    addon_dir = get_addon_dir()
    rel_folder = directory
    if addon_dir and os.path.isabs(directory):
        try:
            rel_folder = os.path.relpath(directory, addon_dir).replace('\\', '/')
        except ValueError:
            rel_folder = directory.replace('\\', '/')

    if not os.path.isdir(directory):
        debug(f"[Matcher] Directory does not exist: {directory}")
        return []

    all_files: List[Tuple[str, str]] = []
    for root, _, files in os.walk(directory):
        for f in files:
            if not is_file_ignored(f, ignore_extensions, ignore_patterns):
                all_files.append((f, os.path.join(root, f)))

    asset_groups: Dict[str, List[Tuple[str, str]]] = {}

    for fname, fpath in all_files:
        base, _ = os.path.splitext(fname)
        if algorithm == 1:
            root_name = base.rsplit('_', 1)[0] if '_' in base else base
        else:
            root_name = strip_known_suffix(base)

        if not root_name:
            root_name = base

        asset_groups.setdefault(root_name, []).append((fname, fpath))

    results: List[AssetGroupItem] = []

    for asset_name, group_files in sorted(asset_groups.items()):
        item = AssetGroupItem(name=asset_name, relative_folder=rel_folder)
        item.target_output = f"{asset_name}.{extension}"

        assigned_files: Set[str] = set()

        for fname, fpath in group_files:
            base, ext = os.path.splitext(fname)

            if any(s in base.lower() for s in ('_phys', '_col', '_hull', '_collision')):
                item.slots['collision'] = fpath
                assigned_files.add(fname)
            elif '_lod1' in base.lower() or '_lod_1' in base.lower():
                item.slots['lod1'] = fpath
                assigned_files.add(fname)
            elif '_lod2' in base.lower() or '_lod_2' in base.lower():
                item.slots['lod2'] = fpath
                assigned_files.add(fname)
            elif any(s in base.lower() for s in ('_color', '_albedo', '_basecolor', '_c', '_diffuse')):
                item.slots['color'] = fpath
                assigned_files.add(fname)
            elif any(s in base.lower() for s in ('_normal', '_norm', '_n')):
                item.slots['normal'] = fpath
                assigned_files.add(fname)
            elif any(s in base.lower() for s in ('_rough', '_roughness', '_r')):
                item.slots['roughness'] = fpath
                assigned_files.add(fname)
            elif any(s in base.lower() for s in ('_ao', '_ambient', '_occlusion')):
                item.slots['ao'] = fpath
                assigned_files.add(fname)
            elif any(s in base.lower() for s in ('_metal', '_metallic', '_m')):
                item.slots['metalness'] = fpath
                assigned_files.add(fname)

        remaining = [f for f in group_files if f[0] not in assigned_files]
        if remaining:
            exact = next((f for f in remaining if os.path.splitext(f[0])[0].lower() == asset_name.lower()), None)
            primary_file = exact[1] if exact else remaining[0][1]
            item.slots['mesh'] = primary_file
            item.slots['model'] = primary_file
        elif 'mesh' not in item.slots and group_files:
            item.slots['mesh'] = group_files[0][1]

        _evaluate_item_status(item, slots)
        results.append(item)

    return results


def _evaluate_item_status(item: AssetGroupItem, slots_def: Dict[str, Dict]):
    missing_required = []
    warnings = []

    for slot_key, slot_info in slots_def.items():
        is_required = slot_info.get('required', False)
        fallback = slot_info.get('fallback', '')

        if slot_key not in item.slots:
            if fallback and fallback in item.slots:
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
