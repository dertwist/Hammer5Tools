import os
from src.preferences import get_cs2_path, debug
import keyvalues3
from src.common import editor_info

def asset_types_modify():
    # Initialize variables
    process = False
    processed = None
    output = {}
    vsmart_block = {}
    data = {}
    path = os.path.join(get_cs2_path(), 'game', 'bin', 'assettypes_common.txt')
    debug(path)

    # Load the file
    data.update(keyvalues3.read(path).value)

    # Check if 'editor_info' is already processed
    processed = data.get('editor_info', None)
    debug(f'Process var: {type(processed)}')
    if isinstance(processed, list):
        process = False
    else:
        process = True

    if process:
        debug('Adding custom asset types to cs2 cfg')
        debug(process)

        # Add vsmart block
        vsmart_block = {
            'smart_prop': {
                '_class': 'CResourceAssetTypeInfo',
                'm_FriendlyName': 'Smart Prop',
                'm_Ext': 'vsmart',
                'm_IconLg': 'game:tools/images/assettypes/smart_prop_lg.png',
                'm_IconSm': 'game:tools/images/assettypes/smart_prop_sm.png',
                'm_CompilerIdentifier': 'CompileVData',
                'm_Blocks': [
                    {
                        'm_BlockID': 'DATA',
                        'm_Encoding': 'RESOURCE_ENCODING_KV3'
                    }
                ]
            }
        }
        data['assettypes'].update(vsmart_block)
        debug('Added vsmart asset type')

        # Prepare output data
        output = editor_info
        output.update(data)

        # Write the updated data back to the file
        keyvalues3.write(output, path)