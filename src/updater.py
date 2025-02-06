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
    except Exception:
        return False

def run_as_admin():
    if sys.argv[-1] != 'asadmin':
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([script] + sys.argv[1:] + ['asadmin'])
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            sys._exit(0)
        except Exception as e:
            print("Error:", f"Failed to elevate privileges: {str(e)}")
            return False
    return True

init(autoreset=True)

def kill_main_app():
    """
    This function is intentionally left empty.
    The main application will now be terminated via the PowerShell script.
    """
    pass

def download_and_extract(url, target_path):
    try:
        response = requests.get(url, stream=True)
    except Exception as e:
        print(Fore.RED + f"Error downloading update: {e}")
        return False

    if response.status_code == 200:
        total_size = int(response.headers.get('content-length', 0))
        zip_file = io.BytesIO()

        with tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024, desc="Downloading") as pbar:
            for data in response.iter_content(chunk_size=1024):
                zip_file.write(data)
                pbar.update(len(data))

        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(target_path)
            print(Fore.GREEN + 'Download and extraction successful.')
            return True
        except Exception as e:
            print(Fore.RED + f"Error extracting update: {e}")
            return False

    print(Fore.RED + f'Failed to download update. HTTP Status Code: {response.status_code}')
    return False

def create_powershell_script(update_path, program_path, updater_name):
    psscript_path = os.path.join(tempfile.gettempdir(), "self_update.ps1")
    script_content = f'''\
# PowerShell Self-Update Script
Write-Output "Waiting for Python updater to close..."
$retryCount = 10
while ($retryCount -gt 0 -and (Get-Process -Name "python" -ErrorAction SilentlyContinue)) {{
    Start-Sleep -Seconds 1
    $retryCount--
}}
if ($retryCount -le 0) {{
    Write-Error "Failed to wait for the updater to exit."
    exit 1
}}

Write-Output "Attempting to kill main application..."
$processName = "Hammer5Tools"
$processes = Get-Process | Where-Object {{ $_.ProcessName -eq $processName }}
if ($processes) {{
    foreach ($process in $processes) {{
        try {{
            $process | Stop-Process -Force
            Write-Output "Successfully terminated process with ID: $($process.Id)"
        }} catch {{
            Write-Error "Failed to terminate process with ID: $($process.Id)"
        }}
    }}
}} else {{
    Write-Output "No running instances of $processName found."
}}

Write-Output "Performing file updates..."

# Delete the old updater if it exists
$oldUpdater = Join-Path -Path "{program_path}" -ChildPath "{updater_name}"
if (Test-Path $oldUpdater) {{
    Remove-Item $oldUpdater -Force
}}

# Move new updater to the program path
$sourceUpdater = Join-Path -Path "{update_path}" -ChildPath "{updater_name}"
Move-Item -Path $sourceUpdater -Destination "{program_path}" -Force

# Move other updated files
Copy-Item -Path (Join-Path "{update_path}" "*") -Destination "{program_path}" -Recurse -Force

Write-Output "Cleaning up temporary files..."
Remove-Item -Path "{update_path}" -Recurse -Force

Write-Output "Restarting the application..."
Start-Process -FilePath (Join-Path "{program_path}" "Hammer5Tools.exe")

# Remove this PowerShell script
Remove-Item -Path $MyInvocation.MyCommand.Path -Force
exit 0
'''
    try:
        with open(psscript_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        print(Fore.GREEN + f"PowerShell script created at {psscript_path}.")
        return psscript_path
    except Exception as e:
        print(Fore.RED + f"Failed to create PowerShell script: {e}")
        return None

def main(dev_mode=False):
    update_path = tempfile.mkdtemp(prefix="hammer5tools_update_")
    program_path = os.getcwd() if not dev_mode else os.path.normpath("D:/CG/Projects/Other/Hammer5Tools/hammer5tools")
    updater_name = "Hammer5Tools_Updater.exe"
    update_url = 'https://github.com/dertwist/Hammer5Tools/releases/latest/download/Hammer5Tools.zip'

    if not download_and_extract(update_url, update_path):
        return

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

    ps_script = create_powershell_script(update_path, program_path, updater_name)
    if not ps_script:
        return

    try:
        print(Fore.CYAN + "Launching PowerShell script for update...")
        subprocess.Popen(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", ps_script], shell=True)
    except Exception as e:
        print(Fore.RED + f"Failed to launch PowerShell script: {e}")
    finally:
        print(Fore.CYAN + "Exiting Python script.")
        sys.exit()

if __name__ == "__main__":
    try:
        dev_mode = '--dev' in sys.argv
        if os.name == 'nt' and not is_admin():
            run_as_admin()
        else:
            main(dev_mode)
    except Exception as e:
        print(Fore.RED + f"An error occurred: {e}")