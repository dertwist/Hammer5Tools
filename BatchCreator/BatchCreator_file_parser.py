import configparser

def batch_creator_file_parser_parse(config_file):
    # Create a ConfigParser object
    config = configparser.ConfigParser()

    # Read the configuration file
    config.read(config_file)

    # Extract values from the configuration
    version = config.get('APP', 'version', fallback=None)
    content = config.get('CONTENT', 'file', fallback=None)
    exceptions = config.get('EXCEPTIONS', 'example', fallback=None)

    return version, content, exceptions

def batch_creator_file_parser_initialize(version):
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
        'example': 'name.extension'
    }
    return config