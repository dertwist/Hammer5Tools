# from src.preferences import get_cs2_path
from src.other.get_cs2_path import get_counter_strike_path_from_registry, get_steam_install_path
from src.styles.common import qt_stylesheet_tabbar
import os
import subprocess
from PySide6.QtWidgets import QTabBar, QDockWidget
import threading
import keyvalues3 as kv3
from keyvalues3.textwriter import KV3EncoderOptions
import ctypes
import re, unicodedata, random, string
#======================================================<  Copied from preferences.py file  >===================================================

def get_cs2_path():
    try:
        counter_strikke_2_path = (get_counter_strike_path_from_registry()).replace("\\\\", "\\")
        return counter_strikke_2_path
    except:
        pass



#=================================================================<  Title  >===============================================================
def enable_dark_title_bar(window):
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    try:
        hwnd = int(window.winId())
        set_dark_mode = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(set_dark_mode),
            ctypes.sizeof(set_dark_mode)
        )
    except Exception as e:
        print(f"Failed to set dark mode title bar: {e}")

#===============================================================<  Variables  >=============================================================
# Versions
app_version = '4.6.0'

editor_info = {
    'editor_info':
    {
    'name': 'Hammer 5 Tools',
    'version' : f'{app_version}'
    }
    }

# Paths
app_dir = os.getcwd()
SoundEventEditor_Preset_Path = os.path.join(app_dir, "SoundEventEditor", "Presets")
SmartPropEditor_Preset_Path = os.path.join(app_dir, "SmartPropEditor", "Presets")
Presets_Path = os.path.join(app_dir, "presets")
SoundEventEditor_sounds_path = os.path.join(app_dir, "SoundEventEditor", 'sounds')
SoundEventEditor_path = os.path.join(app_dir, "SoundEventEditor")
Decompiler_path = os.path.join(os.path.dirname(__file__), 'external', 'Decompiler.exe')
KeyValues2Net_path = os.path.join(os.path.dirname(__file__), 'external', 'keyvalues2', 'Datamodel.NET.dll')

# web
discord_feedback_channel = "https://discord.gg/5yzvEQnazG"

# other
default_commands = " -addon " + 'addon_name' + ' -tool hammer' + ' -asset maps/' + 'addon_name' + '.vmap' + " -tools -steam -retail -gpuraytracing -noinsecru +install_dlc_workshoptools_cvar 1 +sv_steamauth_enforce 0"

#------------<  QT functions  >----------

def set_qdock_tab_style(findChildren):
    for tab_bar in findChildren(QTabBar):
        tab_bar.setStyleSheet(qt_stylesheet_tabbar)

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
def JsonToKv3(input, disable_line_value_length_limit_keys: list = None, format=None):
    if format == 'vmdl':
        format_option = kv3.FORMAT_VMDL
    else:
        format_option = kv3.FORMAT_GENERIC
    if isinstance(input, dict) or isinstance(input, list):
        kv3_file = kv3.KV3File(value=input, format=format_option)
        options = KV3EncoderOptions(
            serialize_enums_as_ints=False,
            no_header=False,
            disable_line_value_length_limit_keys=disable_line_value_length_limit_keys,
        )
        return kv3.textwriter.encode(kv3_file, options=options)
    else:
        raise ValueError('[JsonToKv3] Invalid input type: Input should be a dictionary or list')