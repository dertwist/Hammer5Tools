import os
import shutil
import psutil
import requests
import zipfile
import io
import tempfile
from tqdm import tqdm
from colorama import init, Fore
import subprocess
import sys
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if sys.argv[-1] != 'asadmin':
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([script] + sys.argv[1:] + ['asadmin'])
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            sys._exit(0)
        except Exception as e:
            print("Error", f"Failed to elevate privileges: {str(e)}")
            return False
    return True

# Initialize colorama
init(autoreset=True)

def kill_main_app(app_name='Hammer5Tools.exe'):
    """Kills the specified main application if it's running."""
    processes = [process for process in psutil.process_iter() if process.name() == app_name]
    if processes:
        for process in processes:
            process.kill()
            print(Fore.GREEN + f'{app_name} process killed successfully.')
    else:
        print(Fore.YELLOW + f'{app_name} process not found.')

def download_and_extract(url, target_path):
    """Downloads a zip file from the given URL and extracts it to the target path."""
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        total_size = int(response.headers.get('content-length', 0))
        zip_file = io.BytesIO()

        with tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024, desc="Downloading") as pbar:
            for data in response.iter_content(chunk_size=1024):
                zip_file.write(data)
                pbar.update(len(data))

        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(target_path)
        print(Fore.GREEN + 'Download and extraction successful.')
    else:
        print(Fore.RED + f'Failed to download update. HTTP Status Code: {response.status_code}')
        return False
    return True

def create_batch_script(update_path, program_path, updater_name):
    """
    Creates a batch script to handle the self-update.
    The script:
    1. Waits for the Python script to exit.
    2. Deletes old files.
    3. Moves updated files to their locations.
    4. Restarts the updated updater.
    """
    batch_path = os.path.join(tempfile.gettempdir(), "self_update.bat")
    with open(batch_path, 'w') as f:
        f.write(f"""
@echo off
setlocal enabledelayedexpansion

:: Wait for the Python updater to exit
echo Waiting for Python updater to close...
set RETRY_COUNT=10
:WAIT
timeout /t 1 >nul
tasklist | find /i "{os.path.basename(sys.executable)}" >nul
if not errorlevel 1 (
    set /a RETRY_COUNT-=1
    if !RETRY_COUNT! gtr 0 goto WAIT
    echo Failed to wait for the updater to exit.
    exit /b 1
)

:: Perform the update
echo Performing file updates...

:: Delete the old updater
if exist "{os.path.join(program_path, updater_name)}" del "{os.path.join(program_path, updater_name)}"

:: Move new updater to the program path
move "{os.path.join(update_path, updater_name)}" "{os.path.join(program_path, updater_name)}"

:: Move other updated files
xcopy /E /Y /Q "{update_path}\\*" "{program_path}\\"

:: Cleanup
echo Cleaning up temporary files...
rd /S /Q "{update_path}"

:: Restart the updated application
echo Restarting the application...
start "" "{os.path.join(program_path, "Hammer5Tools")}"

:: Delete the batch script
del "%~f0"
exit /b 0
        """)
    print(Fore.GREEN + f"Batch script created at {batch_path}.")
    return batch_path

def main(dev_mode=False):
    """Main function to handle the update process."""
    # Kill the main application if running
    kill_main_app()

    # Initialize paths
    update_path = tempfile.mkdtemp(prefix="hammer5tools_update_")
    program_path = os.getcwd() if not dev_mode else os.path.normpath("D:/CG/Projects/Other/Hammer5Tools/hammer5tools")
    updater_name = "Hammer5Tools_Updater.exe"

    # Update URL
    update_url = 'https://github.com/dertwist/Hammer5Tools/releases/latest/download/Hammer5Tools.zip'

    # Download and extract the update
    if not download_and_extract(update_url, update_path):
        return

    # Remove old preset
    preset_hammer5tools = os.path.join(program_path, 'presets', 'hammer5tools')

    try:
        shutil.rmtree(preset_hammer5tools)
        print(Fore.GREEN + f"Successfully removed preset: {preset_hammer5tools}")
    except FileNotFoundError:
        print(Fore.YELLOW + f"Preset not found: {preset_hammer5tools}")
    except PermissionError:
        print(Fore.RED + f"Permission denied while trying to remove preset: {preset_hammer5tools}")
    except Exception as e:
        print(Fore.RED + f"An error occurred while removing preset: {e}")

    # Create batch script to handle file operations
    batch_script = create_batch_script(update_path, program_path, updater_name)

    # Run the batch script and exit Python
    try:
        print(Fore.CYAN + "Launching batch script for update...")
        subprocess.Popen(batch_script, shell=True)
    except Exception as e:
        print(Fore.RED + f"Failed to launch batch script: {e}")
    finally:
        print(Fore.CYAN + "Exiting Python script.")
        sys.exit()

if __name__ == "__main__":
    try:
        dev_mode = '--dev' in sys.argv
        if os.name == 'nt':
            if sys.argv[-1] != 'asadmin' and not is_admin():
                main(dev_mode)
            else:
                main(dev_mode)
        else:
            main(dev_mode)
    except Exception as e:
        print(Fore.RED + f"An error occurred: {e}")