import configparser, os, json
from preferences import config_dir
from distutils.util import strtobool

config_file_path = os.path.join(config_dir, 'batch_creator.cfg')
os.makedirs(config_dir, exist_ok=True)
config = configparser.ConfigParser()

def bc_set_config_value(section, key, value):
    if not config.has_section(section):
        config.add_section(section)
    config.set(section, key, value)
    with open(config_file_path, 'w') as configfile:
        config.write(configfile)

def bc_get_config_value(section, key):
    if config.has_section(section) and config.has_option(section, key):
        return config.get(section, key)
    return None


def bc_set_config_bool(section,key, bool):
    return bc_set_config_value(section, key, str(bool))

def bc_get_config_bool(section,key):
    return bool(strtobool(bc_get_config_value(section, key)))
def default_settings():
    if os.path.exists(config_file_path):
        config.read(config_file_path)
    else:
        bc_set_config_value('MINI_EXPLORER_LAST_PATH', 'addon_test', 'path')
    print(f"Configuration file path: {config_file_path}")

default_settings()

def batch_creator_file_parser_parse(config_file):
    config = configparser.ConfigParser()
    # Create a ConfigParser object

    try:
        # Read the configuration file
        config.read(config_file)

        # Extract values from the configuration
        version = config.get('APP', 'version', fallback=None)
        content = json.loads(config.get('FILE', 'content', fallback=None))
        process = {}
        process_config_values = ['ignore_list', 'custom_files', 'custom_output', 'load_from_the_folder', 'algorithm','output_to_the_folder', 'ignore_extensions']
        for value in process_config_values:
            process[value] = (config.get('PROCESS', value, fallback=None))
        extension = config.get('FILE', 'extension', fallback=None)

        return version, content, extension, process

    except (configparser.Error, json.JSONDecodeError) as e:
        # Handle specific exceptions that may occur during reading or parsing
        print(f"An error occurred: {e}")
        # You can choose to log the error, raise a custom exception, or handle it in any other way

        # Return default values or handle the error accordingly
        return None, None, None, None
def batch_creator_file_parser_output(version, content, process, extension, file_path):
    config = configparser.ConfigParser()
    # Add sections and key-value pairs
    config['APP'] = {
        'name': 'BatchCreator',
        'version': version
    }
    config['FILE'] = {
        'content': json.dumps(content),
        'extension': extension
    }
    config['PROCESS'] = {}
    print(process)
    for value in process:
        config['PROCESS'][str(value)] = str(process[value])
    try:
        with open(file_path, 'w') as configfile:
            config.write(configfile)
        print(f"File created at: {file_path}")
    except Exception as e:
        print(f"Failed to create file: {e}")

def batch_creator_file_parser_initialize(version,file_path):
    # Create a ConfigParser object
    config = configparser.ConfigParser()

    # Add sections and key-value pairs
    config['APP'] = {
        'name': 'BatchCreator',
        'version': version
    }
    config['FILE'] = {
        'content': json.dumps(''),
        'extension': 'vmdl'
    }
    config['PROCESS'] = {
        'ignore_list': 'name.extension,name.extension,relative_path',
        'custom_files': 'name.extension,name.extension',
        'custom_output': 'relative_path',
        'load_from_the_folder': 'True',
        'algorithm': '0',
        'output_to_the_folder': 'True',
        'ignore_extensions': 'blend,vmdl,vmat'
    }

    try:
        with open(file_path, 'w') as configfile:
            config.write(configfile)
        print(f"File created at: {file_path}")
    except Exception as e:
        print(f"Failed to create file: {e}")