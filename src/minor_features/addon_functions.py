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

    supports_ray_tracing = False

    # Check for NVIDIA GPU
    try:
        py3nvml.nvmlInit()
        try:
            handle = py3nvml.nvmlDeviceGetHandleByIndex(0)
            gpu_name = py3nvml.nvmlDeviceGetName(handle)
            supports_ray_tracing = "RTX" in gpu_name
        finally:
            py3nvml.nvmlShutdown()
    except py3nvml.NVMLError as e:
        print(f"NVML Error: {e}")

    # Check for AMD GPU
    if not supports_ray_tracing:
        try:
            # Use subprocess to run a command that lists GPU information
            result = subprocess.run(['lspci'], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if "VGA compatible controller" in line and "AMD" in line:
                    if "Radeon" in line and "RX" in line:
                        supports_ray_tracing = True
                        break
        except Exception as e:
            print(f"AMD GPU Info Error: {e}")

    # Check for Intel GPU
    if not supports_ray_tracing:
        try:
            # Attempt to run intel_gpu_top to check for Intel GPU
            result = subprocess.run(['intel_gpu_top', '-l'], capture_output=True, text=True)
            if "Intel" in result.stdout:
                # Simplified check for ray tracing support
                supports_ray_tracing = "Xe" in result.stdout
        except Exception as e:
            print(f"Intel GPU Info Error: {e}")

    # Construct the launch command
    cs2_launch_commands = (
        '"' + cs2_path + '"' + r"\game\bin\win64\cs2.exe" +
        " -addon " + addon_name +
        ' -tool hammer' +
        ' -asset maps/' + addon_name + '.vmap' +
        " -tools -steam -retail -noinsecru +install_dlc_workshoptools_cvar 1"
        + '-gpuraytracing'
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