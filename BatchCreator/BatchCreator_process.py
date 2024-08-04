import os
from BatchCreator.BatchCreator_file_parser import batch_creator_file_parser_parse
from preferences import get_cs2_path, get_addon_name

def extract_base_names_from_end_underscore(names):
    base_names = set()
    for name in names:
        base_name = name[0].rsplit('_', 1)[0]
        base_names.add(base_name)
    return base_names
def extract_base_names_extension(names):
    base_names = set()
    for name in names:
        base_name = os.path.splitext(name[0])[0]  # Access the first element of the tuple
        base_names.add(base_name)
    return base_names


def search_files(directory, algorithm, ignore_extensions):
    files_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if not any(file.endswith(ext) for ext in ignore_extensions):
                file_name = os.path.splitext(file)
                files_list.append(file_name)

    if algorithm == 0:
        return extract_base_names_extension(files_list)
    elif algorithm == 1:
        return extract_base_names_from_end_underscore(files_list)
    else:
        # Handle the case when algorithm is neither 0 nor 1
        # You can return a default value or raise an exception based on your requirements
        return None, None


def batchcreator_process_all(current_path_file, process, preview):
    folder_path = (os.path.splitext(current_path_file))[0]
    prefix_path = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name())
    folder_path_relative = os.path.relpath(folder_path, prefix_path)

    algorithm = int(process['algorithm'])

    extension = (batch_creator_file_parser_parse(current_path_file))[2]
    ignore_extensions = [f"{item}" for item in process['ignore_extensions'].split(',')]
    files_r = search_files(folder_path, algorithm, ignore_extensions)
    if preview:
        files_list_out = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if not any(file.endswith(ext) for ext in ignore_extensions):
                    files_list_out.append(file)
        return files_r, files_list_out, extension
    else:
        content = (batch_creator_file_parser_parse(current_path_file))[1]
        for item in files_r:
            content_out = content.replace("#$FOLDER_PATH$#", folder_path_relative)
            content_out = content_out.replace("#$ASSET_NAME$#", item)
            filename = os.path.join(folder_path, item) + f".{extension}"
            with open(filename, 'w') as file:
                # Write some content to the file
                file.write(content_out)

            print(f'File {filename} created successfully.')

