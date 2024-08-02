import os
from BatchCreator.BatchCreator_file_parser import batch_creator_file_parser_parse
from preferences import get_cs2_path, get_addon_name

def extract_base_names(names):
    base_names = set()
    for name in names:
        base_name = name.rsplit('_', 1)[0]
        base_names.add(base_name)
    return base_names
def search_files(directory):
    files_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_name = (os.path.splitext(file))[0]
            files_list.append(file_name)
    return extract_base_names(files_list)


def batchcreator_process_all(current_path_file):
    folder_path = (os.path.splitext(current_path_file))[0]
    prefix_path = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name())
    folder_path_relative = os.path.relpath(folder_path, prefix_path)

    files = search_files(folder_path)
    content = (batch_creator_file_parser_parse(current_path_file))[1]
    extension = (batch_creator_file_parser_parse(current_path_file))[3]
    print(files)
    for item in files:
        content_out = content.replace("#$FOLDER_PATH$#", folder_path_relative)
        content_out = content_out.replace("#$ASSET_NAME$#", item)
        filename = os.path.join(folder_path, item) + f".{extension}"
        with open(filename, 'w') as file:
            # Write some content to the file
            file.write(content_out)

        print(f'File {filename} created successfully.')

