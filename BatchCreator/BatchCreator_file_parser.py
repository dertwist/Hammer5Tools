import configparser

def batch_creator_file_parser_parse(config_file):
    # Create a ConfigParser object
    config = configparser.ConfigParser()

    # Read the configuration file
    config.read(config_file)

    # Extract values from the configuration
    version = config.get('APP', 'version', fallback=None)
    content = config.get('CONTENT', 'file', fallback=None)
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
        'file': content
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
        'file': ""
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