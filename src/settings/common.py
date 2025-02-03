import os
from PySide6.QtCore import QSettings

from src.other.get_cs2_path_from_registry import get_counter_strike_path_from_registry, get_steam_install_path

# Define the application directory
app_dir = os.getcwd()
settings_file = os.path.join(app_dir, 'settings.ini')

# Initialize settings to use settings.ini in the program folder
settings = QSettings(settings_file, QSettings.IniFormat)

def set_config_value(section, key, value):
    settings.setValue(f"{section}/{key}", value)

def set_config_bool(section, key, bool_value):
    set_config_value(section, key, bool_value)


def get_config_value(section, key, default=None):
    config_key = f"{section}/{key}"
    try:
        value = settings.value(config_key, defaultValue=default)
    except Exception as error:
        if default is None:
            raise ValueError(f"Error retrieving configuration for '{config_key}': {error}") from error
        return default

    return value


def get_config_bool(section, key, default: bool = None):
    config_key = f"{section}/{key}"
    try:
        value = settings.value(config_key, defaultValue=default, type=bool)
    except Exception as error:
        if default is None:
            raise ValueError(f"Error retrieving boolean configuration for '{config_key}': {error}") from error
        return default

    if value is None and default is None:
        raise ValueError(f"Boolean configuration for '{config_key}' not found.")
    return value

def default_settings():
    if not os.path.exists(settings.fileName()):
        desktop_user_path = os.path.join(os.path.expanduser("~"), "Desktop")
        set_config_value('PATHS', 'archive', desktop_user_path)
        set_config_value('DISCORD_STATUS', 'custom_status', 'Doing stuff')
        set_config_value('DISCORD_STATUS', 'show_status', True)
        set_config_value('DISCORD_STATUS', 'show_project_name', False)
        set_config_value('LAUNCH', 'ncm_mode', False)
        set_config_value('AssetGroupMaker', 'monitor_folders', 'models, materials, smartprops')
        set_config_bool('SoundEventEditor', 'play_on_click', True)
        set_config_bool('LAUNCH', 'ncm_mode_setup', False)
        set_config_bool('APP', 'minimize_message_shown', True)
        set_config_bool('APP', 'start_with_system', False)
        set_config_bool('APP', 'first_launch', True)
        set_config_bool('APP', 'minimize_to_tray', True)
        set_config_bool('OTHER', 'launch_addon_after_nosteamlogon_fix', False)
        settings.sync()

default_settings()

# Debug function
def debug(value):
    if settings.value("OTHER/debug_info", type=bool, defaultValue=False):
        print(value)

def get_cs2_path():
    """
    Retrieves the CS2 installation path without saving it back to the settings.
    """
    def cs2_exe_exists(cs2_path):
        cs2_exe_path = os.path.join(cs2_path, "game", "bin", "win64", "cs2.exe")
        return os.path.exists(cs2_exe_path)

    cs2_path = get_config_value('PATHS', 'Cs2')

    if cs2_path:
        cs2_path = os.path.normpath(cs2_path)
        if cs2_exe_exists(cs2_path):
            return cs2_path
        else:
            cs2_path = None

    if not cs2_path:
        cs2_path = get_counter_strike_path_from_registry()
        if cs2_path:
            cs2_path = os.path.normpath(cs2_path)
            if cs2_exe_exists(cs2_path):
                return cs2_path
            else:
                cs2_path = None

    return cs2_path

def get_steam_path():
    """
    Retrieves the Steam installation path without saving it back to the settings.
    """
    try:
        steam_path = get_config_value('PATHS', 'steam')
        if not steam_path:
            raise ValueError("Steam path not found or empty")
        return steam_path
    except:
        steam_path = get_steam_install_path()
        if not steam_path:
            raise ValueError("Cannot find Steam path, and none set in config.")
        return steam_path

def get_addon_dir():
    try:
        cs2_path = get_cs2_path()
        addon_name = get_addon_name()
        if not addon_name:
            raise ValueError("Addon name not found or empty in configuration.")
        return os.path.join(cs2_path, 'content', 'csgo_addons', addon_name)
    except Exception as e:
        debug(f"Error retrieving addon directory: {e}")
        raise

def get_addon_name():
    return get_config_value('LAUNCH', 'addon')

def set_addon_name(addon_name_set):
    return set_config_value('LAUNCH', 'addon', addon_name_set)