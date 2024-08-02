# This Python file uses the following encoding: utf-8

# if __name__ == "__main__":
#     pass

from PySide6.QtWidgets import QDialog
from ui_preferences import Ui_preferences_dialog
import os, configparser, subprocess
from distutils.util import strtobool
import webbrowser
from minor_features.get_cs2_path_from_registry import get_counter_strike_path_from_registry, get_steam_install_path
from minor_features.NCM_mode_setup_main import NCM_mode_setup
import winreg as reg

# config -------------------------------------------------------------------------------
# Get the path to the user's AppData directory
appdata_path = os.getenv('APPDATA')

# Define the path to the configuration directory
config_dir = os.path.join(appdata_path, 'DerTwist', 'Hammer5Tools')
# config_dir = os.path.join(appdata_path, 'DerTwist', 'Hammer5Tools')
app_dir = os.getcwd()

# Create the directory if it does not exist
os.makedirs(config_dir, exist_ok=True)

# Define the path to the configuration file
config_file_path = os.path.join(config_dir, 'settings.cfg')
# config_file_path = "settings.cfg"

# Initialize the ConfigParser
config = configparser.ConfigParser()



def set_config_value(section, key, value):
    if not config.has_section(section):
        config.add_section(section)
    config.set(section, key, value)
    with open(config_file_path, 'w') as configfile:
        config.write(configfile)

def set_config_bool(section,key, bool):
    return set_config_value(section, key, str(bool))

def get_config_value(section, key):
    if config.has_section(section) and config.has_option(section, key):
        return config.get(section, key)
    return None
def get_config_bool(section,key):
    return bool(strtobool(get_config_value(section, key)))


def default_settings():
    if os.path.exists(config_file_path):
        config.read(config_file_path)
    else:
        desktop_user_path = os.path.join(os.path.expanduser("~"), "Desktop")
        set_config_value('PATHS', 'archive', desktop_user_path)
        set_config_value('PATHS', 'settings', config_dir)
        set_config_value('PATHS', 'user_presets', (app_dir + '\\presets'))
        set_config_value('DISCORD_STATUS', 'custom_status', 'Doing stuff')
        set_config_value('DISCORD_STATUS', 'show_status', 'True')
        set_config_value('DISCORD_STATUS', 'show_project_name', 'False')
        set_config_value('LAUNCH', 'ncm_mode', 'False')
        set_config_bool('LAUNCH', 'ncm_mode_setup', 'False')
        set_config_bool('APP', 'minimize_message_shown', 'True')
        set_config_bool('APP', 'start_with_system', 'False')
        set_config_bool('APP', 'first_launch', 'True')
        os.makedirs(os.path.join(config_dir, 'presets'), exist_ok=True)
    print(f"Configuration file path: {config_file_path}")

default_settings()



# get preferences from registry, if it new user search path to cs2 and set it to registry
def get_cs2_path():
    try:
        # get_registry_value(settings_path, settings_key, "Cs2Path")
        counter_strikke_2_path = get_config_value('PATHS', 'Cs2')
        if not counter_strikke_2_path:
            raise ValueError("value cs2 not found or empty")
        return counter_strikke_2_path
    except:
        counter_strikke_2_path = (get_counter_strike_path_from_registry()).replace("\\\\", "\\")
        set_config_value('PATHS', 'Cs2', counter_strikke_2_path)
        return counter_strikke_2_path


def get_steam_path():
    try:
        steam_path = get_config_value('PATHS', 'steam')
        if not steam_path:
            raise ValueError("value steam not found or empty")
        return steam_path
    except:
        steam_path = get_steam_install_path()
        set_config_value('PATHS', 'steam', steam_path)
        return steam_path


def get_addon_name():
    return get_config_value('LAUNCH', 'addon')


def set_addon_name(addon_name_set):
    return set_config_value('LAUNCH', 'addon', addon_name_set)


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_preferences_dialog()
        self.ui.setupUi(self)






        try:
            # paths
            self.ui.preferences_lineedit_cs2_path.setText(get_cs2_path())
            self.ui.preferences_lineedit_steam_path.setText(get_steam_path())
            self.ui.preferences_lineedit_archive_path.setText(get_config_value('PATHS', 'archive'))
            self.ui.preferences_lineedit_user_presets_path.setText(get_config_value('PATHS', 'user_presets'))
            # discord_status
            self.ui.checkBox_show_in_hammer_discord_status.setChecked(get_config_bool('DISCORD_STATUS', 'show_status'))
            self.ui.checkBox_hide_project_name_discord_status.setChecked(get_config_bool('DISCORD_STATUS', 'show_project_name'))
            self.ui.editline_custom_discord_status.setText(get_config_value('DISCORD_STATUS', 'custom_status'))
            #     start with system
            self.ui.checkBox_start_with_system.setChecked(get_config_bool('APP', 'start_with_system'))
        except:
            pass



        # buttons
        self.ui.open_settings_folder_button.clicked.connect(self.open_settings_fodler)
        self.ui.preferences_apply_button.clicked.connect(self.apply_preferences)
        self.ui.setup_ncm_mode.clicked.connect(self.setup_ncm_mode)
        self.ui.open_presets_folder_button.clicked.connect(self.open_presets_folder)



    def apply_preferences(self):
        # paths
        set_config_value('PATHS', 'cs2', self.ui.preferences_lineedit_cs2_path.text())
        set_config_value('PATHS', 'steam', self.ui.preferences_lineedit_steam_path.text())
        set_config_value('PATHS', 'archive', self.ui.preferences_lineedit_archive_path.text())
        set_config_value('PATHS', 'user_presets', self.ui.preferences_lineedit_user_presets_path.text())

        # discord_status
        set_config_value('DISCORD_STATUS', 'show_status',str(self.ui.checkBox_show_in_hammer_discord_status.isChecked()))
        set_config_value('DISCORD_STATUS', 'show_project_name',str(self.ui.checkBox_hide_project_name_discord_status.isChecked()))
        set_config_value('DISCORD_STATUS', 'custom_status', self.ui.editline_custom_discord_status.text())



        #start with systenm
        set_config_bool('APP', 'start_with_system', self.ui.checkBox_start_with_system.isChecked())
        self.start_with_system()



    def open_settings_fodler(self):
        cfg_path = get_config_value('PATHS', 'settings')
        subprocess.Popen("explorer " + cfg_path)

    def setup_ncm_mode(self):
        NCM_mode_setup(cs2_path=get_cs2_path())
        set_config_bool('LAUNCH', 'ncm_mode_setup', 'True')

    def start_with_system(self):
        path_to_exe = get_config_value('PATHS', 'settings') + '\\' + 'hammer5tools.exe'
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "Hammer5Tools"

        if self.ui.checkBox_start_with_system.isChecked():
            if path_to_exe:
                try:
                    with reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_SET_VALUE) as reg_key:
                        reg.SetValueEx(reg_key, app_name, 0, reg.REG_SZ, path_to_exe)
                    print(f"Successfully added {path_to_exe} to startup")
                except Exception as e:
                    print(f"Failed to add {path_to_exe} to startup: {e}")
            else:
                print("Path to executable not found in configuration")
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
        path = get_config_value('PATHS', 'user_presets')
        subprocess.Popen(['explorer', path], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)