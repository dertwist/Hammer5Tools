import os
import json

from src.batch_creator.objects import default_file
from src.preferences import get_addon_name, get_cs2_path
from src.batch_creator.common import extract_base_names, extract_base_names_underscore
from PySide6.QtWidgets import QMessageBox

def perform_batch_processing(file_path, process, preview):
    base_directory = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name())
    batch_directory = os.path.splitext(file_path)[0]
    relative_batch_path = os.path.relpath(batch_directory, base_directory).replace('\\', '/')
    algorithm = int(process.get('algorithm', default_file['process']['algorithm']))
    file_extension = process.get('extension', default_file['process']['extension'])
    ignore_extensions = [ext.strip() for ext in process.get('ignore_extensions', '').split(',')]

    files_to_process = search_files(batch_directory, algorithm, ignore_extensions, process) if process.get('load_from_the_folder') else process.get('custom_files', [])
    created_files = []

    if preview:
        return preview_processing_files(files_to_process, batch_directory, base_directory, file_extension, process)
    else:
        output_directory = batch_directory if process.get('output_to_the_folder') else os.path.join(
            get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), process.get('custom_output', '')
        )
        execute_file_creation(files_to_process, output_directory, relative_batch_path, file_extension, created_files, file_path)
        return created_files

def execute_file_creation(files, output_path, relative_path, extension, created_files, template_file):
    try:
        with open(template_file, 'r') as file:
            data = json.load(file)
            content_template = data.get('file', {}).get('content', '')
    except Exception as e:
        QMessageBox.critical(None, "Processing Error", f"Error reading batch file: {e}")
        return

    for file_name in files:
        processed_content = content_template.replace("#$FOLDER_PATH$#", relative_path).replace("#$ASSET_NAME$#", file_name)
        output_file_path = os.path.join(output_path, f"{file_name}.{extension}")
        try:
            with open(output_file_path, 'w') as output_file:
                output_file.write(processed_content)
            print(f'File created: {output_file_path}')
            created_files.append(output_file_path)
        except Exception as e:
            print(f"Failed to create file {output_file_path}: {e}")

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