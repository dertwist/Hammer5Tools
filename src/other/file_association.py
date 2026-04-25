import os
import sys
import winreg
from pathlib import Path
from PySide6.QtWidgets import QMessageBox

def get_fileedit_path():
    """Returns the absolute path to fileedit.exe next to the main executable."""
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent.parent
    
    fileedit = base_dir / "fileedit.exe"
    return str(fileedit)

def get_smartprop_icon_path():
    """Returns the absolute path to smartprop.ico."""
    if getattr(sys, 'frozen', False):
        # In frozen builds, it should be in the app root or defaults
        base_dir = Path(sys.executable).parent
        # Try several common locations
        candidates = [
            base_dir / "app" / "icons" / "smartprop.ico",
            base_dir / "icons" / "smartprop.ico",
            base_dir / "defaults" / "icons" / "smartprop.ico"
        ]
        for c in candidates:
            if c.exists():
                return str(c)
    
    # Development fallback
    dev_path = Path(__file__).parent.parent / "icons" / "smartprop.ico"
    return str(dev_path)

def check_association(extension):
    """
    Checks the current association for an extension.
    Returns:
        prog_id (str): The ProgID associated with the extension, or None.
        is_us (bool): True if it's already associated with Hammer5Tools.
    """
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
            
        # Add "Edit with Hammer5Tools" context menu for smartprops
        if extension == ".vsmart":
            edit_key_path = f"{prog_key_path}\\shell\\editwith"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, edit_key_path) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Edit With Hammer5Tools")
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon_path)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{edit_key_path}\\command") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{open_cmd}" "%1"')
                
        return True
    except Exception as e:
        print(f"Failed to register extension {extension}: {e}")
        return False

def setup_all_associations(force=False, parent_window=None):
    """
    Sets up all associations (.vsmart, .vsndevts, .hbat).
    If force is False, it will prompt the user if an extension is already taken.
    """
    fileedit = get_fileedit_path()
    smartprop_icon = get_smartprop_icon_path()
    
    # For now we use the same icon for others, or we could add more specific ones later
    # The user specifically mentioned smartprop.ico for associations.
    
    associations = [
        (".vsmart", "Hammer5Tools.SmartProp", "SmartProp File", smartprop_icon),
        (".vsndevts", "Hammer5Tools.SoundEvent", "SoundEvent File", smartprop_icon),
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
