import os
import json
import re
from typing import Optional, Dict, List, Tuple, Set
from PySide6.QtCore import Signal, QThread
from src.settings.main import get_addon_name, get_cs2_path, get_addon_dir, debug
from src.editors.assetgroup_maker.objects import get_default_file
from src.editors.assetgroup_maker.matcher import match_folder_assets, AssetGroupItem
from src.editors.assetgroup_maker.analyzer import analyze_reference_file


class StartProcess(QThread):
    """Thread to handle the start of a processing task."""

    finished = Signal()

    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.stop_thread = False

    def update_reference_content(self, reference: str) -> str:
        reference_path = os.path.join(get_addon_dir(), reference) if get_addon_dir() else reference
        try:
            with open(reference_path, 'r', encoding='utf-8', errors='replace') as file:
                return file.read()
        except Exception as e:
            debug(f"Error reading reference file {reference_path}: {e}")
            return ""

    def load_file(self, filepath: str) -> Tuple[Dict, Dict, str]:
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                data = json.load(file)
            process = data.get('process', {})
            replacements = data.get('replacements', {})
            content = data.get('file', {}).get('content', '')
            return process, replacements, content
        except Exception as e:
            debug(f"Error loading file {filepath}: {e}")
            return {}, {}, ""

    def run(self):
        try:
            if self.stop_thread:
                return

            process, replacements, content = self.load_file(self.filepath)
            if not process:
                debug("No process configuration found. Aborting.")
                return

            reference = process.get('reference')
            if reference and not content:
                content = self.update_reference_content(reference)

            if self.stop_thread:
                return

            perform_batch_processing(
                file_path=self.filepath,
                process=process,
                preview=False,
                replacements=replacements,
                content_template=content
            )

            self.finished.emit()
        except Exception as e:
            debug(f"Error in StartProcess: {e}")

    def stop(self):
        self.stop_thread = True
        self.quit()
        self.wait()


def render_asset_template(
    content_template: str,
    asset_item: AssetGroupItem,
    relative_batch_path: str,
    replacements: Optional[Dict] = None
) -> str:
    data = content_template

    # 1. Apply user replacement rules if any
    if replacements:
        for key, replacement in replacements.items():
            old, new = replacement.get('replacement', ['', ''])
            if old:
                data = data.replace(old, new)

    # 2. Base tokens
    data = data.replace("#$FOLDER_PATH$#", relative_batch_path)
    data = data.replace("#$ASSET_NAME$#", asset_item.name)

    # 3. Slot tokens
    for slot_name, slot_path in asset_item.slots.items():
        slot_filename = os.path.basename(slot_path)
        slot_base, _ = os.path.splitext(slot_filename)
        data = data.replace(f"#${slot_name.upper()}$#", slot_filename)
        data = data.replace(f"#${slot_name.upper()}_NAME$#", slot_base)
        data = data.replace(f"#${slot_name.upper()}_PATH$#", slot_path.replace('\\', '/'))

    # 4. Handle conditional blocks: <!-- IF SLOT --> ... <!-- ENDIF -->
    def evaluate_conditional(match):
        slot_var = match.group(1).strip().lower()
        block_content = match.group(2)
        if slot_var in asset_item.slots and asset_item.slots[slot_var]:
            return block_content
        return ""

    data = re.sub(r'<!--\s*IF\s+([A-Za-z0-9_]+)\s*-->([\s\S]*?)<!--\s*ENDIF\s*-->', evaluate_conditional, data)
    return data


def perform_batch_processing(
    file_path: str,
    process: Dict,
    preview: bool,
    replacements: Dict,
    content_template: Optional[str] = None
) -> List[str]:
    cs2_path = get_cs2_path()
    addon_name = get_addon_name()
    addon_dir = get_addon_dir()

    if addon_dir:
        base_directory = addon_dir
    elif cs2_path and addon_name:
        base_directory = os.path.join(cs2_path, 'content', 'csgo_addons', addon_name)
    else:
        base_directory = os.path.dirname(file_path) if file_path else os.getcwd()

    # Determine batch directory: subfolder matching file stem, or parent directory
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

    algorithm = int(process.get('algorithm', 0))
    file_extension = process.get('extension', 'vmdl').lstrip('.')
    ignore_extensions = process.get('ignore_extensions', get_default_file()['process']['ignore_extensions'])
    ignore_list = process.get('ignore_list', '')
    reference = process.get('reference')
    reference_full = os.path.join(addon_dir, reference) if reference and addon_dir else reference

    load_from_the_folder = bool(process.get('load_from_the_folder', True))
    output_to_the_folder = bool(process.get('output_to_the_folder', True))

    slots_def = {}
    if reference:
        analysis = analyze_reference_file(reference)
        slots_def = analysis.slots

    if not slots_def:
        slots_def = {'mesh': {'required': True}}

    if load_from_the_folder and os.path.isdir(batch_directory):
        asset_items = match_folder_assets(
            directory=batch_directory,
            slots=slots_def,
            extension=file_extension,
            ignore_extensions_str=ignore_extensions,
            ignore_list_str=ignore_list,
            algorithm=algorithm
        )
    else:
        custom_files = process.get('custom_files', [])
        asset_items = []
        for cf in custom_files:
            base_name = os.path.splitext(os.path.basename(cf))[0]
            item = AssetGroupItem(name=base_name, relative_folder=relative_batch_path)
            item.slots['mesh'] = cf
            item.slots['model'] = cf
            item.target_output = f"{base_name}.{file_extension}"
            asset_items.append(item)

    if preview:
        return preview_processing_files([item.name for item in asset_items], batch_directory, file_extension, process)

    if output_to_the_folder:
        output_directory = batch_directory
    else:
        custom_output = process.get('custom_output', '')
        output_directory = os.path.join(addon_dir, custom_output) if addon_dir else custom_output

    if not os.path.isdir(output_directory):
        try:
            os.makedirs(output_directory, exist_ok=True)
        except Exception as e:
            debug(f"Failed to create output directory {output_directory}: {e}")
            return []

    created_files: List[str] = []

    if content_template is None:
        if reference_full and os.path.isfile(reference_full):
            try:
                with open(reference_full, 'r', encoding='utf-8', errors='replace') as f:
                    content_template = f.read()
            except Exception as e:
                debug(f"Failed to load content template: {e}")
                return []
        else:
            debug("Content template is missing. Skipping file creation.")
            return []

    for item in asset_items:
        output_file_path = os.path.join(output_directory, f"{item.name}.{file_extension}")
        output_resolved = os.path.abspath(output_file_path)

        if reference_full:
            ref_resolved = os.path.abspath(reference_full)
            if os.name == 'nt' and output_resolved.lower() == ref_resolved.lower():
                continue
            elif output_resolved == ref_resolved:
                continue

        rendered_data = render_asset_template(
            content_template=content_template,
            asset_item=item,
            relative_batch_path=relative_batch_path,
            replacements=replacements
        )

        try:
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(rendered_data)
            created_files.append(output_file_path)
            debug(f"Created file: {output_file_path}")
        except Exception as e:
            debug(f"Failed to write file {output_file_path}: {e}")

    return created_files


def preview_processing_files(files: List[str], base_directory: str, extension: str,
                             process: Dict) -> Tuple[List[str], Optional[List[str]], str, str]:
    if process.get('load_from_the_folder', True):
        files_list_out = []
        ignore_exts = [ext.strip().lstrip('.').lower() for ext in process.get('ignore_extensions', '').split(',') if ext.strip()]
        ignore_list = [item.strip() for item in process.get('ignore_list', '').split(',') if item.strip()]

        if os.path.isdir(base_directory):
            for root, _, files_in_dir in os.walk(base_directory):
                for file in files_in_dir:
                    _, ext = os.path.splitext(file)
                    ext = ext.lstrip('.').lower()
                    if ext not in ignore_exts and file not in ignore_list:
                        files_list_out.append(file)
        return files, files_list_out, extension, base_directory
    else:
        return [get_basename_without_extension(f) for f in files], None, extension, base_directory


def get_basename_without_extension(file_path: str) -> str:
    return os.path.splitext(os.path.basename(file_path))[0]


def extract_base_names(names: List[str]) -> Set[str]:
    return set(os.path.basename(name) for name in names)


def extract_base_names_underscore(names: List[str]) -> Set[str]:
    return set(name.rsplit('_', 1)[0] if '_' in name else name for name in names)


def search_files(directory: str, algorithm: int, ignore_extensions: List[str], process: Dict) -> Set[str]:
    ignore_list = [item.strip() for item in process.get('ignore_list', '').split(',') if item.strip()]
    files_found = []
    clean_ignore_exts = [e.lstrip('.').lower() for e in ignore_extensions]

    if os.path.isdir(directory):
        for root, _, files_in_dir in os.walk(directory):
            for file in files_in_dir:
                _, ext = os.path.splitext(file)
                ext = ext.lstrip('.').lower()
                if file not in ignore_list and ext not in clean_ignore_exts:
                    base_name, _ = os.path.splitext(file)
                    files_found.append(base_name)

    if algorithm == 0:
        return extract_base_names(files_found)
    elif algorithm == 1:
        return extract_base_names_underscore(files_found)
    else:
        return set()