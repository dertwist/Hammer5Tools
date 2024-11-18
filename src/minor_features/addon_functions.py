from PySide6.QtWidgets import QMessageBox
from src.minor_features.NCM_mode_setup_main import NCM_mode_setup
from src.minor_features.assettypes import AssetTypesModify
from src.preferences import get_addon_name, get_cs2_path, get_config_bool, set_config_bool
import os, subprocess, shutil, psutil
from src.widgets import ErrorInfo, ExpetionErrorDialog
from py3nvml import py3nvml


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

def __launch_addon():
    addon_name = get_addon_name()
    cs2_path = get_cs2_path()

    # Initialize NVML
    py3nvml.nvmlInit()
    try:
        # Get the handle for the first GPU
        handle = py3nvml.nvmlDeviceGetHandleByIndex(0)
        # Get the GPU name
        gpu_name = py3nvml.nvmlDeviceGetName(handle)
        # Check if the GPU supports ray tracing
        # This is a simplified check; you might need a more specific check based on your requirements
        supports_ray_tracing = "RTX" in gpu_name
    finally:
        # Shutdown NVML
        py3nvml.nvmlShutdown()

    # Construct the launch command
    cs2_launch_commands = (
        '"' + cs2_path + '"' + r"\game\bin\win64\cs2.exe" +
        " -addon " + addon_name +
        ' -tool hammer' +
        ' -asset maps/' + addon_name + '.vmap' +
        " -tools -steam -retail -noinsecru +install_dlc_workshoptools_cvar 1"
    )

    # Add the -gpuraytracing command if the GPU supports ray tracing
    if supports_ray_tracing:
        cs2_launch_commands += " -gpuraytracing"

    if get_config_bool('LAUNCH', 'ncm_mode'):
        if get_config_bool('LAUNCH', 'ncm_mode_setup'):
            psutil.Popen((cs2_launch_commands + " -nocustomermachine"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            NCM_mode_setup(cs2_path)
            psutil.Popen((cs2_launch_commands + " -nocustomermachine"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            set_config_bool('LAUNCH', 'ncm_mode_setup', True)
    else:
        psutil.Popen(cs2_launch_commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
def launch_addon():
    ExpetionErrorDialog(AssetTypesModify, 'AssetTypesModify')
    ExpetionErrorDialog(__launch_addon, 'LaunchAddon')

def kill_addon():
    subprocess.run(["taskkill", "/f", "/im", "cs2.exe"])