# from src.preferences import get_cs2_path
from src.other.get_cs2_path import get_counter_strike_path_from_registry, get_steam_install_path
from src.styles.common import qt_stylesheet_tabbar
import sys
import os
import subprocess
from PySide6.QtWidgets import QTabBar, QDockWidget
import threading
import keyvalues3 as kv3
from keyvalues3.textwriter import KV3EncoderOptions
import ctypes
from typing import Dict, List, Optional, Set
import re

def generate_unique_name(base_name: str, existing_names: Set[str], separator: str = "_") -> str:
    """
    Generates a unique name by appending or incrementing a numeric suffix (_01, _02, etc.).
    If base_name already ends in [separator]NN, it increments that number.
    It skips any names already present in existing_names.
    """
    # Strip whitespace to avoid regex match failures
    base_name = base_name.strip()
    
    # Escape separator for regex
    sep_esc = re.escape(separator)
    
    # Regex to match a suffix like [separator]01, [separator]02, etc. at the end of the string.
    match = re.search(f'{sep_esc}(\\d+)$', base_name)
    
    if match:
        prefix = base_name[:match.start()]
        counter = int(match.group(1)) + 1
    else:
        prefix = base_name
        counter = 1
        
    while True:
        new_name = f"{prefix}{separator}{counter:02d}"
        if new_name not in existing_names:
            return new_name
        counter += 1




from pathlib import Path

# Versions
app_version = '5.0.0'

def get_channel() -> str:
    """
    Returns the build channel ('stable' or 'dev') by reading line 2 of version.txt.
    In frozen builds, version.txt is next to the executable.
    """
    try:
        if getattr(sys, 'frozen', False):
            vtxt = Path(sys.executable).parent / 'version.txt'
        else:
            return 'stable'
        
        if vtxt.exists():
            lines = vtxt.read_text(encoding='utf-8').splitlines()
            return lines[1].strip() if len(lines) >= 2 else 'stable'
    except Exception:
        pass
    return 'stable'

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

editor_info = {
    'editor_info':
    {
        'name': 'Hammer 5 Tools',
        'version': f'{app_version}'
    }
}
def get_app_paths() -> tuple[Path, Path]:
    """
    Returns (app_dir, user_data_dir).
    app_dir: The folder containing the executable.
    user_data_dir: Persistent folder for user data (survives updates).
    """
    if getattr(sys, 'frozen', False):
        exe_path = Path(sys.executable)
        current_dir = exe_path.parent
        
        # Velopack structure: <root>/current/Hammer5Tools.exe
        # We want userdata in <root>/userdata
        if current_dir.name.lower() in ('app', 'current'):
            root_dir = current_dir.parent
        else:
            # Fallback if structure is different
            root_dir = current_dir.parent
            
        return current_dir, root_dir / "userdata"
    
    # Dev mode: repo root
    root = Path(__file__).resolve().parent.parent
    return root, root / "userdata_dev"

# Initialize Paths
app_dir, user_data_dir = get_app_paths()
user_data_dir.mkdir(parents=True, exist_ok=True)

# Preset Paths
SoundEventEditor_Path = user_data_dir / "SoundEventEditor"
SoundEventEditor_path = SoundEventEditor_Path
SmartPropEditor_Path = user_data_dir / "SmartPropEditor"
Presets_Path = user_data_dir / "Presets"
Hotkeys_Path = user_data_dir / "Hotkeys"

SoundEventEditor_Preset_Path = SoundEventEditor_Path / "Presets"
SmartPropEditor_Preset_Path = SmartPropEditor_Path / "Presets"

# Bundled presets (read-only, updated with app)
if getattr(sys, 'frozen', False):
    # PyInstaller bundles defaults into sys._MEIPASS/defaults
    internal_base = Path(sys._MEIPASS) / "defaults"
else:
    # Dev mode: defaults are in the repo root
    internal_base = app_dir

SoundEventEditor_Internal_Preset_Path = internal_base / "SoundEventEditor" / "Presets"
SmartPropEditor_Internal_Preset_Path = internal_base / "SmartPropEditor" / "Presets"

# Data paths for SoundEventEditor
SoundEventEditor_sounds_path = SoundEventEditor_Path / 'sounds'
SoundEventEditor_soundevents_path = SoundEventEditor_Path / 'soundevents'

# Ensure critical directories exist even if not seeded
for p in [Presets_Path, Hotkeys_Path, SoundEventEditor_Preset_Path, SmartPropEditor_Preset_Path,
          SoundEventEditor_sounds_path, SoundEventEditor_soundevents_path]:
    p.mkdir(parents=True, exist_ok=True)

def get_all_presets(internal_path: Path, user_path: Path) -> list[dict]:
    """Returns a list of presets from both internal and user paths."""
    presets = []
    for path in (internal_path, user_path):
        if path.is_dir():
            for file in path.rglob("*"):
                if file.suffix in (".kv3", ".vdata", ".vsmart") and file.is_file():
                    presets.append({file.name: str(file.absolute())})
    return presets

def seed_user_data():
    """Seeds the user directory from bundled defaults on first launch or if files are missing."""
    if getattr(sys, 'frozen', False):
        defaults_path = Path(sys._MEIPASS) / "defaults"
    else:
        # Dev mode: defaults are in the 'Hammer5Tools' subfolder of the repo root
        defaults_path = Path(__file__).resolve().parent.parent / "Hammer5Tools"
        
    if not defaults_path.exists():
        return

    import shutil
    
    def copy_if_not_exists(src: Path, dest: Path):
        if src.is_dir():
            # Skip internal app folders
            if src.name.lower() in ('app', '_internal'):
                return
            dest.mkdir(parents=True, exist_ok=True)
            for item in src.iterdir():
                copy_if_not_exists(item, dest / item.name)
        else:
            # Skip executables
            if src.suffix == '.exe':
                return
            if not dest.exists():
                try:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
                    print(f"Seeded {dest.relative_to(user_data_dir)} from defaults")
                except Exception as e:
                    print(f"Failed to seed {dest}: {e}")

    copy_if_not_exists(defaults_path, user_data_dir)

# Run seeding
seed_user_data()

# web
discord_feedback_channel = "https://discord.gg/5yzvEQnazG"

# other
default_commands = " -addon " + 'addon_name' + ' -tool hammer' + ' -asset maps/' + 'addon_name' + '.vmap' + " -tools -steam -retail -gpuraytracing -noinsecru +install_dlc_workshoptools_cvar 1 +sv_steamauth_enforce 0 -netconport 2121"

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

    def run_rc(input_file):
        from src.settings.common import get_cs2_path
        rc_path = get_cs2_path()
        if not rc_path:
            return
            
        resourcecompiler = os.path.join(rc_path, 'game', 'bin', 'win64', 'resourcecompiler.exe')
        if not os.path.exists(resourcecompiler):
            return

        cmd_args = [resourcecompiler]
        if fshallow:
            cmd_args.append('-fshallow')
        if fshallow2:
            cmd_args.append('-fshallow2')
        if force:
            cmd_args.append('-f')
        if verbose:
            cmd_args.append('-v')
        
        cmd_args.extend(['-i', input_file])
        
        try:
            process = subprocess.Popen(cmd_args)
            process.wait()
        except Exception as e:
            print(f"Error running ResourceCompiler: {e}")

    # Create a new thread for the compile function
    thread = threading.Thread(target=run_rc, args=(input_file,))
    thread.start()

# web
discord_feedback_channel = "https://discord.gg/5yzvEQnazG"

# other
default_commands = " -addon " + 'addon_name' + ' -tool hammer' + ' -asset maps/' + 'addon_name' + '.vmap' + " -tools -steam -retail -gpuraytracing -noinsecru +install_dlc_workshoptools_cvar 1 +sv_steamauth_enforce 0 -netconport 2121"

#------------<  QT functions  >----------
def set_qdock_tab_style(findChildren):
    for tab_bar in findChildren(QTabBar):
        tab_bar.setStyleSheet(qt_stylesheet_tabbar)

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

#===============================================================<  Kv3 Format  >============================================================
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

#===============================================================<  Fast Copy  >=============================================================
import copy

try:
    import orjson

    def fast_deepcopy(obj):
        """Deep-copy a JSON-safe nested dict/list via orjson round-trip (3-10x faster than copy.deepcopy)."""
        try:
            return orjson.loads(orjson.dumps(obj))
        except (TypeError, orjson.JSONEncodeError):
            return copy.deepcopy(obj)

except ImportError:
    def fast_deepcopy(obj):
        """Fallback deep-copy when orjson is not installed."""
        return copy.deepcopy(obj)

def get_cs2_path():
    from src.settings.common import get_cs2_path as _get_cs2_path
    return _get_cs2_path()