import copy
from src.common import JsonToKv3, Kv3ToJson
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

        try:
            rel_path = os.path.relpath(self.filepath, get_addon_dir()).replace(os.path.sep, '/')
        except Exception as e:
            debug(f"Error computing relative path: {e}")
            return

        try:
            with open(self.filepath, 'r') as file:
                file_content = file.read()
        except Exception as e:
            debug(f"Error reading file '{self.filepath}': {e}")
            return

        try:
            source_model = Kv3ToJson(file_content)
        except Exception as e:
            debug(f"Error converting file content to JSON: {e}")
            return

        # Determine file paths based on the current file's directory.
        parent_dir = os.path.dirname(self.filepath)
        parent_name = os.path.basename(parent_dir)
        output_dir = os.path.dirname(parent_dir)
        output_file = os.path.join(output_dir, f"{parent_name}.hbat")

        default_config = get_default_file()
        extension = default_config.get("process", {}).get("extension", "vmdl")
        reference = rel_path.replace('/', '\\')
        try:
            children = source_model.get('rootNode', {}).get('children', [])
            if len(children) > 1:
                child = children[1]
                grand_children = child.get('children', [])
                if grand_children:
                    extracted_filename = grand_children[0].get('filename', '')
                else:
                    raise ValueError("No grandchild found in source model")
            else:
                raise ValueError("Not enough children in source model")
        except Exception as e:
            debug(f"Error extracting filename from source model: {e}")
            return
        new_config = {
            "process": {
                "extension": extension,
                "reference": reference,
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
                        f"filename = \"{extracted_filename}\"",
                        f"filename = \"{os.path.dirname(extracted_filename)}/#$ASSET_NAME$#.{extension}\""
                    ]
                }
            },
            "file": {
                "content": default_config.get("file", {}).get("content", "")
            }
        }
        try:
            with open(output_file, 'w') as file:
                json.dump(new_config, file, indent=4)
            debug(f"Created config file: {output_file}")
        except Exception as e:
            debug(f"Error creating config file: {e}")