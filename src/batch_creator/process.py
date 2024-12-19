# src/batch_creator/process.py

import os
import json
from src.batch_creator.objects import default_file
from src.preferences import get_addon_name, get_cs2_path, get_addon_dir
from PySide6.QtWidgets import QMessageBox
from pathlib import Path
from PySide6.QtCore import Signal, QThread

class StartProcess(QThread):
    finished = Signal()

    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.stop_thread = False

    def update_reference_content(self, reference):
        reference_path = os.path.join(get_addon_dir(), reference)
        with open(reference_path, 'r') as file:
            __data = file.read()
        return __data

    def load_file(self, filepath):
        # Open the file and pass the file object to json.load()
        with open(filepath, 'r') as file:
            __data = json.load(file)
        process = __data.get('process', {})
        replacements = __data.get('replacements', {})
        content = __data.get('file', {}).get('content', '')
        return process, replacements, content

    def run(self):
        try:
            if self.stop_thread:
                return

            # Load and process the file
            process, replacements, content = self.load_file(self.filepath)
            reference = process.get('reference')

            if reference:
                content = self.update_reference_content(reference)
                # Avoid modifying the config file to prevent infinite loop

            if self.stop_thread:
                return

            # Perform batch processing
            perform_batch_processing(self.filepath, process, False, replacements, content)

            # Emit the finished signal when done
            self.finished.emit()

        except Exception as e:
            print(f"Error in StartProcess: {e}")

    def stop(self):
        self.stop_thread = True
        self.quit()
        self.wait()

def perform_batch_processing(file_path, process, preview, replacements, content_template=None):
    base_directory = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name())
    batch_directory = os.path.splitext(file_path)[0]
    relative_batch_path = os.path.relpath(batch_directory, base_directory).replace('\\', '/')
    algorithm = int(process.get('algorithm', default_file['process']['algorithm']))
    file_extension = process.get('extension', default_file['process']['extension'])
    ignore_extensions = [ext.strip() for ext in process.get('ignore_extensions', '').split(',')]
    reference = process.get('reference', False)
    reference = os.path.join(get_addon_dir(), reference) if reference else None

    files_to_process = search_files(batch_directory, algorithm, ignore_extensions, process) if process.get('load_from_the_folder') else process.get('custom_files', [])
    created_files = []

    if preview:
        return preview_processing_files(files_to_process, batch_directory, base_directory, file_extension, process)
    else:
        output_directory = batch_directory if process.get('output_to_the_folder') else os.path.join(
            get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), process.get('custom_output', '')
        )
        execute_file_creation(files_to_process, output_directory, relative_batch_path, file_extension, created_files, replacements, reference, content_template)
        return created_files

def execute_file_creation(files, output_path, relative_path, extension, created_files, replacements, reference, content_template):
    if content_template is None:
        QMessageBox.critical(None, "Processing Error", "No content template provided.")
        return

    for file_name in files:
        __data_replacements = content_template
        if replacements:
            for key, replacement in replacements.items():
                old, new = replacement.get('replacement', ['', ''])
                if old == "":
                    pass
                else:
                    __data_replacements = __data_replacements.replace(old, new)

        __data = __data_replacements.replace("#$FOLDER_PATH$#", relative_path).replace("#$ASSET_NAME$#", file_name)
        output_file_path = os.path.join(output_path, f"{file_name}.{extension}")

        output_path_resolved = Path(output_file_path).resolve()
        reference_path_resolved = Path(reference).resolve() if reference else None

        if output_path_resolved != reference_path_resolved:
            try:
                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                with open(output_file_path, 'w') as output_file:
                    output_file.write(__data)
                print(f'File created: {output_file_path}')
                created_files.append(output_file_path)
            except Exception as e:
                print(f"Failed to create file {output_file_path} \n {e}")
        else:
            print(f"Skipped writing to the reference file to prevent infinite loop: {output_file_path}")

def preview_processing_files(files, batch_directory, base_directory, extension, process):
    if process.get('load_from_the_folder'):
        files_list_out = []
        for root, _, files_in_dir in os.walk(batch_directory):
            for file in files_in_dir:
                if file not in process.get('ignore_list', []) and not any(file.endswith(ext) for ext in process.get('ignore_extensions', '').split(',')):
                    files_list_out.append(file)
        return files, files_list_out, extension, batch_directory
    else:
        return files, None, extension, batch_directory

def extract_base_names(names):
    return set(os.path.basename(name) for name in names)

def extract_base_names_underscore(names):
    return set(name.rsplit('_', 1)[0] if '_' in name else name for name in names)

def search_files(directory, algorithm, ignore_extensions, process):
    ignore_list = [item.strip() for item in process.get('ignore_list', '').split(',')]
    files_found = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file not in ignore_list and not any(file.endswith(ext) for ext in ignore_extensions):
                base_name, _ = os.path.splitext(file)
                files_found.append(base_name)

    if algorithm == 0:
        return extract_base_names(files_found)
    elif algorithm == 1:
        return extract_base_names_underscore(files_found)
    else:
        return []