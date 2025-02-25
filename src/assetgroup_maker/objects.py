import ast
from src.settings.common import get_settings_value, set_settings_value

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