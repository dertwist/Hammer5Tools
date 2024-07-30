from export_and_import_addon.ui_export_and_import_addon import Ui_export_and_import_addon_widget
from preferences import get_cs2_path, get_addon_name, get_config_value
from PySide6.QtWidgets import QDialog

import os
import shutil
import zipfile
from PySide6.QtWidgets import QMessageBox, QProgressDialog
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
import math
from PySide6.QtWidgets import QFileDialog

from PySide6.QtGui import QStandardItemModel, QStandardItem

cs2_path = get_cs2_path()
exclude_game_folders = []
iclude_content_folders = []

class export_and_import_addon_dialog(QDialog):


    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_export_and_import_addon_widget()
        self.ui.setupUi(self)
        self.ui.export_addon_button.clicked.connect(self.do_export_addon)
        self.ui.import_addon_button.clicked.connect(self.do_import_addon)
        self.update_size_status()
        self.ui.skip_non_default_folders_in_content_checkbox.stateChanged.connect(self.update_size_status)
        self.ui.compiled_maps_checkbox.stateChanged.connect(self.update_size_status)
        self.ui.compiled_materials_checkbox.stateChanged.connect(self.update_size_status)
        self.ui.compiled_models_checkbox.stateChanged.connect(self.update_size_status)



    def exclude_include_folders(self):
        game_folder = os.path.join(cs2_path, 'game', 'csgo_addons', get_addon_name())
        content_folder = os.path.join(cs2_path, 'content', 'csgo_addons', get_addon_name())
        global exclude_game_folders
        global iclude_content_folders
        exclude_game_folders = ['tools_thumbnail_cache.bin']
        iclude_content_folders = []

        # Define the folders to exclude
        excluded_folders = {'panorama', 'postprocess', 'resource', 'smartprops', 'maps', 'materials', 'models', 'soundevents'}

        # List the directories in the root of game_folder
        for dir_name in os.listdir(game_folder):
            dir_path = os.path.join(game_folder, dir_name)
            if os.path.isdir(dir_path) and dir_name not in excluded_folders:
                base_name = os.path.basename(dir_path)
                name, extension = os.path.splitext(base_name)
                exclude_game_folders.append((name))

        if self.ui.compiled_maps_checkbox.isChecked():
            pass
        else:
            exclude_game_folders.append('maps')
        if self.ui.compiled_models_checkbox.isChecked():
            pass
        else:
            exclude_game_folders.append('models')
        if self.ui.compiled_materials_checkbox.isChecked():
            pass
        else:
            exclude_game_folders.append('materials')
        if self.ui.skip_non_default_folders_in_content_checkbox.isChecked():
            iclude_content_folders = ['maps', 'models', 'materials', 'postprocess', 'smartprops', 'soundevents','sounds']
    def do_export_addon(self):
        self.exclude_include_folders()
        self.archive_addon()

    def do_import_addon(self):
        # Open file dialog to choose a zip file
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Zip files (*.zip)")
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                zip_file_path = selected_files[0]
                zip_file_name = os.path.basename(zip_file_path)
                addon_name, _ = os.path.splitext(zip_file_name)

                # Check if the addon already exists
                content_addons_path = os.path.join(cs2_path, "content", "csgo_addons")
                existing_addons = [item for item in os.listdir(content_addons_path)
                                   if os.path.isdir(
                        os.path.join(content_addons_path, item)) and item not in exclude_game_folders]

                if addon_name in existing_addons:
                    # Show confirmation dialog
                    reply = QMessageBox.question(self, 'Addon Exists',
                                                 f"The addon '{addon_name}' already exists. Do you want to delete it and continue?",
                                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        # Delete the existing addon
                        shutil.rmtree(os.path.join(content_addons_path, addon_name))
                        print(f"Deleted existing addon: {addon_name}")
                    else:
                        print("Import cancelled")
                        return

                # Proceed with importing the addon
                self.import_addon(zip_file_path, addon_name)

    def import_addon(self, zip_file_path, addon_name):
        try:
            # Extract the zip file to the addons directory
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(os.path.join(cs2_path, "content", "csgo_addons", addon_name))
            print(f"Imported addon: {addon_name}")
            QMessageBox.information(self, 'Import Successful', f"Addon '{addon_name}' imported successfully.")
        except Exception as e:
            QMessageBox.critical(self, 'Import Failed', f"Failed to import the addon.\nError: {str(e)}")

    def update_size_status(self):
        self.exclude_include_folders()
        game_folder = os.path.join(cs2_path, 'game', 'csgo_addons', get_addon_name())
        content_folder = os.path.join(cs2_path, 'content', 'csgo_addons', get_addon_name())

        def calculate_folder_size(folder, include_folders=None, exclude_folders=None):
            total_size = 0
            folder_sizes = {}
            for root, dirs, files in os.walk(folder):
                if include_folders:
                    dirs[:] = [d for d in dirs if any(
                        os.path.commonpath([os.path.join(root, d), os.path.join(folder, inc_folder)]) == os.path.join(
                            folder, inc_folder) for inc_folder in include_folders)]
                if exclude_folders:
                    dirs[:] = [d for d in dirs if d not in exclude_folders]
                for file in files:
                    if file == 'tools_thumbnail_cache.bin':
                        continue  # Skip the file tools_thumbnail_cache.bin
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    folder_sizes[file_path] = file_size
            return total_size, folder_sizes

        def convert_size(size_bytes):
            if size_bytes == 0:
                return "0B"
            size_name = ("B", "KB", "MB", "GB", "TB")
            i = int(math.floor(math.log(size_bytes, 1024)))
            p = math.pow(1024, i)
            s = round(size_bytes / p, 2)
            return f"{s} {size_name[i]}"

        size_content, content_folder_sizes = calculate_folder_size(
            content_folder, include_folders=iclude_content_folders if iclude_content_folders else None)
        size_game, game_folder_sizes = calculate_folder_size(
            game_folder, exclude_folders=exclude_game_folders if exclude_game_folders else None)

        total_size = size_game + size_content
        size_display = convert_size(total_size)
        self.ui.size_display.setText(f'Output size before archiving: {size_display}')

        threshold_size = total_size * 0.02  # Changed from 0.05 to 0.02

        large_files = {path: size for path, size in {**content_folder_sizes, **game_folder_sizes}.items() if
                       size > threshold_size}
        sorted_large_files = sorted(large_files.items(), key=lambda item: item[1], reverse=True)

        large_files_list = "\n".join(
            [f"{os.path.relpath(path, cs2_path)}: {convert_size(size)}" for path, size in sorted_large_files])

        self.ui.size_display.setText(
            f'Output size before archiving: {size_display}\nFiles larger than 2% of total size:\n{large_files_list}')

        # Clear the existing list
        model = QStandardItemModel(self.ui.size_of_files_list)
        self.ui.size_of_files_list.setModel(model)

        # Add only large files to the list
        for path, size in sorted_large_files:
            item_text = f"{os.path.basename(path)} ({convert_size(size)})"  # Show file name and size
            item = QStandardItem(item_text)
            item.setEditable(False)  # Make the item non-editable
            item.setData(path, Qt.UserRole)  # Store the full path in the item
            model.appendRow(item)

        # Connect double-click event to open the file or folder
        self.ui.size_of_files_list.doubleClicked.connect(self.open_file)

    def open_file(self, index):
        item = self.ui.size_of_files_list.model().itemFromIndex(index)
        file_path = item.data(Qt.UserRole)
        if file_path:
            folder_path = os.path.dirname(file_path)
            os.startfile(folder_path)

    def archive_addon(self):
        reply = QMessageBox.question(None, 'Archive addon', f"Are you sure you want to archive '{get_addon_name()}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            addon_name = get_addon_name()

            # Archive the addon
            archive_path = get_config_value('PATHS', 'archive')
            game_source_path = os.path.join(cs2_path, 'game', 'csgo_addons', addon_name)
            content_source_path = os.path.join(cs2_path, 'content', 'csgo_addons', addon_name)
            destination_path = os.path.join(archive_path, addon_name + '.zip')

            global exclude_game_folders
            global iclude_content_folders

            try:
                # Collect all files to be archived
                files_to_archive = []

                # Collect files from game_source_path excluding exclude_game_folders and tools_thumbnail_cache.bin
                for root, dirs, files in os.walk(game_source_path):
                    dirs[:] = [d for d in dirs if d not in exclude_game_folders]
                    for file in files:
                        if file == 'tools_thumbnail_cache.bin':
                            continue  # Skip the file tools_thumbnail_cache.bin
                        files_to_archive.append(os.path.join(root, file))

                # Collect files from content_source_path including only iclude_content_folders and their subfolders if specified
                for root, dirs, files in os.walk(content_source_path):
                    if iclude_content_folders:
                        # Check if the current directory is within the included folders or their subfolders
                        dirs[:] = [d for d in dirs if any(os.path.commonpath(
                            [os.path.join(root, d), os.path.join(content_source_path, folder)]) == os.path.join(
                            content_source_path, folder) for folder in iclude_content_folders)]
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

                # Show completion dialog with open button
                completion_dialog = QMessageBox(self)
                completion_dialog.setWindowTitle("Archiving Completed")
                completion_dialog.setText(f"Archiving completed successfully.\nArchive path: {destination_path}")
                open_button = completion_dialog.addButton("Open Archive Path", QMessageBox.ActionRole)
                completion_dialog.addButton(QMessageBox.Ok)
                completion_dialog.exec()

                if completion_dialog.clickedButton() == open_button:
                    os.startfile(archive_path)  # This will open the archive path in the file explorer

            except Exception as e:
                QMessageBox.information(None, 'Archive Failed', f'Failed to archive the addon.\nError: {str(e)}')
        else:
            print('Archiving cancelled')