import winreg
import os
import shlex

def get_default_application(file_extension):
    """
    Get the default application associated with a file extension on Windows.
    Returns the application name and path, or None if not found.
    """
    try:
        # Remove the dot from extension if present
        if file_extension.startswith('.'):
            file_extension = file_extension[1:]
        
        file_type = None
        
        # 1. Try getting from UserChoice first (Windows 8+)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\.{file_extension}\\UserChoice") as key:
                file_type, _ = winreg.QueryValueEx(key, "ProgId")
        except (FileNotFoundError, OSError, winreg.error):
            pass
            
        # 2. Fallback to HKEY_CLASSES_ROOT
        if not file_type:
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f".{file_extension}") as key:
                    file_type, _ = winreg.QueryValueEx(key, "")
            except (FileNotFoundError, OSError, winreg.error):
                pass
                
        if not file_type:
            return None
            
        command = None
        # 3. Get the command associated with the file type
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{file_type}\\shell\\open\\command") as key:
                command, _ = winreg.QueryValueEx(key, "")
        except (FileNotFoundError, OSError, winreg.error):
            # Try alternative path
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{file_type}\\shell\\edit\\command") as key:
                    command, _ = winreg.QueryValueEx(key, "")
            except (FileNotFoundError, OSError, winreg.error):
                pass
        
        if command:
            # Extract the executable path from the command
            # Commands often contain quotes and parameters like: "C:\Program Files\App\app.exe" "%1"
            import shlex
            try:
                parts = shlex.split(command)
                if parts:
                    exe_path = parts[0]
                    app_name = os.path.basename(exe_path)
                    return app_name, exe_path
            except ValueError:
                # Fallback for malformed commands
                if command.startswith('"'):
                    end_quote = command.find('"', 1)
                    if end_quote != -1:
                        exe_path = command[1:end_quote]
                        app_name = os.path.basename(exe_path)
                        return app_name, exe_path
                else:
                    # Simple case without quotes
                    parts = command.split()
                    if parts:
                        exe_path = parts[0]
                        app_name = os.path.basename(exe_path)
                        return app_name, exe_path
        
        return None
        
    except Exception:
        return None

print("txt", get_default_application(".txt"))
print("png", get_default_application(".png"))
