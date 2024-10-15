import os.path
from preferences import get_cs2_path, debug
import  keyvalues3 as kv3
from common import editor_info

path = os.path.join(get_cs2_path(), 'game', 'bin', 'assettypes_common.txt')
class AssetTypesProcess:
    def __init__(self):
        pass
        # Variables
        self.processed = True
        self.data = editor_info

        self.load_file()
        self.check_processed()

    def load_file(self):
        self.data.update(kv3.read(path).value)
    def check_processed(self):
        processed = self.data.get('editor_info', True)
        if isinstance(processed, dict):
            self.processed = True
        else:
            self.processed = False

        if self.processed:
            debug(f'Adding custom asset types to cs2 cfg')
            self.add_vsmart()
            self.save_file()
    def add_vsmart(self):
        vsmart_block = {'smart_prop': {'_class': 'CResourceAssetTypeInfo', 'm_FriendlyName': 'Smart Prop', 'm_Ext': 'vsmart', 'm_IconLg': 'game:tools/images/assettypes/smart_prop_lg.png', 'm_IconSm': 'game:tools/images/assettypes/smart_prop_sm.png', 'm_CompilerIdentifier': 'CompileVData', 'm_Blocks': [{'m_BlockID': 'DATA', 'm_Encoding': 'RESOURCE_ENCODING_KV3'}]}}
        self.data['assettypes'].update(vsmart_block)
        debug('Added vsmart asset type')
    def save_file(self):
        kv3.write(self.data, path)