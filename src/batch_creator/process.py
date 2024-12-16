from src.preferences import get_addon_name, get_cs2_path
import os
from src.batch_creator.common import *

def perform_batch_processing(__filepath, process, preview):
    base_directory = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name())
    batch_directory = os.path.splitext(__filepath)[0]
    relative_batch_path = os.path.relpath(batch_directory, base_directory).replace('\\', '/')
    algorithm = int(process.get('algorithm', 0))
    file_extension = get_file_extension(__filepath)
    ignore_extensions = [ext.strip() for ext in process.get('ignore_extensions', '').split(',')]

    files_to_process = search_files(batch_directory, algorithm, ignore_extensions, process) if process.get('load_from_the_folder') else process.get('custom_files', [])
    created_files = []

    if preview:
        if process.get('load_from_the_folder'):
            preview_files = [file for file in files_to_process if file not in process.get('ignore_list', [])]
            return files_to_process, preview_files, file_extension, batch_directory
        else:
            return files_to_process, None, file_extension, batch_directory
    else:
        output_directory = batch_directory if process.get('output_to_the_folder') else os.path.join(
            get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), process.get('custom_output', '')
        )
        for file_name in files_to_process:
            content_template, _, _ = parse_batch_file(__filepath)
            if content_template is None:
                continue
            processed_content = content_template.replace("#$FOLDER_PATH$#", relative_batch_path).replace("#$ASSET_NAME$#", file_name)
            output_file_path = os.path.join(output_directory, f"{file_name}.{file_extension}")
            try:
                with open(output_file_path, 'w') as output_file:
                    output_file.write(processed_content)
                print(f"Created file: {output_file_path}")
                created_files.append(output_file_path)
            except Exception as e:
                print(f"Failed to create file {output_file_path}: {e}")
        return created_files


def search_files(directory, algorithm, ignore_extensions, process):
    ignore_list = [item.strip() for item in process.get('ignore_list', '').split(',')]
    files_found = []
    for root, dirs, files in os.walk(directory):
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