import logging
import sys
from PySide6.QtWidgets import QMessageBox
from core.runtime_paths import resolve_runtime_paths

log = logging.getLogger(__name__)

try:
    import winreg
except ImportError:
    winreg = None

def get_fileedit_path():
    """Returns the absolute path to the main Hammer5Tools.exe launcher."""
    return str(resolve_runtime_paths().install_root / "Hammer5Tools.exe")

def get_smartprop_icon_path():
    """Returns the absolute path to smartprop.ico."""
    if getattr(sys, 'frozen', False):
        paths = resolve_runtime_paths()
        candidates = [
            paths.runtime_resource("gui", "assets", "icons", "app", "smartprop.ico"),
            paths.application_resource("icons", "smartprop.ico"),
            paths.runtime_resource("icons", "smartprop.ico"),
        ]
        for c in candidates:
            if c.exists():
                return str(c)

    # Development fallback
    from gui.common import gui_assets_dir
    return gui_assets_dir("icons", "app", "smartprop.ico")

def get_vsnd_icon_path():
    """Returns the absolute path to vsnd.ico."""
    if getattr(sys, 'frozen', False):
        paths = resolve_runtime_paths()
        candidates = [
            paths.runtime_resource("gui", "assets", "icons", "app", "vsnd.ico"),
            paths.application_resource("icons", "vsnd.ico"),
            paths.runtime_resource("icons", "vsnd.ico"),
        ]
        for c in candidates:
            if c.exists():
                return str(c)

    # Development fallback
    from gui.common import gui_assets_dir
    return gui_assets_dir("icons", "app", "vsnd.ico")

def check_association(extension):
    """
    Checks the current association for an extension.
    Returns:
        prog_id (str): The ProgID associated with the extension, or None.
        is_us (bool): True if it's already associated with Hammer5Tools.
    """
    if winreg is None:
        return None, False

    if not extension.startswith('.'):
        extension = '.' + extension
        
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{extension}", 0, winreg.KEY_READ) as key:
            prog_id, _ = winreg.QueryValueEx(key, "")
            is_us = prog_id in ["Hammer5Tools.SmartProp", "Hammer5Tools.SoundEvent", "Hammer5Tools.Batch"]
            return prog_id, is_us
    except FileNotFoundError:
        return None, False
    except Exception:
        return None, False

def register_extension(extension, prog_id, description, icon_path, open_cmd):
    """Registers a file extension in the registry."""
    if winreg is None:
        return False

    if not extension.startswith('.'):
        extension = '.' + extension
        
    try:
        # 1. Register extension -> ProgID
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{extension}") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, prog_id)
            
        # 2. Register ProgID details
        prog_key_path = f"Software\\Classes\\{prog_id}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, prog_key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, description)
            
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{prog_key_path}\\DefaultIcon") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon_path)
            
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{prog_key_path}\\shell\\open\\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{open_cmd}" "%1"')
            
        # Add "Edit with Hammer5Tools" context menu for smartprops and soundevents
        if extension in [".vsmart", ".vsndevts"]:
            edit_key_path = f"{prog_key_path}\\shell\\editwith"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, edit_key_path) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Edit With Hammer5Tools")
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon_path)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{edit_key_path}\\command") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{open_cmd}" "%1"')
                
        return True
    except Exception as e:
        log.error(f"Failed to register extension {extension}: {e}")
        return False

def setup_all_associations(force=False, parent_window=None):
    """
    Sets up all associations (.vsmart, .vsndevts, .hbat).
    If force is False, it will prompt the user if an extension is already taken.
    """
    fileedit = get_fileedit_path()
    smartprop_icon = get_smartprop_icon_path()
    vsnd_icon = get_vsnd_icon_path()
    
    associations = [
        (".vsmart", "Hammer5Tools.SmartProp", "SmartProp File", smartprop_icon),
        (".vsndevts", "Hammer5Tools.SoundEvent", "SoundEvent File", vsnd_icon),
        (".hbat", "Hammer5Tools.Batch", "Hammer Batch File", smartprop_icon)
    ]
    
    for ext, prog_id, desc, icon in associations:
        current_prog, is_us = check_association(ext)
        
        should_register = False
        if is_us or current_prog is None or force:
            should_register = True
        else:
            # It's taken by something else
            if parent_window:
                reply = QMessageBox.question(
                    parent_window,
                    "File Association Conflict",
                    f"The extension {ext} is already associated with '{current_prog}'.\n\n"
                    f"Do you want to change it to Hammer5Tools?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    should_register = True
            else:
                # No UI context, maybe we skip or force? 
                # If it's a first launch check, we might want to skip or just prompt later.
                pass
        
        if should_register:
            register_extension(ext, prog_id, desc, icon, fileedit)
            
    # Notify Shell
    try:
        import ctypes
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None) # SHCNE_ASSOCCHANGED
    except Exception:
        pass
