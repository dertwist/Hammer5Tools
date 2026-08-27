import os
from gui.settings.common import get_addon_dir

def vsnd_case_convert(__value):
    __value_root, _ = os.path.splitext(__value)
    __value = __value_root + ".vsnd"
    __value = __value.replace('\\', '/')
    return __value
def vsnd_filepath_convert(__value):
    __value = vsnd_case_convert(os.path.relpath(__value, get_addon_dir()))
    __value = __value.replace('\\', '/')
    return __value