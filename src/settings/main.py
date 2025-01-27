import os
import subprocess
import winreg as reg
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import QSettings

try:
    from src.settings.ui_main import Ui_preferences_dialog
except:
    pass

from src.other.get_cs2_path_from_registry import get_counter_strike_path_from_registry, get_steam_install_path
from src.other.NCM_mode_setup_main import NCM_mode_setup
from src.other.update_check import check_updates
from src.common import Presets_Path, enable_dark_title_bar

# Define the application directory
app_dir = os.getcwd()
settings_file = os.path.join(app_dir, 'settings.ini')

# Initialize settings to use settings.ini in the program folder
settings = QSettings(settings_file, QSettings.IniFormat)

def set_config_value(section, key, value):
    settings.setValue(f"{section}/{key}", value)

def set_config_bool(section, key, bool_value):
    set_config_value(section, key, bool_value)

def get_config_value(section, key):
    return settings.value(f"{section}/{key}")

def get_config_bool(section, key, default: bool = None):
    if default is None:
        try:
            return settings.value(f"{section}/{key}", type=bool)
        except:
            raise ValueError
    else:
        try:
            return settings.value(f"{section}/{key}", type=bool)
        except:
            return default

def default_settings():
    if not os.path.exists(settings.fileName()):
        desktop_user_path = os.path.join(os.path.expanduser("~"), "Desktop")
        set_config_value('PATHS', 'archive', desktop_user_path)
        set_config_value('DISCORD_STATUS', 'custom_status', 'Doing stuff')
        set_config_value('DISCORD_STATUS', 'show_status', True)
        set_config_value('DISCORD_STATUS', 'show_project_name', False)
        set_config_value('LAUNCH', 'ncm_mode', False)
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
                set_config_value('PATHS', 'Cs2', cs2_path)
                return cs2_path
            else:
                cs2_path = None

    return cs2_path

def get_steam_path():
    try:
        steam_path = get_config_value('PATHS', 'steam')
        if not steam_path:
            raise ValueError("Steam path not found or empty")
        return steam_path
    except:
        steam_path = get_steam_install_path()
        set_config_value('PATHS', 'steam', steam_path)
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

class PreferencesDialog(QDialog):

    def __init__(self, app_version, parent=None):
        super().__init__(parent)
        self.ui = Ui_preferences_dialog()
        self.ui.setupUi(self)

        self.app_version = app_version
        enable_dark_title_bar(self)

        # Populate UI with current preferences
        self.populate_preferences()

        # Connect signals to slots for immediate updates
        self.connect_signals()

        # Set version label
        self.ui.version_label.setText(f"Version: {app_version}")

    def populate_preferences(self):
        self.ui.preferences_lineedit_archive_path.setText(get_config_value('PATHS', 'archive'))
        # Discord status
        self.ui.checkBox_show_in_hammer_discord_status.setChecked(get_config_bool('DISCORD_STATUS', 'show_status'))
        self.ui.checkBox_hide_project_name_discord_status.setChecked(get_config_bool('DISCORD_STATUS', 'show_project_name'))
        self.ui.editline_custom_discord_status.setText(get_config_value('DISCORD_STATUS', 'custom_status'))
        # Other
        self.ui.launch_addon_after_nosteamlogon_fix.setChecked(get_config_bool('OTHER', 'launch_addon_after_nosteamlogon_fix'))
        # App
        self.ui.checkBox_start_with_system.setChecked(get_config_bool('APP', 'start_with_system'))
        self.ui.checkBox_close_to_tray.setChecked(get_config_bool('APP', 'minimize_to_tray', True))
        # SmartProp Editor
        self.ui.spe_display_id_with_variable_class.setChecked(get_config_bool('SmartPropEditor', 'display_id_with_variable_class', False))

    def connect_signals(self):
        self.ui.preferences_lineedit_archive_path.textChanged.connect(
            lambda: set_config_value('PATHS', 'archive', self.ui.preferences_lineedit_archive_path.text())
        )

        self.ui.checkBox_show_in_hammer_discord_status.toggled.connect(
            lambda: set_config_bool('DISCORD_STATUS', 'show_status', self.ui.checkBox_show_in_hammer_discord_status.isChecked())
        )
        self.ui.checkBox_hide_project_name_discord_status.toggled.connect(
            lambda: set_config_bool('DISCORD_STATUS', 'show_project_name', self.ui.checkBox_hide_project_name_discord_status.isChecked())
        )
        self.ui.editline_custom_discord_status.textChanged.connect(
            lambda: set_config_value('DISCORD_STATUS', 'custom_status', self.ui.editline_custom_discord_status.text())
        )

        self.ui.launch_addon_after_nosteamlogon_fix.toggled.connect(
            lambda: set_config_bool('OTHER', 'launch_addon_after_nosteamlogon_fix', self.ui.launch_addon_after_nosteamlogon_fix.isChecked())
        )

        self.ui.checkBox_start_with_system.toggled.connect(self.start_with_system)
        self.ui.checkBox_close_to_tray.toggled.connect(
            lambda: set_config_bool('APP', 'minimize_to_tray', self.ui.checkBox_close_to_tray.isChecked())
        )

        self.ui.spe_display_id_with_variable_class.toggled.connect(
            lambda: set_config_bool('SmartPropEditor', 'display_id_with_variable_class', self.ui.spe_display_id_with_variable_class.isChecked())
        )

        # Connect buttons to their respective methods
        self.ui.open_settings_folder_button.clicked.connect(self.open_settings_folder)
        self.ui.setup_ncm_mode.clicked.connect(self.setup_ncm_mode)
        self.ui.open_presets_folder_button.clicked.connect(self.open_presets_folder)
        self.ui.check_update_button.clicked.connect(self.check_update)

    def open_settings_folder(self):
        subprocess.Popen(f'explorer "{app_dir}"')

    def setup_ncm_mode(self):
        NCM_mode_setup(cs2_path=get_cs2_path())
        set_config_bool('LAUNCH', 'ncm_mode_setup', True)

    def start_with_system(self):
        path_to_exe = os.path.join(app_dir, 'hammer5tools.exe')
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "Hammer5Tools"

        if self.ui.checkBox_start_with_system.isChecked():
            if os.path.exists(path_to_exe):
                try:
                    with reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_SET_VALUE) as reg_key:
                        reg.SetValueEx(reg_key, app_name, 0, reg.REG_SZ, path_to_exe)
                    print(f"Successfully added {path_to_exe} to startup")
                except Exception as e:
                    print(f"Failed to add {path_to_exe} to startup: {e}")
            else:
                print("Executable not found at the specified path")
        else:
            try:
                with reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_SET_VALUE | reg.KEY_WRITE) as reg_key:
                    reg.DeleteValue(reg_key, app_name)
                print(f"Successfully removed {app_name} from startup")
            except FileNotFoundError:
                print(f"{app_name} not found in startup")
            except Exception as e:
                print(f"Failed to remove {app_name} from startup: {e}")

    def open_presets_folder(self):
        os.startfile(Presets_Path)

    def check_update(self):
        check_updates("https://github.com/dertwist/Hammer5Tools", self.app_version, False)