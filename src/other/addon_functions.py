from PySide6.QtWidgets import QMessageBox
from src.other.ncm_setup import NCM_mode_setup
from src.other.assettypes import ensure_vsmart_configured
from src.settings.main import get_addon_name, get_cs2_path, get_settings_bool, set_settings_bool, get_settings_value, \
    set_settings_value
import shutil, psutil
from src.common import *
from src.widgets import exception_handler


@exception_handler
def delete_addon(ui, cs2_path, get_addon_name):
    if cs2_path is None:
        QMessageBox.warning(None, "CS2 Path Not Set", 
                          "CS2 installation path is not set. Please set it in Settings > General > CS2 Path.")
        return
        
    addon_name = get_addon_name()
    if not addon_name:
        QMessageBox.warning(None, "No Addon Selected", 
                          "No addon is selected for deletion.")
        return
        
    delete_paths = [
        os.path.join(cs2_path, 'content', 'csgo_addons', addon_name),
        os.path.join(cs2_path, 'game', 'csgo_addons', addon_name)
    ]
    
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
    
    if cs2_path is None:
        QMessageBox.warning(None, "CS2 Path Not Set", 
                          "CS2 installation path is not set. Please set it in Settings > General > CS2 Path.")
        return
        
    if not addon_name:
        QMessageBox.warning(None, "No Addon Selected", 
                          "No addon is selected for launch.")
        return

    commands = get_settings_value("LAUNCH", "commands")
    if not commands:
        commands = default_commands
        set_settings_value("LAUNCH", "commands", commands)

    commands = assemble_commands(commands, addon_name)
    
    # Ensure -netconport 2121 is always included (mandatory flag)
    if '-netconport' not in commands:
        commands += ' -netconport 2121'

    # Ensure -disable_workshop_command_filtering is always included (mandatory flag)
    if '-disable_workshop_command_filtering' not in commands:
        commands += ' -disable_workshop_command_filtering'

    cs2_exe_path = os.path.join(cs2_path, "game", "bin", "win64", "cs2.exe")
    
    if not os.path.exists(cs2_exe_path):
        QMessageBox.warning(None, "CS2 Executable Not Found", 
                          f"CS2 executable not found at:\n{cs2_exe_path}\n\n"
                          "Please verify your CS2 installation path in Settings.")
        return

    cs2_launch_commands = f'"{cs2_exe_path}" {commands}'

    ncm_mode = get_settings_bool("LAUNCH", "ncm_mode", default=False)

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
def configure_particle_editor():
    """
    Automatically configure the Particle Editor in sdkenginetools.txt.
    Finds the "pet" (Particle Editor) entry and removes any m_ExcludeFromMods
    restriction to ensure it's available for CS:GO addons.
    """
    cs2_path = get_cs2_path()
    if cs2_path is None:
        return

    sdk_tools_path = os.path.join(cs2_path, "game", "bin", "sdkenginetools.txt")

    if not os.path.exists(sdk_tools_path):
        return

    try:
        import re

        with open(sdk_tools_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        modified = False
        inside_pet = False
        inside_exclude = False
        skip_lines = []

        for i, line in enumerate(lines):
            if 'm_Name = "pet"' in line:
                inside_pet = True
            if inside_pet and re.match(r'^\s*\},?\s*$', line):
                inside_pet = False

            if inside_pet and 'm_ExcludeFromMods' in line:
                inside_exclude = True
                skip_lines.append(i)
                modified = True

            elif inside_exclude:
                skip_lines.append(i)
                if ']' in line:
                    inside_exclude = False

        if modified:
            new_lines = [line for i, line in enumerate(lines) if i not in skip_lines]

            with open(sdk_tools_path, 'w', encoding='utf-8') as file:
                file.writelines(new_lines)

    except Exception as e:
        pass


@exception_handler
def launch_addon():
    ensure_vsmart_configured()
    configure_particle_editor()
    __launch_addon()


def kill_addon():
    subprocess.run(["taskkill", "/f", "/im", "cs2.exe"])