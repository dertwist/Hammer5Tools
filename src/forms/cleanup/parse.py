from src.common import Kv3ToJson
import vdf
from collections import deque
from src.dotnet import extract_vmap_references
import unittest
from src.settings.main import get_addon_name, get_addon_dir
import os
import re


def get_vmap_references(addon_dir=None, vmap=None):
    """
    Identify unused (junk) files in the addon, including textures and meshes.
    Returns a list of tuples (file_path, size).
    """
    if addon_dir is None:
        addon_dir = get_addon_dir()
    if vmap is None:
        raise ValueError("vmap must be provided")

    # Subfunctions

    def parse_vtex_dmx(vtex_path):
        """
        Parse .vtex file in DMX format with keyvalues2_noids encoding.
        Extracts texture dependencies from m_inputTextureArray.
        """
        try:
            with open(vtex_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
        except FileNotFoundError:
            print(f"Error: File '{vtex_path}' not found")
            return []
        except Exception as e:
            print(f"Error reading '{vtex_path}': {e}")
            return []

        references = []

        # Pattern to match m_fileName entries in DMX format
        # Looks for: "m_fileName" "string" "path/to/file.png"
        pattern = r'"m_fileName"\s+"string"\s+"([^"]+)"'
        matches = re.findall(pattern, content)

        for match in matches:
            # Normalize path separators
            normalized_path = match.replace('\\', '/').lower()
            references.append(normalized_path)

        return references

    def get_particle_references(vpcf_path):
        """
        Extract references from a .vpcf (Valve Particle) file.
        Uses KV3 format parser to extract resource: prefixed dependencies.
        """
        try:
            with open(vpcf_path, 'r', encoding='utf-8') as file:
                kv3_data = file.read()
            file_data = Kv3ToJson(kv3_data)
        except FileNotFoundError:
            print(f"Error: File '{vpcf_path}' not found")
            return []
        except Exception as e:
            print(f"Error parsing '{vpcf_path}': {e}")
            return []

        references = []

        def extract_references(data):
            """Recursively extract resource: prefixed strings from KV3 data."""
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, str):
                        # Check for resource: prefix
                        if value.startswith('resource:'):
                            # Remove the 'resource:' prefix and normalize
                            resource_path = value[9:].strip('"').replace('\\', '/').lower()
                            references.append(resource_path)
                    elif isinstance(value, (dict, list)):
                        extract_references(value)
            elif isinstance(data, list):
                for item in data:
                    extract_references(item)

        extract_references(file_data)
        return references

    def get_texture_references(vtex_path):
        """
        Extract texture source file references from a .vtex file.
        Uses DMX parser to extract m_inputTextureArray entries.
        """
        return parse_vtex_dmx(vtex_path)

    def get_soundevent_references(vsndevts_path):
        """Extract sound event references from a .vsndevts file."""
        try:
            with open(vsndevts_path, 'r') as file:
                kv3_data = Kv3ToJson(file.read())
        except FileNotFoundError:
            print(f"Error: File '{vsndevts_path}' not found")
            return []
        except Exception as e:
            print(f"Error parsing '{vsndevts_path}': {e}")
            return []

        references = []

        def convert_vsnd(vsnd):
            """
            Convert a .vsnd path to a real file path by trying alternative extensions.
            """
            path, _ = (os.path.splitext(vsnd.replace('/', '\\')))
            full_base_path = os.path.join(addon_dir, path)
            for ext in ['.mp3', '.wav', '.ogg']:
                full_path = full_base_path + ext
                if os.path.isfile(full_path):
                    return vsnd.replace('.vsnd', ext)
            return vsnd

        def extract_references(data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == 'vsnd_files_track_01':
                        if isinstance(value, str):
                            references.append(convert_vsnd(value))
                        elif isinstance(value, list):
                            for item in value:
                                if isinstance(item, str):
                                    references.append(convert_vsnd(item))
                    elif isinstance(value, dict):
                        extract_references(value)
                    elif isinstance(value, list):
                        for item in value:
                            extract_references(item)
            elif isinstance(data, list):
                for item in data:
                    extract_references(item)

        extract_references(kv3_data)
        return references

    def get_smartprop_references(vsmart_path, addon_dir=None, visited=None):
        """
        Extract references from a .vsmart file, avoiding infinite recursion by tracking visited files.
        :param vsmart_path: Path to the .vsmart file.
        :param addon_dir: Base directory for resolving relative references.
        :param visited: Set of already visited file paths.
        :return: List of referenced model names.
        """
        if visited is None:
            visited = set()
        if addon_dir is None:
            addon_dir = os.path.dirname(vsmart_path)

        abs_path = os.path.abspath(vsmart_path)
        if abs_path in visited:
            # Already processed this file, avoid recursion
            return []
        visited.add(abs_path)

        try:
            with open(vsmart_path, 'r') as f:
                kv3_data = f.read()
            file = Kv3ToJson(kv3_data)
        except FileNotFoundError:
            print(f"Error: File '{vsmart_path}' not found")
            return []
        except Exception as e:
            print(f"Error parsing '{vsmart_path}': {e}")
            return []

        references = []

        def extract_references(d):
            if isinstance(d, dict):
                for key, value in d.items():
                    if key == 'm_sModelName' and isinstance(value, str) and value:
                        references.append(value)
                    elif key == 'm_sSmartProp' and isinstance(value, str) and value:
                        # Recursively process referenced smartprop files
                        ref_path = os.path.join(addon_dir, value)
                        references.extend(get_smartprop_references(ref_path, addon_dir, visited))
                        references.append(value)
                    elif isinstance(value, (dict, list)):
                        extract_references(value)
            elif isinstance(d, list):
                for item in d:
                    extract_references(item)

        extract_references(file)
        return references

    def get_material_references(vmat_path):
        """Extract texture and material references from a .vmat file."""
        try:
            with open(vmat_path, 'r') as f:
                file = vdf.load(f)
        except FileNotFoundError:
            print(f"Error: File '{vmat_path}' not found")
            return [], []
        except Exception as e:
            print(f"Error parsing '{vmat_path}': {e}")
            return [], []

        texture_references = []
        material_references = []

        def extract_references(node):
            """Recursively walk a nested dict / list structure collecting texture and material paths."""
            # Handle dictionaries
            if isinstance(node, dict):
                for key, val in node.items():
                    # If the value is a string, decide if it represents a texture or material reference
                    if isinstance(val, str):
                        # Looks-like-a-path heuristics: contains a path separator and a dot, and isn't an inline array (starts with '[')
                        is_path_like = (('/' in val or '\\' in val) and '.' in val and not val.strip().startswith('['))
                        if is_path_like and ('Texture' in key or 'Material' in key or 'SkyTexture' in key):
                            if 'Texture' in key:
                                # Direct texture reference
                                print(val)
                                texture_references.append(val.lower())
                            else:  # 'Material' in key
                                # First add the material itself
                                material_references.append(val.lower())
                                # Then dive into that material file to find nested references
                                child_tex, child_mat = get_material_references(os.path.join(addon_dir, val))
                                texture_references.extend(child_tex)
                                material_references.extend(child_mat)
                    # Recurse into nested containers
                    if isinstance(val, (dict, list)):
                        extract_references(val)
            # Handle lists
            elif isinstance(node, list):
                for item in node:
                    extract_references(item)

        extract_references(file)
        return texture_references, material_references

    def get_model_references(vmdl_path):
        """Extract references from a .vmdl or .vmdl_prefab file."""
        try:
            with open(vmdl_path, 'r') as f:
                kv3_data = f.read()
            file = Kv3ToJson(kv3_data)
        except FileNotFoundError:
            print(f"Error: File '{vmdl_path}' not found")
            return []
        except Exception as e:
            print(f"Error parsing '{vmdl_path}': {e}")
            return []

        references = []

        def extract_references(d):
            if isinstance(d, dict):
                for key, value in d.items():
                    if key in ('filename', 'target_file', 'to', 'global_default_material',
                               'single_override_material') and isinstance(value, str) and value:
                        normalised = os.path.normpath(value).replace('\\', '/').lower()
                        references.append(normalised)
                    elif isinstance(value, (dict, list)):
                        if isinstance(value, dict):
                            extract_references(value)
                        else:
                            for item in value:
                                extract_references(item)

        extract_references(file)
        return references

    def get_references(file_path, addon_dir):
        """Extract references from a file based on its type."""
        ext = os.path.splitext(file_path)[1].lower()
        full_path = os.path.join(addon_dir, file_path)
        if ext == '.vsmart':
            return get_smartprop_references(full_path)
        elif ext in ['.vmdl', '.vmdl_prefab']:
            return get_model_references(full_path)
        elif ext == '.vmat':
            texture_refs, mat_refs = get_material_references(full_path)
            return texture_refs + mat_refs
        elif ext == '.vsndevts':
            return get_soundevent_references(full_path)
        elif ext == '.vpcf':
            return get_particle_references(full_path)
        elif ext == '.vtex':
            return get_texture_references(full_path)

        return []

    # Define file extensions - UPDATED to include .vpcf and .vtex
    asset_extensions = ['.vmat', '.vmdl', '.vmdl_prefab', '.vsndevts', '.vsmart', '.vmap',
                        '.png', '.tga', '.fbx', '.obj', '.jpg', '.wav', '.mp3', '.ogg', '.vmap', '.hdri', '.tif',
                        '.psd', '.exr', '.hdr', '.vpcf', '.vtex']
    directories_to_search = ['maps', 'models', 'materials', 'sounds', 'soundevents', 'smartprops', 'particles']
    directories_to_ignore = ['materials\\default', 'weapons', 'RadGen', 'materials\\radgen']
    essentials_files = [f'soundevents/soundevents_addon.vsndevts']
    # Get the main .vmap file path
    vmap_path = vmap
    vmap_relative_path = os.path.relpath(vmap_path, addon_dir).replace('\\', '/')
    print(f'vmap_relative_path {vmap_relative_path}')
    vmap_assets_references = extract_vmap_references(vmap_path)
    print(f"Found {len(vmap_assets_references)} direct references in the addon.")

    # Collect all asset files in the addon
    assets_collection = []
    for directory in directories_to_search:
        for root, dirs, files in os.walk(os.path.join(addon_dir, directory)):
            if any(ignored in root for ignored in directories_to_ignore):
                continue
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file_path)[1].lower()
                if ext in asset_extensions:
                    relative_path = os.path.relpath(file_path, addon_dir).replace('\\', '/')
                    assets_collection.append(relative_path)

    print(f"Found {len(assets_collection)} assets in the addon.")

    addon_assets = [file for file in assets_collection if
                    not (file.startswith('csgo/') or file.startswith('csgo_addons/'))]

    # --- Recursive reference collection with ordered stages -----------------
    # Stage priority:
    #   1) All .vmap files (including child vmaps)
    #      ↳ can reference: other .vmap, .vsmart, .vmat, .vmdl, .vpcf files
    #   2) All .vsmart files (including child smartprops)
    #      ↳ can reference: other .vsmart, .vmdl files
    #   3) All .vpcf files (particle systems)
    #      ↳ can reference: .vmat, .vtex, .vmdl files
    #   4) All .vmdl / .vmdl_prefab files (including child models)
    #      ↳ can reference: .vmdl, .vmdl_prefab, .vmat, geometry sources (.fbx, .obj, .dmx, …)
    #   5) All .vmat files (including child materials)
    #      ↳ can reference: other .vmat and texture assets (.png, .tga, .tif, etc.)
    #   6) All .vtex files (texture compiler)
    #      ↳ can reference: source texture files (.png, .tga, .psd, .tif, .exr, etc.)
    #   7) All .vsndevts files
    #      ↳ can reference: audio assets (.mp3, .wav, .ogg, …)

    referenced_files: set[str] = set()

    # Separate queues for each priority level
    queue_vmap: deque[str] = deque([vmap_relative_path])  # start with root vmap
    queue_vsmart: deque[str] = deque()
    queue_vpcf: deque[str] = deque()
    queue_vmdl: deque[str] = deque()
    queue_vmat: deque[str] = deque()
    queue_vtex: deque[str] = deque()
    queue_vsndevts: deque[str] = deque()
    queue_other: deque[str] = deque()

    # Helper to push a reference into the correct queue if it's new
    def enqueue(path: str):
        ext = os.path.splitext(path)[1].lower()
        if ext == '.vmap':
            queue_vmap.append(path)
        elif ext == '.vsmart':
            queue_vsmart.append(path)
        elif ext == '.vpcf':
            queue_vpcf.append(path)
        elif ext in ('.vmdl', '.vmdl_prefab'):
            queue_vmdl.append(path)
        elif ext == '.vmat':
            queue_vmat.append(path)
        elif ext == '.vtex':
            queue_vtex.append(path)
        elif ext == '.vsndevts':
            queue_vsndevts.append(path)
        else:
            queue_other.append(path)

    # Seed initial references extracted directly from the root vmap
    for ref in vmap_assets_references:
        enqueue(ref)

    # Utility to process a single file and enqueue its references
    def process_file(rel_path: str):
        """Add file to reference set and enqueue any nested references it contains."""
        if rel_path in referenced_files:
            return
        referenced_files.add(rel_path)
        ext = os.path.splitext(rel_path)[1].lower()
        refs: list[str] = []

        # Dedicated handling for nested vmaps to avoid re-opening large sets later
        if ext == '.vmap':
            child_vmap_path = os.path.join(addon_dir, rel_path)
            if os.path.exists(child_vmap_path):
                refs.extend(extract_vmap_references(child_vmap_path))
        # Generic extraction for all supported file types
        refs.extend(get_references(rel_path, addon_dir))

        # Add essential always-present files
        refs.extend(essentials_files)

        for r in refs:
            enqueue(r)

    # Stage 1 – process every vmap first
    while queue_vmap:
        vmap_to_process = queue_vmap.popleft()
        process_file(vmap_to_process)

    # Stage 2 – process all smartprops (.vsmart)
    while queue_vsmart:
        smart_to_process = queue_vsmart.popleft()
        process_file(smart_to_process)

    # Stage 3 – process all particle systems (.vpcf)
    while queue_vpcf:
        vpcf_to_process = queue_vpcf.popleft()
        process_file(vpcf_to_process)

    # Stage 4 – process all models (.vmdl / .vmdl_prefab)
    while queue_vmdl:
        model_to_process = queue_vmdl.popleft()
        process_file(model_to_process)

    # Stage 5 – process all materials (.vmat)
    while queue_vmat:
        vmat_to_process = queue_vmat.popleft()
        process_file(vmat_to_process)

    # Stage 6 – process all texture compiler files (.vtex)
    while queue_vtex:
        vtex_to_process = queue_vtex.popleft()
        process_file(vtex_to_process)

    # Stage 7 – process all sound event files (.vsndevts)
    while queue_vsndevts:
        vsnd_to_process = queue_vsndevts.popleft()
        process_file(vsnd_to_process)

    # Finally process any remaining miscellaneous files
    while queue_other:
        process_file(queue_other.popleft())

    return addon_assets, referenced_files


def get_junk_files(addon_dir=None, vmap=None):
    addon_assets, referenced_files = get_vmap_references(addon_dir, vmap)

    referenced_files_lower = set(f.lower() for f in referenced_files)
    junk_collection = []
    for file in addon_assets:
        if file.lower() not in referenced_files_lower:
            full_path = os.path.join(addon_dir, file)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0
            junk_collection.append((file, size))
    return junk_collection


class TestJunkCollect(unittest.TestCase):
    def test_junkcollect(self):
        addon_name = "de_sanctum"
        addon_dir = os.path.normpath(
            r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_sanctum")
        vmap = os.path.normpath(
            r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_sanctum\maps\de_sanctum.vmap")
        junk_files = get_junk_files(addon_dir, vmap)
        print(f'Junk collect for addon: {addon_name}: {len(junk_files)}')
