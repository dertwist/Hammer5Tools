from gui.common import JsonToKv3, Kv3ToJson, fast_deepcopy
from gui.editors.smartprop_editor.document_model import format_smartprop
import os, json
from gui.editors.assetgroup_maker.objects import DEFAULT_VMDL, get_default_file
from gui.settings.common import get_addon_dir
from gui.editors.assetgroup_maker.process import perform_batch_processing

# Optional dependencies for image processing
try:
    import numpy as np
    from PIL import Image
except Exception as _e:
    np = None
    Image = None
    # Handled at runtime with debug logs

class QuickVmdlFile():
    def __init__(self, filepath):
        try:
            rel_mesh = os.path.relpath(filepath, get_addon_dir()).replace(os.path.sep, '/')
        except (ValueError, Exception):
            rel_mesh = ""
        
        basename = os.path.splitext(os.path.basename(filepath))[0]
        vmdl_content = fast_deepcopy(DEFAULT_VMDL)
        
        for child in vmdl_content.get('rootNode', {}).get('children', []):
            if child.get('_class') == 'RenderMeshList':
                for mesh_file in child.get('children', []):
                    if mesh_file.get('_class') == 'RenderMeshFile':
                        mesh_file['filename'] = rel_mesh
            if child.get('_class') == 'PhysicsShapeList':
                for phys_file in child.get('children', []):
                    if phys_file.get('_class') == 'PhysicsHullFile':
                        phys_file['filename'] = rel_mesh
                        phys_file['name'] = basename

        vmdl_file = f"{os.path.splitext(filepath)[0]}.vmdl"
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
            return

        try:
            with open(self.filepath, 'r') as file:
                file_content = file.read()
        except Exception as e:
            return

        try:
            source_model = Kv3ToJson(file_content)
        except Exception as e:
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
            extracted_filename = ''
            for child in children:
                if child.get('_class') == 'RenderMeshList':
                    for grand_child in child.get('children', []):
                        if 'filename' in grand_child:
                            extracted_filename = grand_child.get('filename', '')
                            break
                    if extracted_filename:
                        break
            if not extracted_filename and len(children) > 1:
                child = children[1]
                grand_children = child.get('children', [])
                if grand_children:
                    extracted_filename = grand_children[0].get('filename', '')
                else:
                    raise ValueError("No grandchild found in source model")
            elif not extracted_filename and not children:
                raise ValueError("No children found in source model")
        except Exception as e:
            return

        # Use original file content for the file content key if available,
        # otherwise fall back to the default configuration.
        file_content_for_config = file_content if file_content.strip() else default_config.get("file", {}).get("content", "")

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
                        f"filename = \"{os.path.dirname(extracted_filename)}/#$ASSET_NAME$#{os.path.splitext(extracted_filename)[1]}\""
                    ]
                }
            },
            "file": {
                "content": file_content_for_config
            }
        }
        try:
            with open(output_file, 'w') as file:
                json.dump(new_config, file, indent=4)
            from gui.editors.assetgroup_maker.monitor import MonitoringFileWatcher
            MonitoringFileWatcher.notify_new_file(output_file)
        except Exception as e:
            pass

class QuickProcess:
    def __init__(self, parent=None, filepath=None):
        # No need for super().__init__ as this is not a Qt class
        self._filepath = filepath
        if self._filepath is None:
            raise ValueError('There is no filepath to process. Please provide a filepath.')

    def process(self):
        try:
            with open(self._filepath, 'r') as f:
                data = json.load(f)
            process = data.get('process', {})
            replacements = data.get('replacements', {})
            content = data.get('file', {}).get('content', '')
            if not process:
                return
            perform_batch_processing(
                file_path=self._filepath,
                process=process,
                preview=False,
                replacements=replacements,
                content_template=content
            )
        except Exception as e:
            pass


def fix_pbr_range(filepath: str, low: float = 0.25, high: float = 0.99) -> bool:
    """
    Clamp the image RGB channels to [low, high] in normalized 0..1 space.
    Alpha (if present) is preserved. Overwrites file in-place.
    Returns True on success.
    """
    try:
        if Image is None or np is None:
            return False
        if not os.path.isfile(filepath):
            return False

        img = Image.open(filepath)
        original_mode = img.mode
        if original_mode in ("P",):
            img = img.convert("RGBA")
        elif original_mode in ("CMYK", "YCbCr"):
            img = img.convert("RGB")

        arr = np.array(img)

        def clamp_norm(chan, lo, hi, max_val, dtype):
            f = chan.astype(np.float32) / max_val
            f = np.clip(f, lo, hi)
            f = (f * max_val).round()
            f = np.clip(f, 0, max_val)
            return f.astype(dtype)

        if arr.ndim == 2:
            # single-channel
            if np.issubdtype(arr.dtype, np.integer):
                max_val = float(np.iinfo(arr.dtype).max)
            else:
                max_val = 1.0
            out = clamp_norm(arr, low, high, max_val, arr.dtype)
        else:
            ch = arr.shape[-1]
            if np.issubdtype(arr.dtype, np.integer):
                max_val = float(np.iinfo(arr.dtype).max)
            else:
                max_val = 1.0
            if ch == 4:
                rgb = clamp_norm(arr[..., :3], low, high, max_val, arr.dtype)
                a = arr[..., 3]
                out = np.dstack([rgb, a])
            else:
                rgb = clamp_norm(arr[..., :3], low, high, max_val, arr.dtype)
                out = rgb

        out_img = Image.fromarray(out)
        try:
            if original_mode in ("RGB", "RGBA", "L"):
                out_img = out_img.convert(original_mode)
        except Exception:
            pass
        out_img.save(filepath)
        return True
    except Exception as e:
        return False




class QuickVsmart:
    def __init__(self, filepaths):
        if not filepaths:
            return
        if isinstance(filepaths, str):
            filepaths = [filepaths]

        valid_paths = [p for p in filepaths if p and (p.lower().endswith('.vmdl') or p.lower().endswith('.vsmart'))]
        if not valid_paths:
            return

        import random
        import string
        from gui.common import generate_unique_name, editor_info

        addon_dir = get_addon_dir()
        first_file = valid_paths[0]
        dir_path = os.path.dirname(first_file)

        # Determine new vsmart filename
        if len(valid_paths) == 1:
            base_name = os.path.splitext(os.path.basename(first_file))[0]
        else:
            base_name = os.path.basename(dir_path)

        existing_files = {f for f in os.listdir(dir_path) if f.endswith('.vsmart')}
        if f"{base_name}.vsmart" in existing_files:
            vsmart_name = generate_unique_name(base_name, {os.path.splitext(f)[0] for f in existing_files}, separator="_") + ".vsmart"
        else:
            vsmart_name = f"{base_name}.vsmart"
        vsmart_path = os.path.join(dir_path, vsmart_name)

        element_id = 1
        def next_id():
            nonlocal element_id
            cur = element_id
            element_id += 1
            return cur

        def gen_hash():
            return ''.join(random.choices(string.ascii_lowercase + string.digits, k=3))

        selector_hash = gen_hash()
        transform_hash = gen_hash()
        other_hash = gen_hash()

        rel_model_paths = []
        for path in valid_paths:
            try:
                rel_path = os.path.relpath(path, addon_dir).replace(os.path.sep, '/')
            except Exception:
                rel_path = path.replace(os.path.sep, '/')
            rel_model_paths.append((path, rel_path))

        max_child_index = max(0, len(valid_paths) - 1)
        first_model_rel = rel_model_paths[0][1] if rel_model_paths else ""

        variables = [
            # --- Category: Selector ---
            {
                "_class": "CSmartPropVariable_Bool",
                "m_VariableName": f"hammer5tools_category_{selector_hash}_start",
                "m_bExposeAsParameter": True,
                "m_DefaultValue": False,
                "m_nElementID": next_id(),
                "m_DisplayName": "---------- Selector ----------",
                "m_Hammer5ToolsCategoryName": "Selector",
                "m_ReadOnlyExpression": "true"
            },
            {
                "_class": "CSmartPropVariable_ChoiceSelectionMode",
                "m_VariableName": "SelectionMode",
                "m_bExposeAsParameter": True,
                "m_DefaultValue": "RANDOM",
                "m_nElementID": next_id()
            },
            {
                "_class": "CSmartPropVariable_Int",
                "m_VariableName": "SpecificChildIndex",
                "m_bExposeAsParameter": True,
                "m_DefaultValue": 0,
                "m_nElementID": next_id(),
                "m_DisplayName": "Model ID",
                "m_nParamaterMinValue": 0,
                "m_nParamaterMaxValue": max_child_index,
                "m_sModelName": "None",
                "m_ReadOnlyExpression": "SelectionMode != 'SPECIFIC'"
            },
            {
                "_class": "CSmartPropVariable_Bool",
                "m_VariableName": f"hammer5tools_category_{selector_hash}_end",
                "m_bExposeAsParameter": False,
                "m_DefaultValue": False,
                "m_nElementID": next_id(),
                "m_DisplayName": "                                             ",
                "m_Hammer5ToolsCategoryName": "New category",
                "m_ReadOnlyExpression": "true"
            },

            # --- Category: Transform ---
            {
                "_class": "CSmartPropVariable_Bool",
                "m_VariableName": f"hammer5tools_category_{transform_hash}_start",
                "m_bExposeAsParameter": True,
                "m_DefaultValue": False,
                "m_nElementID": next_id(),
                "m_DisplayName": "---------- Transform ----------",
                "m_Hammer5ToolsCategoryName": "Transform",
                "m_ReadOnlyExpression": "true"
            },
            {
                "_class": "CSmartPropVariable_Bool",
                "m_VariableName": "EnableRandomRotation",
                "m_bExposeAsParameter": True,
                "m_DefaultValue": False,
                "m_nElementID": next_id(),
                "m_DisplayName": "Random Rotation"
            },
            {
                "_class": "CSmartPropVariable_Vector2D",
                "m_VariableName": "RandomRotation",
                "m_bExposeAsParameter": True,
                "m_DefaultValue": [-180.0, 180.0],
                "m_nElementID": next_id(),
                "m_DisplayName": "RandomRotation (X - min, Y - max)",
                "m_sModelName": "None"
            },
            {
                "_class": "CSmartPropVariable_Bool",
                "m_VariableName": "EnableRandomScale",
                "m_bExposeAsParameter": True,
                "m_DefaultValue": False,
                "m_nElementID": next_id(),
                "m_DisplayName": "Random Scale"
            },
            {
                "_class": "CSmartPropVariable_Float",
                "m_VariableName": "RandomScaleMin",
                "m_bExposeAsParameter": True,
                "m_DefaultValue": 0.8,
                "m_nElementID": next_id(),
                "m_flParamaterMinValue": 0.2,
                "m_flParamaterMaxValue": 2.0,
                "m_sModelName": "None"
            },
            {
                "_class": "CSmartPropVariable_Float",
                "m_VariableName": "RandomScaleMax",
                "m_bExposeAsParameter": True,
                "m_DefaultValue": 1.2,
                "m_nElementID": next_id(),
                "m_flParamaterMinValue": 0.2,
                "m_flParamaterMaxValue": 2.0,
                "m_sModelName": "None"
            },
            {
                "_class": "CSmartPropVariable_Bool",
                "m_VariableName": f"hammer5tools_category_{transform_hash}_end",
                "m_bExposeAsParameter": False,
                "m_DefaultValue": False,
                "m_nElementID": next_id(),
                "m_DisplayName": "                                             ",
                "m_Hammer5ToolsCategoryName": "New category",
                "m_ReadOnlyExpression": "true"
            },

            # --- Category: Other ---
            {
                "_class": "CSmartPropVariable_Bool",
                "m_VariableName": f"hammer5tools_category_{other_hash}_start",
                "m_bExposeAsParameter": True,
                "m_DefaultValue": False,
                "m_nElementID": next_id(),
                "m_DisplayName": "---------- Other ----------",
                "m_Hammer5ToolsCategoryName": "Other",
                "m_ReadOnlyExpression": "true"
            },
            {
                "_class": "CSmartPropVariable_Bool",
                "m_VariableName": "CastShadows",
                "m_bExposeAsParameter": True,
                "m_DefaultValue": True,
                "m_nElementID": next_id()
            },
            {
                "_class": "CSmartPropVariable_Bool",
                "m_VariableName": "DetailObject",
                "m_bExposeAsParameter": True,
                "m_DefaultValue": False,
                "m_nElementID": next_id()
            },
            {
                "_class": "CSmartPropVariable_Int",
                "m_VariableName": "LodLevel",
                "m_bExposeAsParameter": True,
                "m_DefaultValue": 0,
                "m_nElementID": next_id(),
                "m_DisplayName": "LOD Level",
                "m_nParamaterMinValue": -1,
                "m_nParamaterMaxValue": 5,
                "m_sModelName": "None"
            },
            {
                "_class": "CSmartPropVariable_MaterialGroup",
                "m_VariableName": "MaterialGroupName",
                "m_bExposeAsParameter": True,
                "m_DefaultValue": "",
                "m_nElementID": next_id(),
                "m_sModelName": first_model_rel
            },
            {
                "_class": "CSmartPropVariable_Bool",
                "m_VariableName": f"hammer5tools_category_{other_hash}_end",
                "m_bExposeAsParameter": False,
                "m_DefaultValue": False,
                "m_nElementID": next_id(),
                "m_DisplayName": "                                             ",
                "m_Hammer5ToolsCategoryName": "New category",
                "m_ReadOnlyExpression": "true"
            }
        ]

        children = []
        for orig_path, rel_path in rel_model_paths:
            ext = os.path.splitext(orig_path)[1].lower()
            label = os.path.splitext(os.path.basename(orig_path))[0]
            if ext == '.vsmart':
                element = {
                    '_class': 'CSmartPropElement_SmartProp',
                    'm_sSmartProp': rel_path,
                    'm_Modifiers': [],
                    'm_SelectionCriteria': [],
                    'm_nElementID': next_id(),
                    'm_sLabel': label
                }
            else:
                element = {
                    '_class': 'CSmartPropElement_Model',
                    'm_MaterialGroupName': {'m_SourceName': 'MaterialGroupName'},
                    'm_Modifiers': [],
                    'm_SelectionCriteria': [],
                    'm_bCastShadows': {'m_SourceName': 'CastShadows'},
                    'm_bDetailObject': {'m_SourceName': 'DetailObject'},
                    'm_bDisableDynamicDeformable': False,
                    'm_bEnabled': True,
                    'm_bRigidDeformation': False,
                    'm_nElementID': next_id(),
                    'm_nLodLevel': {'m_SourceName': 'LodLevel'},
                    'm_sLabel': label,
                    'm_sModelName': rel_path
                }
            children.append(element)

        pick_one = {
            '_class': 'CSmartPropElement_PickOne',
            'm_HandleColor': [125, 230, 55],
            'm_HandleShape': 'DIAMOND',
            'm_HandleSize': 24.0,
            'm_Modifiers': [
                {
                    '_class': 'CSmartPropOperation_RandomScale',
                    'm_bEnabled': {'m_SourceName': 'EnableRandomScale'},
                    'm_flRandomScaleMax': {'m_SourceName': 'RandomScaleMax'},
                    'm_flRandomScaleMin': {'m_SourceName': 'RandomScaleMin'},
                    'm_flSnapIncrement': 0.0,
                    'm_nElementID': next_id()
                },
                {
                    '_class': 'CSmartPropOperation_RandomRotation',
                    'm_bEnabled': {'m_SourceName': 'EnableRandomRotation'},
                    'm_nElementID': next_id(),
                    'm_vRandomRotationMax': {'m_Components': [0.0, {'m_Expression': 'RandomRotation.y'}, 0.0]},
                    'm_vRandomRotationMin': {'m_Components': [0.0, {'m_Expression': 'RandomRotation.x'}, 0.0]}
                }
            ],
            'm_OutputChoiceVariableName': '',
            'm_SelectionCriteria': [],
            'm_SelectionMode': {'m_SourceName': 'SelectionMode'},
            'm_SpecificChildIndex': {'m_SourceName': 'SpecificChildIndex'},
            'm_bConfigurable': True,
            'm_bEnabled': True,
            'm_nElementID': next_id(),
            'm_sLabel': 'Selector',
            'm_vHandleOffset': {'m_Components': [0.0, -16.0, 0.0]},
            'm_Children': children
        }

        vsmart_content = {
            'generic_data_type': 'CSmartPropRoot',
            'm_nContentVersion': 0,
            'm_Variables': variables,
            'm_Choices': [],
            'm_Children': [pick_one]
        }
        vsmart_content.update(fast_deepcopy(editor_info))
        if 'editor_info' in vsmart_content:
            vsmart_content['editor_info']['m_nElementID'] = next_id()

        with open(vsmart_path, 'w') as f:
            f.write(format_smartprop(vsmart_content))
