from pathlib import Path
import sys
from PySide6.QtCore import QSettings

from gui.other.get_cs2_path import get_counter_strike_path_from_registry, get_steam_install_path
from gui.common import user_data_dir, app_dir

settings_file = user_data_dir / 'settings.ini'

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
        set_settings_bool('APP', 'show_about_on_startup', True)
        set_settings_bool('APP', 'show_project_structure_warning', True)
        set_settings_value('APP', 'theme_level', 2)
        settings.sync()

default_settings()

# APP/brightness_level was renamed to APP/theme_level; carry the existing
# selection over so the rename does not reset anyone to Standard.
_legacy_level = settings.value('APP/brightness_level')
if _legacy_level is not None:
    if settings.value('APP/theme_level') is None:
        set_settings_value('APP', 'theme_level', _legacy_level)
    settings.remove('APP/brightness_level')
    settings.sync()

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

def _addon_dir(root, addon):
    """<cs2>/<root>/csgo_addons/<addon>, or None if either half is unset."""
    cs2_path = get_cs2_path()
    addon = addon or get_addon_name()
    if not cs2_path or not addon:
        return None
    return Path(cs2_path) / root / 'csgo_addons' / addon


def cs2_addons_dir(root: str = 'content', cs2_path: str | None = None) -> Path | None:
    """The CS2 addon root for *root* (``content`` or ``game``)."""
    if root not in {'content', 'game'}:
        raise ValueError(f"Unsupported CS2 addon root: {root}")
    cs2_path = cs2_path or get_cs2_path()
    return Path(cs2_path) / root / 'csgo_addons' if cs2_path else None


def addon_content_dir(addon: str | None = None) -> Path | None:
    """Source assets: models, materials, smartprops, sounds."""
    return _addon_dir('content', addon)


def addon_game_dir(addon: str | None = None) -> Path | None:
    """Compiled output the game loads."""
    return _addon_dir('game', addon)


def cs2_bin_dir() -> Path | None:
    """<cs2>/game/bin/win64 - cs2.exe and resourcecompiler.exe live here."""
    cs2_path = get_cs2_path()
    return Path(cs2_path) / 'game' / 'bin' / 'win64' if cs2_path else None


def get_addon_dir():
    """String form of addon_content_dir(), for the call sites that join onto it."""
    directory = addon_content_dir()
    return str(directory) if directory else None
