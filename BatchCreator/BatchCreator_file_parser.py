import configparser, os, json
from preferences import config_dir

config_file_path = os.path.join(config_dir, 'batch_creator.cfg')
os.makedirs(config_dir, exist_ok=True)


def bc_set_config_value(section, key, value):
    config = configparser.ConfigParser()
    if not config.has_section(section):
        config.add_section(section)
    config.set(section, key, value)
    with open(config_file_path, 'w') as configfile:
        config.write(configfile)

def bc_get_config_value(section, key):
    config = configparser.ConfigParser()
    if config.has_section(section) and config.has_option(section, key):
        return config.get(section, key)
    return None

def default_settings():
    config = configparser.ConfigParser()
    if os.path.exists(config_file_path):
        config.read(config_file_path)
    else:
        bc_set_config_value('MINI_EXPLORER_LAST_PATH', '', '')
    print(f"Configuration file path: {config_file_path}")

default_settings()

def batch_creator_file_parser_parse(config_file):
    config = configparser.ConfigParser()
    # Create a ConfigParser object

    # Read the configuration file
    config.read(config_file)

    # Extract values from the configuration
    version = config.get('APP', 'version', fallback=None)
    content = json.loads(config.get('CONTENT','file',fallback=None))
    exceptions = config.get('EXCEPTIONS', 'ignore_list', fallback=None)

    return version, content, exceptions

def batch_creator_file_parser_output(version, content, exceptions, file_path):
    config = configparser.ConfigParser()
    # Add sections and key-value pairs
    config['APP'] = {
        'name': 'BatchCreator',
        'version': version
    }
    config['CONTENT'] = {
        'file': json.dumps(content)
    }
    config['EXCEPTIONS'] = {
        'ignore_list': exceptions
    }
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
    config['CONTENT'] = {
        'file': json.dumps('')
    }
    config['EXCEPTIONS'] = {
        'ignore_list': 'name.extension,name.extension,relative_path'
    }

    try:
        with open(file_path, 'w') as configfile:
            config.write(configfile)
        print(f"File created at: {file_path}")
    except Exception as e:
        print(f"Failed to create file: {e}")