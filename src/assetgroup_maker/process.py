import os
import json
from PySide6.QtCore import Signal, QThread

from src.assetgroup_maker.objects import default_file
from src.settings.main import get_addon_name, get_cs2_path, get_addon_dir, debug

class StartProcess(QThread):
    finished = Signal()

    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.stop_thread = False

    def update_reference_content(self, reference):
        reference_path = os.path.join(get_addon_dir(), reference)
        try:
            with open(reference_path, 'r') as file:
                __data = file.read()
            return __data
        except FileNotFoundError:
            debug(f"Reference file not found: {reference_path}")
            return ""
        except Exception as e:
            debug(f"Error reading reference file {reference_path}: {e}")
            return ""

    def load_file(self, filepath):
        try:
            with open(filepath, 'r') as file:
                __data = json.load(file)
            process = __data.get('process', {})
            replacements = __data.get('replacements', {})
            content = __data.get('file', {}).get('content', '')
            return process, replacements, content
        except FileNotFoundError:
            debug(f"File to load not found: {filepath}")
            return {}, {}, ""
        except json.JSONDecodeError as e:
            debug(f"JSON decode error in file {filepath}: {e}")
            return {}, {}, ""
        except Exception as e:
            debug(f"Error loading file {filepath}: {e}")
            return {}, {}, ""

    def run(self):
        try:
            if self.stop_thread:
                return

            process, replacements, content = self.load_file(self.filepath)
            if not process:
                debug("No process configuration found. Aborting.")
                return

            reference = process.get('reference')
            if reference:
                content = self.update_reference_content(reference)

            if self.stop_thread:
                return

            perform_batch_processing(
                file_path=self.filepath,
                process=process,
                preview=False,
                replacements=replacements,
                content_template=content  # Assuming 'content' is intended as 'content_template'
            )

            self.finished.emit()

        except Exception as e:
            debug(f"Error in StartProcess: {e}")

    def stop(self):
        self.stop_thread = True
        self.quit()
        self.wait()

def perform_batch_processing(file_path, process, preview, replacements, content_template=None):
    base_directory = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name())
    if not os.path.isdir(base_directory):
        debug(f"Base directory does not exist: {base_directory}")
        return []

    batch_directory = os.path.splitext(file_path)[0]
    if not os.path.isdir(batch_directory):
        os.makedirs(batch_directory)

    relative_batch_path = os.path.relpath(batch_directory, base_directory).replace('\\', '/')

    algorithm = int(process.get('algorithm', default_file['process']['algorithm']))
    file_extension = process.get('extension', default_file['process']['extension'])
    ignore_extensions = [ext.strip() for ext in process.get('ignore_extensions', '').split(',')]
    reference = process.get('reference')
    reference = os.path.join(get_addon_dir(), reference) if reference else None

    load_from_the_folder = bool(process.get('load_from_the_folder'))
    output_to_the_folder = bool(process.get('output_to_the_folder'))

    if load_from_the_folder:
        files_to_process = search_files(batch_directory, algorithm, ignore_extensions, process)
    else:
        files_to_process = process.get('custom_files', [])

    created_files = []
    if preview:
        return preview_processing_files(files_to_process, batch_directory, file_extension, process)
    else:
        if output_to_the_folder:
            output_directory = batch_directory
        else:
            custom_output = process.get('custom_output', '')
            output_directory = os.path.join(get_addon_dir(), custom_output)

        if not os.path.isdir(output_directory):
            try:
                os.makedirs(output_directory, exist_ok=True)
                debug(f"Created output directory: {output_directory}")
            except Exception as e:
                debug(f"Failed to create output directory {output_directory}: {e}")
                return created_files

        execute_file_creation(
            files=files_to_process,
            output_path=output_directory,
            relative_path=relative_batch_path,
            extension=file_extension,
            created_files=created_files,
            replacements=replacements,
            reference=reference,
            content_template=content_template,  # Ensure content_template is passed here
            load_from_the_folder=load_from_the_folder,
            base_directory=base_directory
        )
        return created_files

def execute_file_creation(files, output_path, relative_path, extension, created_files,
                          replacements, reference, content_template, load_from_the_folder,
                          base_directory=None):
    if content_template is None:
        debug("Content template is missing. Skipping file creation.")
        return

    for file_name in files:
        __data_replacements = content_template
        if replacements:
            for key, replacement in replacements.items():
                old, new = replacement.get('replacement', ['', ''])
                if old:
                    __data_replacements = __data_replacements.replace(old, new)

        if load_from_the_folder:
            __data = __data_replacements.replace("#$FOLDER_PATH$#", relative_path)
            __data = __data.replace("#$ASSET_NAME$#", file_name)
            output_file_path = os.path.join(output_path, f"{file_name}.{extension}")
        else:
            original_dir = os.path.dirname(file_name)
            base_name = os.path.splitext(os.path.basename(file_name))[0]

            dynamic_relative_path = os.path.relpath(original_dir, base_directory).replace('\\', '/')

            __data = __data_replacements.replace("#$FOLDER_PATH$#", dynamic_relative_path)
            __data = __data.replace("#$ASSET_NAME$#", base_name)
            output_file_path = os.path.join(output_path, f"{base_name}.{extension}")

        output_path_resolved = os.path.abspath(output_file_path)
        reference_path_resolved = os.path.abspath(reference) if reference else None

        if output_path_resolved != reference_path_resolved:
            try:
                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                with open(output_file_path, 'w') as output_file:
                    output_file.write(__data)
                debug(f"File created: {output_file_path}")
                created_files.append(output_file_path)
            except PermissionError as e:
                debug(f"Permission denied: {output_file_path}\n{e}")
            except Exception as e:
                debug(f"Failed to create file {output_file_path}\n{e}")
        else:
            debug(f"Skipped writing to the reference file to prevent infinite loop: {output_file_path}")

def get_basename_without_extension(file_path):
    return os.path.splitext(os.path.basename(file_path))[0]

def preview_processing_files(files, base_directory, extension, process):
    if process.get('load_from_the_folder'):
        files_list_out = []
        for root, _, files_in_dir in os.walk(base_directory):
            for file in files_in_dir:
                if (
                    file not in process.get('ignore_list', [])
                    and not any(file.endswith(ext) for ext in process.get('ignore_extensions', '').split(','))
                ):
                    files_list_out.append(file)
        return files, files_list_out, extension, base_directory
    else:
        return [get_basename_without_extension(f) for f in files], None, extension, base_directory


def extract_base_names(names):
    return set(os.path.basename(name) for name in names)

def extract_base_names_underscore(names):
    return set(name.rsplit('_', 1)[0] if '_' in name else name for name in names)

def search_files(directory, algorithm, ignore_extensions, process):
    ignore_list = [item.strip() for item in process.get('ignore_list', '').split(',')]
    files_found = []
    for root, _, files_in_dir in os.walk(directory):
        for file in files_in_dir:
            if file not in ignore_list and not any(file.endswith(ext) for ext in ignore_extensions):
                base_name, _ = os.path.splitext(file)
                files_found.append(base_name)

    if algorithm == 0:
        return extract_base_names(files_found)
    elif algorithm == 1:
        return extract_base_names_underscore(files_found)
    else:
        debug(f"Unknown algorithm: {algorithm}")
        return []