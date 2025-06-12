from src.common import Kv3ToJson
import vdf
from collections import deque
from src.dotnet import extract_vmap_references
import unittest
from src.settings.main import get_addon_name, get_addon_dir
import os

def get_vmap_references(addon_dir=None, vmap=None):
    """
    Identify unused (junk) files in the addon, including textures and meshes.
    Returns a list of tuples (file_path, size).
    """
    if addon_dir is None:
        addon_dir = get_addon_dir()
    if vmap is None:
        raise ValueError("vmap must be provided")

    #Subfuncitons

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

    def get_smartprop_references(vsmart_path):
        """Extract references from a .vsmart file."""
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
                    if key in ('m_sModelName', 'm_sSmartProp') and isinstance(value, str) and value:
                        references.append(value)
                    elif isinstance(value, (dict, list)):
                        if isinstance(value, dict):
                            extract_references(value)
                        else:
                            for item in value:
                                extract_references(item)

        extract_references(file)
        return references

    def get_material_references(vmat_path):
        """Extract texture and material references from a .vmat file."""
        try:
            file = vdf.load(open(vmat_path, 'r'))
        except FileNotFoundError:
            print(f"Error: File '{vmat_path}' not found")
            return [], []
        except Exception as e:
            print(f"Error parsing '{vmat_path}': {e}")
            return [], []

        texture_references = []
        material_references = []

        def extract_references(d):
            if isinstance(d, dict):
                for key, value in d.items():
                    if key.startswith('Texture') and value and value != '':
                        texture_references.append(value)
                    elif key.startswith('MaterialLayerReference') and value:
                        material_references.append(value)
                    elif key.startswith('SkyTexture') and value:
                        material_references.append(value)
                    elif isinstance(value, dict):
                        extract_references(value)

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
                    if key in ('filename', 'target_file', 'from', 'to') and isinstance(value, str) and value:
                        references.append(value)
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
        if ext in ['.vmdl', '.vmdl_prefab']:
            return get_model_references(full_path)
        elif ext == '.vmat':
            texture_refs, mat_refs = get_material_references(full_path)
            return texture_refs + mat_refs
        elif ext == '.vsndevts':
            return get_soundevent_references(full_path)
        elif ext == '.vsmart':
            return get_smartprop_references(full_path)
        return []

    # Define file extensions
    asset_extensions = ['.vmat', '.vmdl', '.vmdl_prefab', '.vsndevts', '.vsmart', '.vmap',
'.png', '.tga', '.fbx', '.obj', '.jpg', '.wav', '.mp3', '.ogg', '.vmap','.hdri', '.tif', '.psd', '.exr', '.hdr']
    directories_to_search = ['maps', 'models', 'materials', 'sounds', 'soundevents', 'smartprops']
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

    addon_assets = [file for file in assets_collection if not (file.startswith('csgo/') or file.startswith('csgo_addons/'))]

    # Recursively collect all referenced files
    referenced_files = set([vmap_relative_path])
    queue = deque(vmap_assets_references)
    while queue:
        current_file = queue.popleft()
        if current_file not in referenced_files:
            referenced_files.add(current_file)
            ext = os.path.splitext(current_file)[1].lower()
            refs = []
            if ext == '.vmap':
                # Recursively extract references from child vmap
                child_vmap_path = os.path.join(addon_dir, current_file)
                if os.path.exists(child_vmap_path):
                    child_refs = extract_vmap_references(child_vmap_path)
                    refs.extend(child_refs)
            refs.extend(get_references(current_file, addon_dir))
            refs.extend(essentials_files)  # Include essential files in the references
            for ref in refs:
                if ref not in referenced_files:
                    queue.append(ref)
    return addon_assets, referenced_files

def get_junk_files(addon_dir=None, vmap=None):
    addon_assets, referenced_files = get_vmap_references(addon_dir, vmap)
    # Identify junk files
    junk_collection = []
    for file in addon_assets:
        if file not in referenced_files:
            full_path = os.path.join(addon_dir, file)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0
            junk_collection.append((file, size))
    return junk_collection



class TestJunkCollect(unittest.TestCase):
    def test_junkcollect(self):
        addon_name = "test_cleanup"
        addon_dir = os.path.normpath(r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\test_cleanup")
        vmap = os.path.normpath(r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\test_cleanup\maps\test_cleanup.vmap")
        junk_files = get_junk_files(addon_dir, vmap)
        print(f'Junk collect for addon: {addon_name}: {len(junk_files)}')