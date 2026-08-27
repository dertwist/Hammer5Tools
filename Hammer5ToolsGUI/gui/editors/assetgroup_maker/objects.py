import os
import json
import ast
from typing import Dict, List, Any, Optional
from gui.settings.common import get_settings_value, set_settings_value
from gui.common import JsonToKv3, Kv3ToJson

DEFAULT_FILE_TEMPLATE: Dict[str, Any] = {
    'version': 3,
    'settings': {
        'watch_changes': True,
        'filter_mode': 'exclude',
        'ignore_extensions': 'mb,ma,max,st,blend,blend1,vmdl,vmat,vsmart,tga,png,jpg,exr,hdr',
        'ignore_list': '',
        'custom_output': 'relative_path',
        'algorithm': 0,
        'custom_files': []
    },
    'templates': [
        {
            'id': 'template_0',
            'extension': 'vmdl',
            'reference': '',
            'filter_mode': 'exclude',
            'ignore_extensions': '',
            'ignore_list': '',
            'skipped_slots': [],
            'custom_tokens': {},
            'replacements': []
        }
    ]
}

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
                        'filename': '',
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
                        'parent_bone': '',
                        'surface_prop': 'default',
                        'collision_prop': 'default',
                        'tool_material': '',
                        'recenter_on_parent_bone': False,
                        'offset_origin': [0.0, 0.0, 0.0],
                        'offset_angles': [0.0, 0.0, 0.0],
                        'filename': '',
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


def convert_legacy_hbat_to_v3(legacy_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts legacy JSON .hbat data (v1/v2) with 'process' and 'file' blocks
    into the clean v3 multi-template structure without embedded raw KV3 text.
    """
    v3_data: Dict[str, Any] = {
        'version': 3,
        'settings': {
            'watch_changes': True,
            'ignore_extensions': 'mb,ma,max,st,blend,blend1,vmdl,vmat,vsmart,tga,png,jpg,exr,hdr',
            'ignore_list': '',
            'custom_output': 'relative_path',
            'algorithm': 0,
            'custom_files': []
        },
        'templates': []
    }

    process = legacy_data.get('process', {})
    if process:
        v3_data['settings']['watch_changes'] = bool(process.get('watch_changes', True))
        v3_data['settings']['ignore_extensions'] = process.get(
            'ignore_extensions',
            'mb,ma,max,st,blend,blend1,vmdl,vmat,vsmart,tga,png,jpg,exr,hdr'
        )
        v3_data['settings']['ignore_list'] = process.get('ignore_list', '')
        v3_data['settings']['custom_output'] = process.get('custom_output', 'relative_path')
        v3_data['settings']['algorithm'] = int(process.get('algorithm', 0))
        v3_data['settings']['custom_files'] = list(process.get('custom_files', []))

        replacements_raw = legacy_data.get('replacements', {})
        normalized_replacements = []
        if isinstance(replacements_raw, dict):
            for _, rep_info in sorted(replacements_raw.items(), key=lambda x: str(x[0])):
                if isinstance(rep_info, dict):
                    rep_pair = rep_info.get('replacement', [])
                    if len(rep_pair) >= 2:
                        normalized_replacements.append({
                            'from': str(rep_pair[0]),
                            'to': str(rep_pair[1])
                        })
                    elif 'from' in rep_info and 'to' in rep_info:
                        normalized_replacements.append({
                            'from': str(rep_info['from']),
                            'to': str(rep_info['to'])
                        })
        elif isinstance(replacements_raw, list):
            for rep_info in replacements_raw:
                if isinstance(rep_info, dict) and 'from' in rep_info and 'to' in rep_info:
                    normalized_replacements.append({
                        'from': str(rep_info['from']),
                        'to': str(rep_info['to'])
                    })

        ref_path = process.get('reference', '')
        ext = process.get('extension', 'vmdl')
        if not ext and ref_path:
            ext = os.path.splitext(ref_path)[1].lstrip('.').lower()

        v3_data['templates'].append({
            'id': 'template_0',
            'extension': ext or 'vmdl',
            'reference': ref_path,
            'replacements': normalized_replacements
        })

    # If already had templates list, copy them
    if 'templates' in legacy_data and isinstance(legacy_data['templates'], list) and legacy_data['templates']:
        v3_data['templates'] = legacy_data['templates']

    if not v3_data['templates']:
        v3_data['templates'].append({
            'id': 'template_0',
            'extension': 'vmdl',
            'reference': '',
            'replacements': []
        })

    return v3_data


def load_hbat_file(file_path: str) -> Dict[str, Any]:
    """
    Loads an .hbat file, automatically detecting KeyValues3 vs Legacy JSON format.
    Automatically converts legacy formats to clean v3 multi-template data.
    """
    if not os.path.isfile(file_path):
        return get_default_file()

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read().strip()
    except Exception as e:
        return get_default_file()

    # 1. Check if KeyValues3 format
    if '<!-- kv3' in content:
        try:
            parsed = Kv3ToJson(content)
            if isinstance(parsed, dict):
                if 'process' in parsed and 'templates' not in parsed:
                    return convert_legacy_hbat_to_v3(parsed)
                if 'templates' in parsed:
                    # Normalize settings if missing
                    if 'settings' not in parsed or not isinstance(parsed['settings'], dict):
                        parsed['settings'] = DEFAULT_FILE_TEMPLATE['settings'].copy()
                    else:
                        for k, v in DEFAULT_FILE_TEMPLATE['settings'].items():
                            if k not in parsed['settings']:
                                parsed['settings'][k] = v
                    for idx, t in enumerate(parsed.get('templates', [])):
                        if 'id' not in t:
                            t['id'] = f'template_{idx}'
                        if 'filter_mode' not in t:
                            t['filter_mode'] = 'exclude'
                        if 'ignore_extensions' not in t:
                            t['ignore_extensions'] = ''
                        if 'ignore_list' not in t:
                            t['ignore_list'] = ''
                        if 'skipped_slots' not in t:
                            t['skipped_slots'] = []
                        if 'custom_tokens' not in t:
                            t['custom_tokens'] = {}
                        if 'replacements' not in t:
                            t['replacements'] = []
                    return parsed
        except Exception as e:
            pass

    # 2. Try JSON format (legacy)
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            if 'process' in data or 'templates' not in data:
                return convert_legacy_hbat_to_v3(data)
            return data
    except json.JSONDecodeError:
        pass

    # 3. Fallback: try ast.literal_eval for python dict string
    try:
        parsed = ast.literal_eval(content)
        if isinstance(parsed, dict):
            if 'process' in parsed:
                return convert_legacy_hbat_to_v3(parsed)
            return parsed
    except Exception:
        pass

    return get_default_file()


def save_hbat_file(file_path: str, data: Dict[str, Any]) -> bool:
    """
    Saves multi-template configuration directly into KeyValues3 (.hbat) text format.
    Never includes raw file content text.
    """
    try:
        settings_in = data.get('settings', {})
        save_data = {
            'version': 3,
            'settings': {
                'watch_changes': bool(settings_in.get('watch_changes', True)),
                'filter_mode': str(settings_in.get('filter_mode', 'exclude')),
                'ignore_extensions': str(settings_in.get('ignore_extensions', '')),
                'ignore_list': str(settings_in.get('ignore_list', '')),
                'custom_output': str(settings_in.get('custom_output', 'relative_path')),
                'algorithm': int(settings_in.get('algorithm', 0)),
                'custom_files': list(settings_in.get('custom_files', []))
            },
            'templates': []
        }

        # Normalize templates
        templates_in = data.get('templates', [])
        for idx, t in enumerate(templates_in):
            template_entry = {
                'id': t.get('id', f'template_{idx}'),
                'extension': t.get('extension', 'vmdl'),
                'reference': t.get('reference', ''),
                'filter_mode': t.get('filter_mode', 'exclude'),
                'ignore_extensions': t.get('ignore_extensions', ''),
                'ignore_list': t.get('ignore_list', ''),
                'skipped_slots': list(t.get('skipped_slots', [])),
                'custom_tokens': dict(t.get('custom_tokens', {})),
                'replacements': t.get('replacements', [])
            }
            save_data['templates'].append(template_entry)

        # Encode directly to KV3
        kv3_text = JsonToKv3(save_data)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(kv3_text)

        return True
    except Exception as e:
        return False


def get_default_file() -> Dict[str, Any]:
    """Returns a fresh deepcopy of the default v3 multi-template file."""
    import copy
    return copy.deepcopy(DEFAULT_FILE_TEMPLATE)
