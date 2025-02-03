from PySide6.QtWidgets import QMessageBox
from src.other.NCM_mode_setup_main import NCM_mode_setup
from src.other.assettypes import asset_types_modify
from src.settings.main import get_addon_name, get_cs2_path, get_config_bool, set_config_bool, get_config_value, \
    set_config_value
import shutil, psutil
from src.common import *
from src.widgets import exception_handler


@exception_handler
def delete_addon(ui, cs2_path, get_addon_name):
    delete_paths = [
        os.path.join(cs2_path, 'content', 'csgo_addons', get_addon_name()),
        os.path.join(cs2_path, 'game', 'csgo_addons', get_addon_name())
    ]
    addon_name = get_addon_name()
    reply = QMessageBox.question(None, 'Remove Addon', f"Are you sure you want to permanently delete the addon '{addon_name}'? This action cannot be undone.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if reply == QMessageBox.Yes:
        try:
            for path in delete_paths:
                if os.path.exists(path):
                    shutil.rmtree(path)
                    print(f'Successfully deleted: {path}')
                else:
                    print(f'Path does not exist: {path}')
            # Remove the item from ComboBoxSelectAddon
            index = ui.ComboBoxSelectAddon.findText(addon_name)
            if index != -1:
                ui.ComboBoxSelectAddon.removeItem(index)
            QMessageBox.information(None, 'Addon Deleted', f"The addon '{addon_name}' has been successfully deleted.")
        except Exception as e:
            QMessageBox.critical(None, 'Deletion Failed', f"Failed to delete the addon '{addon_name}'. You may need administrative permissions.\nError: {str(e)}")
    else:
        print('Addon deletion cancelled')

def assemble_commands(commands:str, addon_name):
    return commands.replace('addon_name', addon_name)
def __launch_addon():
    addon_name = get_addon_name()
    cs2_path = get_cs2_path()

    commands = get_config_value("LAUNCH", "commands")
    if not commands:
        commands = default_commands
        set_config_value("LAUNCH", "commands", commands)

    commands = assemble_commands(commands, addon_name)

    cs2_exe_path = os.path.join(cs2_path, "game", "bin", "win64", "cs2.exe")

    cs2_launch_commands = f'"{cs2_exe_path}" {commands}'

    ncm_mode = get_config_bool("LAUNCH", "ncm_mode", default=False)

    if ncm_mode:
        NCM_mode_setup(cs2_path)
        launch_command = f'{cs2_launch_commands} -nocustomermachine'
    else:
        launch_command = cs2_launch_commands

    psutil.Popen(
        launch_command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )


@exception_handler
def launch_addon():
    asset_types_modify()
    __launch_addon()


def kill_addon():
    subprocess.run(["taskkill", "/f", "/im", "cs2.exe"])