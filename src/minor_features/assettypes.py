import os
from src.preferences import get_cs2_path
import keyvalues3
from src.common import editor_info

def load_assettypes():
    file_path = os.path.join(get_cs2_path(), 'game', 'bin', 'assettypes_common.txt')
    try:
        data_dict = keyvalues3.read(file_path).value
        return file_path, data_dict
    except:
        raise ValueError

def is_editor_info_processed(data):
    processed = data.get('editor_info')
    return isinstance(processed, list)

def add_vsmart_block(data):
    vsmart_block = {
        'smart_prop': {
            '_class': 'CResourceAssetTypeInfo',
            'm_FriendlyName': 'Smart Prop',
            'm_Ext': 'vsmart',
            'm_IconLg': 'game:tools/images/assettypes/smart_prop_lg.png',
            'm_IconSm': 'game:tools/images/assettypes/smart_prop_sm.png',
            'm_CompilerIdentifier': 'CompileVData',
            'm_Blocks': [
                {'m_BlockID': 'DATA', 'm_Encoding': 'RESOURCE_ENCODING_KV3'}
            ]
        }
    }
    if 'assettypes' not in data:
        data['assettypes'] = {}
    data['assettypes'].update(vsmart_block)
    return data

def asset_types_modify():
    file_path, data = load_assettypes()
    if not data:
        return
    if not is_editor_info_processed(data):
        updated_data = add_vsmart_block(data)
        merged_data = dict(editor_info, **updated_data)
        keyvalues3.write(merged_data, file_path)
    else:
        pass