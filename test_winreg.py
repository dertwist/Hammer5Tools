import winreg
import sys
import os

def get_default_application(file_extension):
    try:
        if file_extension.startswith('.'):
            file_extension = file_extension[1:]
        
        file_type = None
        # Try getting from UserChoice first
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\.{file_extension}\\UserChoice") as key:
                file_type = winreg.QueryValueEx(key, "ProgId")[0]
                print("Found UserChoice:", file_type)
        except (FileNotFoundError, OSError, winreg.error) as e:
            pass

        if not file_type:
            # Fallback to HKEY_CLASSES_ROOT
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f".{file_extension}") as key:
                    file_type = winreg.QueryValue(key, "")
                    print("Found HKCR:", file_type)
            except (FileNotFoundError, OSError, winreg.error) as e:
                pass

        if not file_type:
            return None
            
        command = None
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{file_type}\\shell\\open\\command") as key:
                command = winreg.QueryValue(key, "")
        except FileNotFoundError:
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{file_type}\\shell\\edit\\command") as key:
                    command = winreg.QueryValue(key, "")
            except FileNotFoundError:
                pass
        
        if command:
            import shlex
            try:
                parts = shlex.split(command)
                if parts:
                    exe_path = parts[0]
                    app_name = os.path.basename(exe_path)
                    return app_name, exe_path
            except ValueError:
                if command.startswith('"'):
                    end_quote = command.find('"', 1)
                    if end_quote != -1:
                        exe_path = command[1:end_quote]
                        app_name = os.path.basename(exe_path)
                        return app_name, exe_path
                else:
                    parts = command.split()
                    if parts:
                        exe_path = parts[0]
                        app_name = os.path.basename(exe_path)
                        return app_name, exe_path
        
        return None
        
    except Exception as e:
        print("Error", e)
        return None

print("txt", get_default_application(".txt"))
print("png", get_default_application(".png"))
