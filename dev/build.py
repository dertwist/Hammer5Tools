import zipfile
import os
import subprocess
import time

# Function to print elapsed time
def print_elapsed_time(stage_name, start_time):
    elapsed_time = time.time() - start_time
    print(f"{stage_name} took {elapsed_time:.2f} seconds")

# Record start time for the entire process
overall_start_time = time.time()

# Stage 1: Kill the process
stage_start_time = time.time()
subprocess.run(["taskkill", "/IM", "Hammer5Tools.exe"])
print_elapsed_time("Kill process", stage_start_time)

# Stage 2: Command 1
stage_start_time = time.time()
subprocess.run(['pyinstaller', '--name=Hammer5Tools', '--noconfirm', '--onefile', '--windowed', '--optimize=2', '--icon=src/appicon.ico', '--add-data=src/appicon.ico:.', '--add-data=src/images;images/', '--add-data=src/qt_styles;qt_styles/', '--noupx', '--distpath=hammer5tools', '--exclude-module=PyQt5', 'src/main.py'])
print_elapsed_time("Command 1", stage_start_time)

# Stage 3: Command 2
stage_start_time = time.time()
subprocess.run(['pyinstaller', '--name=Hammer5Tools_Updater', '--noconfirm', '--onefile', '--optimize=2', '--icon=src/appicon.ico', '--noupx', '--distpath=hammer5tools', '--exclude-module=PySide6', '--exclude-module=PyQt5', '--exclude-module=numpy', '--exclude-module=PIL', '--exclude', 'matplotlib', '--exclude', 'pandas', 'src/updater.py'])
print_elapsed_time("Command 2", stage_start_time)

# Stage 4: Archiving files
stage_start_time = time.time()
folder_path = 'hammer5tools'
output_path = 'hammer5tools/hammer5tools.zip'

excluded_files = {'hammer5tools.zip'}
excluded_extensions = {'.wav', '.mp3'}
def should_exclude(file_name):
    return file_name in excluded_files or any(file_name.endswith(ext) for ext in excluded_extensions)

with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_LZMA) as archive:
    for root, _, files in os.walk(folder_path):
        for file in files:
            if should_exclude(file):
                continue
            file_path = os.path.join(root, file)
            archive.write(file_path, os.path.relpath(file_path, folder_path))
print_elapsed_time("Archiving files", stage_start_time)

# Print total elapsed time
print_elapsed_time("Overall process", overall_start_time)