from pathlib import Path
import sys
from PySide6.QtCore import QSettings

from src.other.get_cs2_path import get_counter_strike_path_from_registry, get_steam_install_path
from src.common import user_data_dir, app_dir

settings_file = user_data_dir / 'settings.ini'

# Initialize settings
settings = QSettings(str(settings_file), QSettings.IniFormat)

def set_settings_value(section, key, value):
    settings.setValue(f"{section}/{key}", value)

def set_settings_bool(section, key, bool_value):
    set_settings_value(section, key, bool_value)

def get_settings_value(section, key, default=None):
    config_key = f"{section}/{key}"
    try:
        value = settings.value(config_key, defaultValue=default)
    except Exception as error:
        if default is None:
            raise ValueError(f"Error retrieving configuration for '{config_key}': {error}") from error
        return default
    return value

def get_settings_bool(section, key, default: bool = None):
    config_key = f"{section}/{key}"
    try:
        value = settings.value(config_key, defaultValue=default, type=bool)
    except Exception as error:
        if default is None:
            raise ValueError(f"Error retrieving boolean configuration for '{config_key}': {error}") from error
        return default
    return value

def default_settings():
    if not settings_file.exists():
        desktop_user_path = str(Path.home() / "Desktop")
        set_settings_value('PATHS', 'archive', desktop_user_path)
        set_settings_value('LAUNCH', 'ncm_mode', False)
        set_settings_value('AssetGroupMaker', 'monitor_folders', 'models, materials, smartprops')
        set_settings_bool('SoundEventEditor', 'play_on_click', True)
        set_settings_bool('LAUNCH', 'ncm_mode_setup', False)
        set_settings_bool('APP', 'minimize_message_shown', True)
        set_settings_bool('APP', 'first_launch', True)
        set_settings_bool('APP', 'minimize_to_tray', False)
        settings.sync()

default_settings()

def debug(value):
    if settings.value("OTHER/debug_info", type=bool, defaultValue=False):
        print(value)

def debug_bool():
    return settings.value("OTHER/debug_info", type=bool, defaultValue=False)

def get_cs2_path():
    """Retrieves the CS2 installation path."""
    def cs2_exe_exists(path):
        if not path or Path(path) == app_dir:
            return False
        return (Path(path) / "game" / "bin" / "win64" / "cs2.exe").exists()

    manual_path = get_settings_value('PATHS', 'manual_cs2_path')
    if manual_path:
        manual_path = str(Path(manual_path))
        if cs2_exe_exists(manual_path):
            return manual_path

    reg_path = get_counter_strike_path_from_registry()
    if reg_path:
        reg_path = str(Path(reg_path))
        if cs2_exe_exists(reg_path):
            return reg_path
    return None

def set_manual_cs2_path(path):
    set_settings_value('PATHS', 'manual_cs2_path', path)

def get_manual_cs2_path():
    return get_settings_value('PATHS', 'manual_cs2_path')

def get_steam_path():
    try:
        return get_steam_install_path()
    except:
        return None

def get_addon_name():
    return get_settings_value('LAUNCH', 'addon', default='addon')

def set_addon_name(addon_name):
    set_settings_value('LAUNCH', 'addon', addon_name)

def get_addon_dir():
    cs2_path = get_cs2_path()
    if not cs2_path:
        return None
    
    addon_name = get_addon_name()
    if not addon_name:
        return None
        
    return str(Path(cs2_path) / 'content' / 'csgo_addons' / addon_name)