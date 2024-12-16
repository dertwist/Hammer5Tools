import json
from src.batch_creator.objects import *

def parse_batch_file(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            content = data.get('FILE', {}).get('content', '')
            extension = data.get('FILE', {}).get('extension', 'vmdl')
            process = data.get('PROCESS', {})
            return content, extension, process
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"An error occurred while parsing the batch file: {e}")
        return None, None, {}


def write_batch_file(file_path, content, process, extension):
    data = {
        'FILE': {'content': content, 'extension': extension},
        'PROCESS': process
    }
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
        print(f"Batch file saved at: {file_path}")
    except Exception as e:
        print(f"Failed to save batch file: {e}")


def initialize_batch_file(file_path):
    try:
        with open(file_path, 'w') as file:
            json.dump(default_file, file, indent=4)
        print(f"Batch file initialized at: {file_path}")
    except Exception as e:
        print(f"Failed to initialize batch file: {e}")

def extract_base_names(names):
    return set(name.split('_')[0] for name in names)


def extract_base_names_underscore(names):
    return set(name.rsplit('_', 1)[0] if '_' in name else name for name in names)


def get_file_extension(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data.get('FILE', {}).get('extension', 'vmdl')
    except (json.JSONDecodeError, FileNotFoundError):
        return 'vmdl'