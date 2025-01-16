import zipfile
import os
import subprocess
import time
import argparse
import shutil
import tempfile
import base64

import sys
import pkg_resources

# Print Python version
print("Python version:", sys.version)

# Print installed Python packages
installed_packages = pkg_resources.working_set
installed_packages_list = sorted(["%s==%s" % (i.key, i.version) for i in installed_packages])
print("Python packages:")
for package in installed_packages_list:
    print(package)

def print_elapsed_time(stage_name, start_time):
    elapsed_time = time.time() - start_time
    print(f"{stage_name} took {elapsed_time:.2f} seconds")

def kill_process(process_name):
    subprocess.run(
        ["taskkill", "/F", "/IM", process_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def build_hammer5_tools():
    subprocess.run([
        'pyinstaller',
        '--name=Hammer5Tools',
        '--noupx', '--distpath=hammer5tools',
        '--noconfirm',
        '--onefile',
        '--windowed',
        '--strip',
        '--optimize=2',
        '--icon=src/appicon.ico',
        '--add-data=src/appicon.ico;.',
        '--add-data=src/images;images/',
        '--add-data=src/qt_styles;qt_styles/',
        '--exclude-module=PyQt5',
        '--exclude-module=PySide6.QtWebEngineWidgets',
        '--exclude-module=PySide6.QtWebEngineCore',
        '--exclude-module=PySide6.QtWebEngine',
        '--exclude-module=PySide6.QtMultimediaWidgets',
        '--exclude-module=PySide6.QtCharts',
        '--exclude-module=PySide6.QtSql',
        '--exclude-module=PySide6.QtTest',
        '--exclude-module=PySide6.QtQml',
        '--exclude-module=PySide6.QtQuick',
        '--exclude-module=PySide6.QtQuickWidgets',
        '--exclude-module=PySide6.QtPositioning',
        '--exclude-module=PySide6.QtLocation',
        '--exclude-module=PySide6.QtBluetooth',
        '--exclude-module=PySide6.QtNfc',
        '--exclude-module=PySide6.QtRemoteObjects',
        '--exclude-module=PySide6.QtTextToSpeech',
        '--exclude-module=PySide6.QtWebSockets',
        '--exclude-module=PySide6.QtSensors',
        '--hidden-import=tqdm',
        'src/main.py'
    ], check=True)

def build_updater():
    subprocess.run([
        'pyinstaller',
        '--name=Hammer5Tools_Updater',
        '--onefile',
        '--optimize=2',
        '--icon=src/appicon.ico',
        '--exclude-module=PySide6',
        '--exclude-module=PyQt5',
        '--exclude-module=pandas',
        '--exclude-module=numpy',
        '--hidden-import=psutil',
        '--hidden-import=colorama',
        '--hidden-import=tqdm',
        '--distpath=hammer5tools',
        'src/updater.py'
    ], check=True)

def archive_files(folder_path, output_path, excluded_files, excluded_paths):
    def should_exclude(file_name, file_path):
        if file_name in excluded_files:
            return True
        for excluded_path in excluded_paths:
            if excluded_path in os.path.normpath(file_path):
                return True
        return False

    with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, folder_path)
                if should_exclude(file, rel_path):
                    continue
                archive.write(file_path, rel_path)
    print(f"Archived files to {output_path}")

def create_installer(folder_path, output_exe):
    if os.path.exists(output_exe):
        try:
            os.remove(output_exe)
        except PermissionError:
            print(f"Error: Cannot delete existing installer `{output_exe}`. Make sure it is not running and you have permission to delete it.")
            return

    archive_name = 'application.zip'
    excluded_files = {'hammer5tools.7z', 'hammer5tools.zip', 'hammer5tools_setup.exe'}
    excluded_paths = ['SoundEventEditor\\sounds']

    archive_files(folder_path, archive_name, excluded_files, excluded_paths)

    with open(archive_name, 'rb') as f:
        zip_data = f.read()

    encoded_zip_data = base64.b64encode(zip_data).decode('utf-8')

    installer_script = f"""import sys
import os
import base64
import zipfile
import tempfile
import shutil
import subprocess
import threading
import time
import ctypes

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog

import win32com.client

def main():
    def install():
        install_button.config(state='disabled')
        install_dir = install_dir_var.get()
        if not install_dir:
            messagebox.showerror("Error", "Please select an installation directory.")
            install_button.config(state='normal')
            return
        if not install_dir.lower().endswith("hammer5tools"):
            install_dir = os.path.join(install_dir, "hammer5tools")
        install_dir = os.path.normpath(install_dir)

        try:
            status_label.config(text="Extracting files...")
            root.update_idletasks()
            zip_data_local = base64.b64decode("{encoded_zip_data}")
            os.makedirs(install_dir, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_zip:
                temp_zip.write(zip_data_local)
                temp_zip_path = temp_zip.name
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(install_dir)
            status_label.config(text="Installation complete.")
            if desktop_shortcut_var.get() == 1:
                create_desktop_shortcut(install_dir)
            if start_menu_shortcut_var.get() == 1:
                create_start_menu_shortcut(install_dir)
            exe_path = os.path.join(install_dir, "Hammer5Tools.exe")
            if messagebox.askyesno("Launch Application", "Do you want to launch Hammer 5 Tools now?"):
                subprocess.Popen([exe_path], cwd=install_dir, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os._exit(0) # Exit immediately after launching or skipping the launch
        except Exception as e:
            messagebox.showerror("Installation Error", str(e))
            install_button.config(state='normal')
        finally:
            if 'temp_zip_path' in locals():
                os.remove(temp_zip_path)

    def create_desktop_shortcut(install_path):
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut_path = os.path.join(desktop_path, "Hammer 5 Tools.lnk")
        target = os.path.join(install_path, "Hammer5Tools.exe")
        working_dir = install_path

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = working_dir
        shortcut.IconLocation = target
        shortcut.save()

    def create_start_menu_shortcut(install_path):
        start_menu_path = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs")
        shortcut_path = os.path.join(start_menu_path, "Hammer 5 Tools.lnk")
        target = os.path.join(install_path, "Hammer5Tools.exe")
        working_dir = install_path

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = working_dir
        shortcut.IconLocation = target
        shortcut.save()

    def browse_directory():
        directory = filedialog.askdirectory(initialdir=install_dir_var.get())
        if directory:
            install_dir_var.set(directory)

    root = tk.Tk()
    root.title("Hammer 5 Tools Installer")
    root.resizable(False, False)
    try:
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, "appicon.ico")
        else:
            icon_path = "appicon.ico"
        root.iconbitmap(icon_path)
    except Exception:
        pass

    def set_dark_theme():
        style = ttk.Style()
        root.configure(bg="#2e2e2e")
        style.theme_use("clam")
        style.configure(".", background="#2e2e2e", foreground="#ffffff", fieldbackground="#3e3e3e")
        style.map("TButton", background=[("active", "#393939")])
        style.map("TCheckbutton", background=[("active", "#2e2e2e")])

    set_dark_theme()

    def center_window():
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"+{{x}}+{{y}}")

    install_dir_var = tk.StringVar()
    default_install_dir = os.path.expandvars(r"%ProgramFiles%")
    install_dir_var.set(default_install_dir)

    desktop_shortcut_var = tk.IntVar(value=1)
    start_menu_shortcut_var = tk.IntVar(value=1)

    frame = ttk.Frame(root, padding=20)
    frame.grid(row=0, column=0, sticky="NSEW")

    intro_label = ttk.Label(frame, text="Welcome to the Hammer 5 Tools Installer", font=("Helvetica", 14))
    intro_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))

    install_dir_label = ttk.Label(frame, text="Installation Directory:")
    install_dir_label.grid(row=1, column=0, sticky="E")

    install_dir_entry = ttk.Entry(frame, textvariable=install_dir_var, width=40)
    install_dir_entry.grid(row=1, column=1, padx=(5,5))

    browse_button = ttk.Button(frame, text="Browse...", command=browse_directory)
    browse_button.grid(row=1, column=2, padx=(5,0))

    desktop_shortcut_check = ttk.Checkbutton(frame, text="Create Desktop Shortcut", variable=desktop_shortcut_var)
    desktop_shortcut_check.grid(row=2, column=0, columnspan=3, sticky="W", pady=(10,0))

    start_menu_shortcut_check = ttk.Checkbutton(frame, text="Add to Start Menu", variable=start_menu_shortcut_var)
    start_menu_shortcut_check.grid(row=3, column=0, columnspan=3, sticky="W")

    status_label = ttk.Label(frame, text="")
    status_label.grid(row=4, column=0, columnspan=3, pady=(10, 0))

    install_button = ttk.Button(frame, text="Install", command=lambda: threading.Thread(target=install).start())
    install_button.grid(row=5, column=0, columnspan=3, pady=(10, 0))

    center_window()
    root.mainloop()

if __name__ == "__main__":
    main()
"""

    with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_installer_script:
        temp_installer_script.write(installer_script)
        temp_installer_path = temp_installer_script.name

    try:
        subprocess.run([
            'pyinstaller',
            '--onefile',
            '--windowed',
            '--noconfirm',
            '--name',
            'hammer5tools_setup',
            '--icon',
            'src/appicon.ico',
            '--add-data',
            'src/appicon.ico;.',
            '--hidden-import',
            'win32com',
            '--hidden-import',
            'win32com.shell',
            '--hidden-import',
            'pythoncom',
            '--distpath',
            os.path.dirname(output_exe),
            temp_installer_path
        ], check=True)
        print(f"Created installer: `{output_exe}`")
    finally:
        if os.path.exists(temp_installer_path):
            os.remove(temp_installer_path)
        if os.path.exists(archive_name):
            os.remove(archive_name)
        build_folder = 'build'
        if os.path.exists(build_folder):
            shutil.rmtree(build_folder)
        spec_file = os.path.splitext(temp_installer_path)[0] + '.spec'
        if os.path.exists(spec_file):
            os.remove(spec_file)

def main():
    parser = argparse.ArgumentParser(description="Build and archive Hammer 5 Tools and Updater.")
    parser.add_argument('--build-all', action='store_true', help="Build both Hammer 5 Tools and Updater.")
    parser.add_argument('--build-hammer5', action='store_true', help="Build only Hammer 5 Tools.")
    parser.add_argument('--build-updater', action='store_true', help="Build only Updater.")
    parser.add_argument('--archive', action='store_true', help="Archive the build outputs.")
    parser.add_argument('--installer', action='store_true', help="Create an installer with a GUI.")
    args = parser.parse_args()

    overall_start_time = time.time()

    stage_start_time = time.time()
    kill_process("Hammer5Tools.exe")
    print_elapsed_time("Kill process", stage_start_time)

    try:
        if args.build_all or args.build_hammer5:
            stage_start_time = time.time()
            build_hammer5_tools()
            print_elapsed_time("Hammer 5 Tools Build", stage_start_time)

        if args.build_all or args.build_updater:
            stage_start_time = time.time()
            build_updater()
            print_elapsed_time("Updater Build", stage_start_time)
    except subprocess.CalledProcessError as e:
        print(f"Error during build: {e}")
        return

    output_folder = 'hammer5tools'
    zip_output_path = os.path.join(output_folder, 'hammer5tools.zip')
    installer_output_path = os.path.join(output_folder, 'hammer5tools_setup.exe')

    if args.archive:
        stage_start_time = time.time()
        excluded_files = {'hammer5tools.7z', 'hammer5tools_setup.exe', 'hammer5tools.zip', 'settings.ini'}
        excluded_paths = ['SoundEventEditor\\sounds']
        archive_files(output_folder, zip_output_path, excluded_files, excluded_paths)
        print_elapsed_time("Archiving files", stage_start_time)

    if args.installer:
        stage_start_time = time.time()
        create_installer(output_folder, installer_output_path)
        print_elapsed_time("Creating installer", stage_start_time)

    print_elapsed_time("Overall process", overall_start_time)

if __name__ == "__main__":
    main()