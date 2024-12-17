import json
from src.batch_creator.objects import default_file

def extract_base_names(names):
    return set(name.split('_')[0] for name in names)

def extract_base_names_underscore(names):
    return set(name.rsplit('_', 1)[0] if '_' in name else name for name in names)