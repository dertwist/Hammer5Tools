import subprocess
import zipfile
import os
# Command 1
subprocess.run(['pyinstaller', '--name=Hammer5Tools', '--noconfirm', '--onefile', '--windowed', '--optimize=2', '--icon=appicon.ico', '--add-data=appicon.ico:.', '--add-data=images;images/', '--add-data=qt_styles;qt_styles/', '--noupx', '--distpath=hammer5tools', '--exclude-module=PyQt5', 'main.py'])

# Command 2
subprocess.run(['pyinstaller', '--name=Hammer5Tools_Updater', '--noconfirm', '--onefile', '--optimize=2', '--icon=appicon.ico', '--noupx', '--distpath=hammer5tools', '--exclude-module=PySide6', '--exclude-module=PyQt5', '--exclude-module=numpy', '--exclude-module=PIL', '--exclude', 'matplotlib', '--exclude', 'pandas', 'updater.py'])



folder_path = '../hammer5tools'
output_path = '../hammer5tools/hammer5tools.zip'


files_to_archive = [file for file in os.listdir(folder_path) if file != 'hammer5tools.zip']

with zipfile.ZipFile(output_path, 'w') as archive:
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file != 'hammer5tools.zip':  # Exclude 'hammer5tools.zip'
                file_path = os.path.join(root, file)
                archive.write(file_path, os.path.relpath(file_path, folder_path))

# Command 3 (commented out)
# subprocess.run(['pyinstaller', '--name=Hammer5Tools', '--noconfirm', '--windowed', '--optimize=2', '--icon=appicon.ico', '--add-data=appicon.ico:.', '--add-data=images;images/', '--noupx', 'main.py'])

# Command 4 (commented out)
# subprocess.run(['python', '-m', 'nuitka', '--onefile', '--windows-console-mode=disable', '--enable-plugin=pyside6', '--output-filename=H5T C++', '--windows-icon-from-ico=appicon.ico', 'main.py'])