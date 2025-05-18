import os
from PySide6.QtWidgets import QMessageBox
from src.settings.main import get_cs2_path
from src.common import editor_info
import keyvalues3

ASSETTYPES_FILENAME = 'assettypes_common.txt'
VSMART_BLOCK = {
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


def get_assettypes_path():
    return os.path.join(get_cs2_path(), 'game', 'bin', ASSETTYPES_FILENAME)


def read_assettypes():
    file_path = get_assettypes_path()
    try:
        data = keyvalues3.read(file_path).value
        return file_path, data
    except Exception as e:
        raise ValueError(f"Failed to read assettypes: {e}")


def is_editor_info_processed(data):
    return isinstance(data.get('editor_info'), dict)


def add_vsmart_block(data):
    data = data.copy()
    assettypes = data.setdefault('assettypes', {})
    assettypes.update(VSMART_BLOCK)
    return data


def write_assettypes(data, file_path):
    keyvalues3.write(data, file_path)


def ensure_vsmart_configured():
    file_path, data = read_assettypes()
    if not is_editor_info_processed(data):
        updated_data = add_vsmart_block(data)
        merged_data = {**editor_info, **updated_data}
        write_assettypes(merged_data, file_path)


def show_vsmart_warning():
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Warning)
    msg_box.setWindowTitle('Smart Prop (vsmart) Not Configured')
    msg_box.setText('The Cs2 editor is not yet configured for Smart Prop compilation.')
    msg_box.setInformativeText(
        'To enable vsmart file compilation, please launch the tools using this application.\n'
        'Ensure Counter-Strike 2 is closed, then reopen it through this application.'
    )
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec()


def check_vsmart_configuration():
    _, data = read_assettypes()
    if not is_editor_info_processed(data):
        show_vsmart_warning()