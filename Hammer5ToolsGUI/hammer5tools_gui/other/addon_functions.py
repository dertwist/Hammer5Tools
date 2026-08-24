from PySide6.QtWidgets import QMessageBox
from hammer5tools_gui.other.ncm_setup import NCM_mode_setup
from hammer5tools_gui.other.assettypes import ensure_vsmart_configured
from hammer5tools_gui.settings.main import get_addon_name, get_cs2_path, get_settings_bool, set_settings_bool, get_settings_value, \
    set_settings_value
import shutil, psutil, os, subprocess
from hammer5tools_gui.common import *
from hammer5tools_gui.widgets import exception_handler


@exception_handler
def delete_addon(ui=None):
    cs2_path = get_cs2_path()
    if cs2_path is None:
        QMessageBox.warning(None, "CS2 Path Not Set", 
                          "CS2 installation path is not set. Please set it in Settings > General > CS2 Path.")
        return False
        
    addon_name = get_addon_name()
    if not addon_name:
        QMessageBox.warning(None, "No Addon Selected", 
                          "No addon is selected for deletion.")
        return False
        
    delete_paths = [
        os.path.join(cs2_path, 'content', 'csgo_addons', addon_name),
        os.path.join(cs2_path, 'game', 'csgo_addons', addon_name)
    ]
    
    reply = QMessageBox.question(None, 'Remove Addon', 
                               f"Are you sure you want to permanently delete the addon '{addon_name}'?\n"
                               "This will delete BOTH content and game folders!\n\n"
                               "This action cannot be undone.", 
                               QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    
    if reply == QMessageBox.Yes:
        try:
            for path in delete_paths:
                if os.path.exists(path):
                    shutil.rmtree(path)
                    print(f'Successfully deleted: {path}')
                else:
                    print(f'Path does not exist: {path}')
            
            # If UI is provided, we can try to update it directly, 
            # though usually the caller handles the refresh.
            if ui and hasattr(ui, 'ComboBoxSelectAddon'):
                index = ui.ComboBoxSelectAddon.findText(addon_name)
                if index != -1:
                    ui.ComboBoxSelectAddon.removeItem(index)
            
            QMessageBox.information(None, 'Addon Deleted', f"The addon '{addon_name}' has been successfully deleted.")
            return True
        except Exception as e:
            QMessageBox.critical(None, 'Deletion Failed', f"Failed to delete the addon '{addon_name}'. You may need administrative permissions.\nError: {str(e)}")
            return False
    else:
        print('Addon deletion cancelled')
        return False

def launch_cs2_process(cs2_exe_path: str, commands: str = "") -> bool:
    """
    Launch CS2 as an independent, detached process so that it survives
    Hammer5Tools closing, minimizing, updating, or stopping VS Code debug sessions.
    """
    cs2_exe_path = str(cs2_exe_path)
    commands = str(commands).strip() if commands else ""

    if sys.platform == 'win32':
        work_dir = os.path.dirname(cs2_exe_path)
        if not os.path.exists(work_dir):
            work_dir = "C:\\"

        # 1. Primary: Obtain the active Windows Explorer desktop shell dispatch.
        # This delegates process creation to the actual explorer.exe desktop process,
        # so CS2's parent process in Windows is explorer.exe (NOT python.exe / VS Code / debugpy).
        try:
            import win32com.client
            shell = win32com.client.Dispatch("Shell.Application")
            desktop_window = shell.Windows().FindWindowSW(0, 0, 8, 0, 1)  # SWC_DESKTOP=8, SWFO_NEEDDISPATCH=1
            if desktop_window:
                desktop_window.Document.Application.ShellExecute(
                    cs2_exe_path,
                    commands,
                    work_dir,
                    "open",
                    1  # SW_SHOWNORMAL
                )
                return True
        except Exception:
            pass

        # 2. Secondary: Launch via WMI Win32_Process.
        # WMI process creation is performed by the Windows WMI service (WmiPrvSE.exe),
        # placing the spawned process completely outside VS Code's debugger process tree.
        try:
            cmd = f'"{cs2_exe_path}" {commands}'.strip() if commands else f'"{cs2_exe_path}"'
            escaped_cmd = cmd.replace('"', '`"')
            escaped_work_dir = work_dir.replace('"', '`"')
            ps_script = (
                f'Invoke-CimMethod -ClassName Win32_Process -MethodName Create '
                f'-Arguments @{{CommandLine = "{escaped_cmd}"; CurrentDirectory = "{escaped_work_dir}"}}'
            )
            ret = subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-Command', ps_script],
                capture_output=True,
                check=False
            )
            if ret.returncode == 0:
                return True
        except Exception:
            pass

        # 3. Tertiary: ShellExecuteW via shell32
        try:
            import ctypes
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,
                "open",
                cs2_exe_path,
                commands,
                work_dir if os.path.exists(work_dir) else None,
                1  # SW_SHOWNORMAL
            )
            if ret > 32:
                return True
        except Exception as e:
            print(f"ShellExecute failed: {e}, falling back to subprocess.Popen")

    # 4. Fallback: subprocess.Popen with full detachment flags and null standard handles
    flags_breakaway = (
        getattr(subprocess, 'DETACHED_PROCESS', 0x00000008)
        | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200)
        | 0x00000001  # CREATE_BREAKAWAY_FROM_JOB
    )
    flags_detached = (
        getattr(subprocess, 'DETACHED_PROCESS', 0x00000008)
        | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200)
    )

    cmd = f'"{cs2_exe_path}" {commands}'.strip() if commands else f'"{cs2_exe_path}"'
    popen_kwargs = dict(
        close_fds=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )

    try:
        subprocess.Popen(
            cmd,
            creationflags=flags_breakaway if sys.platform == 'win32' else 0,
            start_new_session=True if sys.platform != 'win32' else False,
            **popen_kwargs
        )
        return True
    except (PermissionError, OSError):
        # Fallback if the job object does not allow breakaway
        subprocess.Popen(
            cmd,
            creationflags=flags_detached if sys.platform == 'win32' else 0,
            start_new_session=True if sys.platform != 'win32' else False,
            **popen_kwargs
        )
        return True


def assemble_commands(commands:str, addon_name):
    return commands.replace('addon_name', addon_name)


def __launch_addon():
    addon_name = get_addon_name()
    cs2_path = get_cs2_path()
    
    if cs2_path is None:
        QMessageBox.warning(None, "CS2 Path Not Set", 
                          "CS2 installation path is not set. Please set it in Settings > General > CS2 Path.")
        return
        
    if not addon_name:
        QMessageBox.warning(None, "No Addon Selected", 
                          "No addon is selected for launch.")
        return

    commands = get_settings_value("LAUNCH", "commands")
    if not commands:
        commands = default_commands
        set_settings_value("LAUNCH", "commands", commands)

    commands = assemble_commands(commands, addon_name)
    
    # Ensure -netconport 2121 is always included (mandatory flag)
    if '-netconport' not in commands:
        commands += ' -netconport 2121'

    # Ensure -disable_workshop_command_filtering is always included (mandatory flag)
    if '-disable_workshop_command_filtering' not in commands:
        commands += ' -disable_workshop_command_filtering'

    cs2_exe_path = os.path.join(cs2_path, "game", "bin", "win64", "cs2.exe")
    
    if not os.path.exists(cs2_exe_path):
        QMessageBox.warning(None, "CS2 Executable Not Found", 
                          f"CS2 executable not found at:\n{cs2_exe_path}\n\n"
                          "Please verify your CS2 installation path in Settings.")
        return

    ncm_mode = get_settings_bool("LAUNCH", "ncm_mode", default=False)

    if ncm_mode:
        NCM_mode_setup(cs2_path)
        commands = f'{commands} -nocustomermachine'

    launch_cs2_process(cs2_exe_path, commands)


@exception_handler
def configure_particle_editor():
    """
    Automatically configure the Particle Editor in sdkenginetools.txt.
    Finds the "pet" (Particle Editor) entry and removes any m_ExcludeFromMods
    restriction to ensure it's available for CS:GO addons.
    """
    cs2_path = get_cs2_path()
    if cs2_path is None:
        return

    sdk_tools_path = os.path.join(cs2_path, "game", "bin", "sdkenginetools.txt")

    if not os.path.exists(sdk_tools_path):
        return

    try:
        import re

        with open(sdk_tools_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        modified = False
        inside_pet = False
        inside_exclude = False
        skip_lines = []

        for i, line in enumerate(lines):
            if 'm_Name = "pet"' in line:
                inside_pet = True
            if inside_pet and re.match(r'^\s*\},?\s*$', line):
                inside_pet = False

            if inside_pet and 'm_ExcludeFromMods' in line:
                inside_exclude = True
                skip_lines.append(i)
                modified = True

            elif inside_exclude:
                skip_lines.append(i)
                if ']' in line:
                    inside_exclude = False

        if modified:
            new_lines = [line for i, line in enumerate(lines) if i not in skip_lines]

            with open(sdk_tools_path, 'w', encoding='utf-8') as file:
                file.writelines(new_lines)

    except Exception as e:
        pass


@exception_handler
def launch_addon():
    ensure_vsmart_configured()
    configure_particle_editor()
    __launch_addon()


def kill_addon():
    subprocess.run(["taskkill", "/f", "/im", "cs2.exe"])