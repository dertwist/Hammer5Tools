import os.path
from preferences import get_cs2_path, debug
import keyvalues3
from common import editor_info
class AssetTypesModify:
    def __init__(self):
        super().__init__()
        # Variables
        self.process = False
        self.data = {}
        self.path = os.path.join(get_cs2_path(), 'game', 'bin', 'assettypes_common.txt')
        debug(self.path)

        self.load_file()
        self.check_processed()


    def load_file(self):
        self.data.update(keyvalues3.read(self.path).value)
    def check_processed(self):
        processed = self.data.get('editor_info', None)
        debug(f'Process var: {type(processed)}')
        if isinstance(processed, list):
            self.process = False
        else:
            self.process = True
        if self.process:
            debug(f'Adding custom asset types to cs2 cfg')
            debug(self.process)
            self.add_vsmart()
            output = editor_info
            output.update(self.data)
            keyvalues3.write(output, self.path)
    def add_vsmart(self):
        vsmart_block = {'smart_prop': {'_class': 'CResourceAssetTypeInfo', 'm_FriendlyName': 'Smart Prop', 'm_Ext': 'vsmart', 'm_IconLg': 'game:tools/images/assettypes/smart_prop_lg.png', 'm_IconSm': 'game:tools/images/assettypes/smart_prop_sm.png', 'm_CompilerIdentifier': 'CompileVData', 'm_Blocks': [{'m_BlockID': 'DATA', 'm_Encoding': 'RESOURCE_ENCODING_KV3'}]}}
        self.data['assettypes'].update(vsmart_block)
        debug('Added vsmart asset type')