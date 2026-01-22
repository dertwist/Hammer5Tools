"""Windows Registry management for file associations.

Handles registration and unregistration of file types with the application.
Supports .vsmart and .vdata files for SmartProp Editor.
"""
import winreg
import os
import sys
import ctypes


class FileAssociationManager:
    """Manages Windows file associations via registry."""
    
    def __init__(self, app_path=None):
        """Initialize with application path.
        
        Args:
            app_path: Path to the application executable.
                     If None, uses sys.executable.
        """
        self.app_path = app_path or sys.executable
        self.app_dir = os.path.dirname(self.app_path)
        
    def register_vsmart(self):
        """Register .vsmart and .vdata file associations.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Create ProgID for SmartProp files
            progid = "Hammer5Tools.vsmart"
            
            # Register both .vsmart and .vdata extensions
            for ext in [".vsmart", ".vdata"]:
                with winreg.CreateKey(
                    winreg.HKEY_CURRENT_USER,
                    f"Software\\Classes\\{ext}"
                ) as key:
                    winreg.SetValue(key, "", winreg.REG_SZ, progid)
            
            # HKCU\Software\Classes\Hammer5Tools.vsmart
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                f"Software\\Classes\\{progid}"
            ) as key:
                winreg.SetValue(key, "", winreg.REG_SZ, "SmartProp File")
            
            # DefaultIcon
            icon_path = os.path.join(self.app_dir, "src", "icons", "vsmart.ico")
            if not os.path.exists(icon_path):
                # Fallback to app icon
                icon_path = f"{self.app_path},0"
            
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                f"Software\\Classes\\{progid}\\DefaultIcon"
            ) as key:
                winreg.SetValue(key, "", winreg.REG_SZ, icon_path)
            
            # Open command - passes file path as argument
            open_command = f'"{self.app_path}" "%1"'
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                f"Software\\Classes\\{progid}\\shell\\open\\command"
            ) as key:
                winreg.SetValue(key, "", winreg.REG_SZ, open_command)
            
            # Notify Windows shell of association changes
            self._notify_shell()
            
            return True
            
        except Exception as e:
            print(f"Failed to register .vsmart association: {e}")
            return False
    
    def unregister_vsmart(self):
        """Remove .vsmart and .vdata file associations.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Remove file extensions
            for ext in [".vsmart", ".vdata"]:
                try:
                    winreg.DeleteKey(
                        winreg.HKEY_CURRENT_USER,
                        f"Software\\Classes\\{ext}"
                    )
                except FileNotFoundError:
                    pass  # Already removed
            
            # Remove ProgID recursively
            self._delete_key_recursive(
                winreg.HKEY_CURRENT_USER,
                r"Software\Classes\Hammer5Tools.vsmart"
            )
            
            # Notify Windows shell
            self._notify_shell()
            
            return True
            
        except FileNotFoundError:
            # Already unregistered
            return True
        except Exception as e:
            print(f"Failed to unregister .vsmart association: {e}")
            return False
    
    def is_registered(self):
        """Check if .vsmart is registered to Hammer5Tools.
        
        Returns:
            bool: True if registered, False otherwise.
        """
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Classes\.vsmart"
            ) as key:
                progid = winreg.QueryValue(key, "")
                return progid == "Hammer5Tools.vsmart"
        except FileNotFoundError:
            return False
        except Exception:
            return False
    
    def _delete_key_recursive(self, root, path):
        """Recursively delete registry key and all subkeys.
        
        Args:
            root: Registry root (e.g., winreg.HKEY_CURRENT_USER)
            path: Path to the key to delete
        """
        try:
            with winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS) as key:
                # Delete all subkeys first
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, 0)
                        self._delete_key_recursive(root, f"{path}\\{subkey_name}")
                    except OSError:
                        break  # No more subkeys
            
            # Delete the key itself
            winreg.DeleteKey(root, path)
            
        except FileNotFoundError:
            pass  # Key doesn't exist
    
    def _notify_shell(self):
        """Notify Windows shell that file associations have changed."""
        try:
            SHCNE_ASSOCCHANGED = 0x08000000
            SHCNF_IDLIST = 0x0000
            ctypes.windll.shell32.SHChangeNotify(
                SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None
            )
        except Exception as e:
            print(f"Failed to notify shell of changes: {e}")
