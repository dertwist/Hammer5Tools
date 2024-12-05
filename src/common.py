# from src.preferences import get_cs2_path
from src.minor_features.get_cs2_path_from_registry import get_counter_strike_path_from_registry, get_steam_install_path
import os
import subprocess
import threading
import keyvalues3 as kv3
import re, unicodedata, random, string
#======================================================<  Copied from preferences.py file  >===================================================

def get_cs2_path():
    try:
        counter_strikke_2_path = (get_counter_strike_path_from_registry()).replace("\\\\", "\\")
        return counter_strikke_2_path
    except:
        pass


#===============================================================<  Variables  >=============================================================
editor_info = {
    'editor_info':
    {
    'Info': 'Hammer5Tools by Twist',
    'GitHub': 'https://github.com/dertwist/Hammer5Tools',
    'Discord_Server': 'https://discord.gg/DvCXEyhssd',
    'social_links': {
        'Steam': 'https://steamcommunity.com/id/der_twist',
        'Twitter': 'https://twitter.com/der_twist',
        'Bluesky': 'https://bsky.app/profile/der-twist.bsky.social',
        'ArtStation': 'https://www.artstation.com/nucky3d',
    }
    }
    }
app_dir = os.getcwd()
SoundEventEditor_Preset_Path = os.path.join(app_dir, "SoundEventEditor", "Presets")
SmartPropEditor_Preset_Path = os.path.join(app_dir, "SmartPropEditor", "Presets")
Presets_Path = os.path.join(app_dir, "presets")
SoundEventEditor_sounds_path = os.path.join(app_dir, "SoundEventEditor", 'sounds')
SoundEventEditor_path = os.path.join(app_dir, "SoundEventEditor")
Decompiler_path = os.path.join(app_dir, 'Decompiler', 'Decompiler.exe')

#===========================================================<  generic functions  >=========================================================
def compile(input_file, fshallow=False, fshallow2=False, force=False, verbose=False):
    """Compiling a file through game resourcecompiler

    Usage: resourcecompiler <in resource file list>
          Options:
           -i:    Source dmx file list, or resource project file list.
                  Wildcards are accepted. Can skip using the -i option
                  if you put file names @ the end of the commandline.
           -filelist <filename>: specify a text file containing a list of files
                  to be processed as inputs.
           -r:    If wildcards are specified, recursively searches subdirectories (you may want to use contentbuilder!)
           -nop4: Disables auto perforce checkout/add.
           -game <path>: Specifies path to a gameinfo.gi file (which mod to build for).
                  If this is not specified, it is derived from the input file name.
           -v:    Verbose mode
           -f:    Force-compile all encountered resources
           -fshallow: Force compile top-level resources, but only compile children and associates as needed
           -fshallow2: Force compile all top-level resources and their children, but associates as needed
           -pc:   compile resources for Windows PC (default)
           -novpk: generate loose files for the map resource and its children instead of generating a vpk
           -vpkincr: incrementally generate vpk, files already in vpk are left intact unless overwritten
           -pauseiferror: pauses for a user keypress before quitting if there was an error
           -pause: pauses for a user keypress before quitting
           -changelist <name>:  use named changelist for p4 operations
           -skiptype <ext,ext>: Skip the specified resource type recompilation by extension, comma-separated list, e.g. -skiptype vmat,vtex
           -crc <abspath>: Diagnostic - report the CRC of the specified file and quit
    """

    def compile(input_file):
        resourcecompiler = os.path.join(get_cs2_path(), 'game', 'bin', 'win64', 'resourcecompiler.exe')
        arguments = ''
        if fshallow2:
            arguments += ' -fshallow'
        if fshallow2:
            arguments += ' -fshallow2'
        if force:
            arguments += ' -f'
        if force:
            arguments += ' -v'
        process = subprocess.Popen([resourcecompiler, arguments,'-i', input_file, ], shell=True)
        process.wait()

    # Create a new thread for the compile function
    thread = threading.Thread(target=compile, args=(input_file,))
    thread.start()


def convert_snake_case(name: str = None):
    """
    Converts a snake_case string to a more readable Title Case format.
    For instance: 'distance_volume_mapping_curve' would be converted to 'Distance Volume Mapping Curve'.
    """
    if name is None:
        raise ValueError
    else:
        # Split the snake_case string by underscores
        words = name.split('_')

        # Capitalize the first letter of each word and join them with spaces
        pretty_label = ' '.join(word.capitalize() for word in words)
        return pretty_label

#===============================================================<  Format  >============================================================
def Kv3ToJson(input):
    if '<!-- kv3 encoding:' in input:
        pass
    else:
        input = '<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->\n{' + input + '\n}'
    output = kv3.textreader.KV3TextReader().parse(input).value
    return output
def JsonToKv3(input):
    if isinstance(input, dict):
        return kv3.textwriter.encode(input)
    else:
        raise ValueError('[JsonToKv3] Invalid input type: Input should be a dictionary')