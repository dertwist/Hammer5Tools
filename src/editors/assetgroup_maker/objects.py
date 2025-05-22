import ast
from src.settings.common import get_settings_value, set_settings_value
from src.common import JsonToKv3, Kv3ToJson

DEFAULT_FILE_TEMPLATE = {
    'file': {
        'content': ''
    },
    'process': {
        'extension': 'vmdl',
        'reference': '',
        'ignore_list': '',
        'custom_files': [],
        'custom_output': 'relative_path',
        'algorithm': 0,
        'ignore_extensions': 'mb,ma,max,st,blend,blend1,vmdl,vmat,vsmart,tga,png,jpg,exr,hdr'
    }
}

def get_default_file():
    stored = get_settings_value('AssetGroupMaker', 'default_file')
    if not stored:
        return DEFAULT_FILE_TEMPLATE
    try:
        parsed = ast.literal_eval(stored)
        if isinstance(parsed, dict) and 'process' in parsed:
            return parsed
        else:
            set_settings_value('AssetGroupMaker', 'default_file', str(DEFAULT_FILE_TEMPLATE))
            return DEFAULT_FILE_TEMPLATE
    except Exception as e:
        print(f"Error parsing default_file setting: {e}")
        set_settings_value('AssetGroupMaker', 'default_file', str(DEFAULT_FILE_TEMPLATE))
        return DEFAULT_FILE_TEMPLATE

DEFAULT_VMDL = {
    'rootNode': {
        '_class': 'RootNode',
        'children': [
            {
                '_class': 'MaterialGroupList',
                'children': [
                    {
                        '_class': 'DefaultMaterialGroup',
                        'remaps': [],
                        'use_global_default': True,
                        'global_default_material': 'materials/dev/reflectivity_20b.vmat'
                    }
                ]
            },
            {
                '_class': 'RenderMeshList',
                'children': [
                    {
                        '_class': 'RenderMeshFile',
                        'filename': 'models/modular/trim_roof/var_01/trim_roof_01_64_a.fbx',
                        'import_scale': 1.0,
                        'import_filter': {
                            'exclude_by_default': False,
                            'exception_list': []
                        }
                    }
                ]
            },
            {
                '_class': 'PhysicsShapeList',
                'children': [
                    {
                        '_class': 'PhysicsHullFile',
                        'name': 'trim_roof_01_128_a',
                        'parent_bone': '',
                        'surface_prop': 'default',
                        'collision_prop': 'default',
                        'tool_material': '',
                        'recenter_on_parent_bone': False,
                        'offset_origin': [0.0, 0.0, 0.0],
                        'offset_angles': [0.0, 0.0, 0.0],
                        'filename': 'models/modular/trim_roof/var_01/trim_roof_01_64_a.fbx',
                        'import_scale': 1.0,
                        'faceMergeAngle': 5.0,
                        'maxHullVertices': 24,
                        'import_mode': 'HullPerElement',
                        'small_element_threshold': 0.0,
                        'thin_element_threshold': 0.0,
                        'optimization_algorithm': 'QEM',
                        'import_filter': {
                            'exclude_by_default': False,
                            'exception_list': []
                        }
                    }
                ],
                'leave_body_collision_unmodified': False
            }
        ],
        'model_archetype': '',
        'primary_associated_entity': '',
        'anim_graph_name': '',
        'document_sub_type': 'ModelDocSubType_None'
    }
}