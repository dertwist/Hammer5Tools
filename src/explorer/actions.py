import copy
from src.common import JsonToKv3
import os, json
from src.assetgroup_maker.objects import DEFAULT_VMDL, get_default_file
from src.settings.main import get_addon_name, get_cs2_path, get_addon_dir, debug

class QuickVmdlFile():
    def __init__(self, filepath):
        model_path = os.path.relpath(filepath, get_addon_dir())
        model_path = model_path.replace(os.path.sep, '/')
        vmdl_content = copy.deepcopy(DEFAULT_VMDL)
        vmdl_content['rootNode']['children'][1]['children'][0]['filename'] = model_path
        vmdl_content['rootNode']['children'][2]['children'][0]['filename'] = model_path
        vmdl_file, _ = os.path.splitext(filepath)
        vmdl_file = f"{vmdl_file}.vmdl"
        with open(vmdl_file, 'w') as file:
            file.write(JsonToKv3(vmdl_content, format='vmdl'))

class QuickConfigFile:
    def __init__(self, filepath):
        self.filepath = filepath
        self.create_config_file()

    def create_config_file(self):
        normalized_path = self.filepath.replace(os.path.sep, '/')
        rel_path = os.path.relpath(self.filepath, get_addon_dir()).replace(os.path.sep, '/')
        parent_dir = os.path.dirname(self.filepath)
        parent_name = os.path.basename(parent_dir)
        output_dir = os.path.dirname(parent_dir)
        output_file = os.path.join(output_dir, f"{parent_name}.hbat")
        default_config = get_default_file()
        new_config = {
            "process": {
                "extension": default_config.get("process", {}).get("extension", "vmdl"),
                "reference": f"{rel_path.replace('/', '\\')}",
                "ignore_list": default_config.get("process", {}).get("ignore_list", ""),
                "custom_files": default_config.get("process", {}).get("custom_files", []),
                "custom_output": default_config.get("process", {}).get("custom_output", "relative_path"),
                "algorithm": default_config.get("process", {}).get("algorithm", 0),
                "load_from_the_folder": True,
                "output_to_the_folder": True,
                "ignore_extensions": default_config.get("process", {}).get(
                    "ignore_extensions",
                    "mb,ma,max,st,blend,blend1,vmdl,vmat,vsmart,tga,png,jpg,exr,hdr"
                )
            },
            "replacements": {
                "0": {
                    "replacement": [
                        f"filename = \"{rel_path}\"",
                        f"filename = \"{os.path.dirname(rel_path)}/#$ASSET_NAME$#.fbx\""
                    ]
                }
            },
            "file": {
                "content": default_config.get("file", {}).get("content", "")
            },
        }
        try:
            with open(output_file, 'w') as file:
                json.dump(new_config, file, indent=4)
            debug(f"Created config file: {output_file}")
        except Exception as e:
            debug(f"Error creating config file: {e}")