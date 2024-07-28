import zipfile
from PySide6.QtWidgets import QMessageBox, QProgressDialog
from PySide6.QtGui import Qt, QIcon
from preferences import get_config_value
from minor_features.NCM_mode_setup_main import NCM_mode_setup
from preferences import get_addon_name, get_cs2_path, get_config_bool, set_config_bool
import os, subprocess, shutil, psutil

def archive_addon(cs2_path, get_addon_name):
    reply = QMessageBox.question(None, 'Archive addon', f"Are you sure you want to archive '{get_addon_name()}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if reply == QMessageBox.Yes:
        addon_name = get_addon_name()
        delete_paths = [
            os.path.join(cs2_path, 'game', 'csgo_addons', addon_name, '_vrad3'),
            os.path.join(cs2_path, 'game', 'csgo_addons', addon_name, '_bakeresourcecache')
        ]

        # Delete the specified paths
        for path in delete_paths:
            if os.path.exists(path):
                shutil.rmtree(path)
                print(f'Moved {path} to the bin')
            else:
                print(f'Path does not exist: {path}')

        # Archive the addon
        archive_path = get_config_value('PATHS', 'archive')
        game_source_path = os.path.join(cs2_path, 'game', 'csgo_addons', addon_name)
        content_source_path = os.path.join(cs2_path, 'content', 'csgo_addons', addon_name)
        destination_path = os.path.join(archive_path, addon_name + '.zip')

        try:
            # Collect all files to be archived
            files_to_archive = []
            for root, dirs, files in os.walk(game_source_path):
                for file in files:
                    files_to_archive.append(os.path.join(root, file))
            for root, dirs, files in os.walk(content_source_path):
                for file in files:
                    files_to_archive.append(os.path.join(root, file))

            # Initialize progress dialog
            progress_dialog = QProgressDialog("Archiving files...", "Cancel", 0, len(files_to_archive))
            progress_dialog.setWindowTitle("Archiving Progress")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setWindowIcon(QIcon(":/icons/appicon.ico"))  # Set the icon

            with zipfile.ZipFile(destination_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for i, file_path in enumerate(files_to_archive):
                    if progress_dialog.wasCanceled():
                        raise Exception("Archiving canceled by user")
                    arcname = os.path.relpath(file_path, cs2_path)
                    zipf.write(file_path, arcname)
                    progress_dialog.setValue(i + 1)

            print(f'Archived {game_source_path} and {content_source_path} to {destination_path}')

        except Exception as e:
            QMessageBox.information(None, 'Archive Failed', f'Failed to archive the addon.\nError: {str(e)}')
    else:
        print('Archiving cancelled')


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


def launch_addon():
    addon_name = get_addon_name()
    cs2_path = get_cs2_path()
    cs2_launch_commands = '"' + cs2_path + '"' + r"\game\bin\win64\cs2.exe" + " -addon " + addon_name + ' -tool hammer' + ' -asset maps/' + addon_name + '.vmap' + " -tools -steam -retail -gpuraytracing  -noinsecru +install_dlc_workshoptools_cvar 1"
    if get_config_bool('LAUNCH', 'ncm_mode'):
        if get_config_bool('LAUNCH', 'ncm_mode_setup'):
            psutil.Popen((cs2_launch_commands + " -nocustomermachine"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            NCM_mode_setup(cs2_path)
            psutil.Popen((cs2_launch_commands + " -nocustomermachine"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            set_config_bool('LAUNCH', 'ncm_mode_setup', 'True')
    else:
        psutil.Popen(cs2_launch_commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)