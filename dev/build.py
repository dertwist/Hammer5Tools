import zipfile
import os
import subprocess
import time
import argparse
import shutil
import tempfile
import sys
import base64

def print_elapsed_time(stage_name, start_time):
    elapsed_time = time.time() - start_time
    print(f"{stage_name} took {elapsed_time:.2f} seconds")

def kill_process(process_name):
    """Forcefully kills a process given its name."""
    subprocess.run(
        ["taskkill", "/F", "/IM", process_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def build_hammer5_tools():
    """Builds the Hammer 5 Tools executable."""
    subprocess.run([
        'pyinstaller', '--name=Hammer5Tools', '--noconfirm', '--onefile', '--windowed',
        '--optimize=2', '--icon=src/appicon.ico',
        '--add-data=src/appicon.ico;.',
        '--add-data=src/images;images/',
        '--add-data=src/qt_styles;qt_styles/',
        '--noupx', '--distpath=hammer5tools',
        '--exclude-module=PyQt5', 'src/main.py'
    ], check=True)

def build_updater():
    """Builds the Hammer 5 Tools Updater executable."""
    subprocess.run([
        'pyinstaller', '--name=Hammer5Tools_Updater', '--noconfirm', '--onefile',
        '--optimize=2', '--icon=src/appicon.ico',
        '--noupx', '--distpath=hammer5tools',
        '--exclude-module=PySide6',
        '--exclude-module=PyQt5',
        '--exclude-module=numpy',
        '--exclude-module=PIL',
        '--exclude', 'matplotlib',
        '--exclude', 'pandas',
        'src/updater.py'
    ], check=True)

def archive_files(folder_path, output_path, excluded_files, excluded_paths):
    """Archives the specified folder into a ZIP file, excluding specified files and paths."""
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
    """Creates a self-extracting installer with a GUI, dark theme, and additional features."""
    # Delete existing installer file if it exists
    if os.path.exists(output_exe):
        try:
            os.remove(output_exe)
        except PermissionError:
            print(f"Error: Cannot delete existing installer '{output_exe}'. Make sure it is not running and you have permission to delete it.")
            return

    # Paths
    archive_name = 'application.zip'

    # Excluded files and paths
    excluded_files = {'hammer5tools.7z', 'hammer5tools.zip', 'Hammer5ToolsInstaller.exe'}
    excluded_paths = ['SoundEventEditor\\sounds']

    # Archive the application files
    archive_files(folder_path, archive_name, excluded_files, excluded_paths)

    # Read the ZIP archive data
    with open(archive_name, 'rb') as f:
        zip_data = f.read()

    # Base64 encode the zip data
    encoded_zip_data = base64.b64encode(zip_data).decode('utf-8')

    # Installer script content with fixes
    installer_script = f"""
import sys
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

def main():
    def install():
        # Disable the install button
        install_button.config(state='disabled')
        # Get the selected installation directory
        install_dir = install_dir_var.get()
        if not install_dir:
            messagebox.showerror('Error', 'Please select an installation directory.')
            install_button.config(state='normal')
            return
        # Ensure the install_dir ends with 'hammer5tools'
        if not install_dir.lower().endswith('hammer5tools'):
            install_dir = os.path.join(install_dir, 'hammer5tools')
        install_dir = os.path.normpath(install_dir)  # Normalize the path

        try:
            # Update status
            status_label.config(text='Extracting files...')
            root.update_idletasks()
            # Decode the embedded ZIP data
            zip_data = base64.b64decode('{encoded_zip_data}')
            # Ensure the installation directory exists
            os.makedirs(install_dir, exist_ok=True)
            # Write the ZIP data to a temporary file
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_zip:
                temp_zip.write(zip_data)
                temp_zip_path = temp_zip.name
            try:
                # Extract the ZIP archive
                with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(install_dir)
                # Update status
                status_label.config(text='Installation complete.')
                # Create shortcuts if requested
                if desktop_shortcut_var.get() == 1:
                    create_desktop_shortcut(install_dir)
                if start_menu_shortcut_var.get() == 1:
                    create_start_menu_shortcut(install_dir)
                # Optionally, run the application
                exe_path = os.path.join(install_dir, 'Hammer5Tools.exe')
                if os.path.exists(exe_path):
                    if messagebox.askyesno('Launch Application', 'Do you want to launch Hammer 5 Tools now?'):
                        # Launch the application without console window
                        process = subprocess.Popen([exe_path], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                        # Wait for the application window to appear
                        window_title = 'Hammer 5 Tools'
                        timeout = 10  # seconds
                        while True:
                            hwnd = ctypes.windll.user32.FindWindowW(None, window_title)
                            if hwnd != 0 or timeout <= 0:
                                break
                            time.sleep(0.5)
                            timeout -= 0.5

                        if hwnd != 0:
                            root.destroy()  # Close installer only if the application window is found
                        else:
                            messagebox.showwarning('Warning', 'Hammer 5 Tools did not start within timeout.')
                            install_button.config(state='normal')  # Re-enable the button
                    else:
                        root.destroy()
                else:
                    messagebox.showwarning('Warning', 'Executable not found after installation.')
                    install_button.config(state='normal')
            finally:
                os.remove(temp_zip_path)
        except Exception as e:
            messagebox.showerror('Installation Error', str(e))
            install_button.config(state='normal')

    def create_desktop_shortcut(install_dir):
        try:
            desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
            shortcut_path = os.path.join(desktop, 'Hammer5Tools.lnk')
            target = os.path.join(install_dir, 'Hammer5Tools.exe')
            create_shortcut(target, shortcut_path, install_dir, icon_path=target)
        except Exception as e:
            messagebox.showerror('Shortcut Error', f'Failed to create desktop shortcut: {{e}}')

    def create_start_menu_shortcut(install_dir):
        try:
            start_menu = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs')
            shortcut_dir = os.path.join(start_menu, 'Hammer5Tools')
            os.makedirs(shortcut_dir, exist_ok=True)
            shortcut_path = os.path.join(shortcut_dir, 'Hammer5Tools.lnk')
            target = os.path.join(install_dir, 'Hammer5Tools.exe')
            create_shortcut(target, shortcut_path, install_dir, icon_path=target)
        except Exception as e:
            messagebox.showerror('Shortcut Error', f'Failed to create Start Menu shortcut: {{e}}')

    def create_shortcut(target, shortcut_path, working_directory, icon_path=None):
        import pythoncom
        from win32com.shell import shell
        shortcut = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink, None,
            pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
        shortcut.SetPath(target)
        shortcut.SetArguments('')
        shortcut.SetWorkingDirectory(working_directory)
        if icon_path:
            shortcut.SetIconLocation(icon_path, 0)
        shortcut.QueryInterface(pythoncom.IID_IPersistFile).Save(shortcut_path, 0)

    def browse_directory():
        directory = filedialog.askdirectory(initialdir=install_dir_var.get() or os.getcwd())
        if directory:
            install_dir_var.set(directory)

    # Create the main window
    root = tk.Tk()
    root.title('Hammer 5 Tools Installer')
    root.resizable(False, False)
    # Set application icon
    try:
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, 'appicon.ico')
        else:
            icon_path = 'appicon.ico'
        root.iconbitmap(icon_path)
    except Exception:
        pass

    # Apply dark theme
    def set_dark_theme():
        style = ttk.Style()
        root.configure(bg='#2e2e2e')
        style.theme_use('clam')
        style.configure('.', background='#2e2e2e', foreground='#ffffff', fieldbackground='#3e3e3e')
        style.map('TButton', background=[('active', '#393939')])
        style.map('TCheckbutton', background=[('active', '#2e2e2e')])

    set_dark_theme()

    # Center the window on the screen
    def center_window():
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'+{{x}}+{{y}}')

    # Installation directory
    install_dir_var = tk.StringVar()
    default_install_dir = os.path.expandvars(r'%ProgramFiles%')
    install_dir_var.set(default_install_dir)

    # Create variables for checkboxes
    desktop_shortcut_var = tk.IntVar(value=1)
    start_menu_shortcut_var = tk.IntVar(value=1)

    # Create and place widgets
    frame = ttk.Frame(root, padding=20)
    frame.grid(row=0, column=0, sticky='NSEW')

    intro_label = ttk.Label(frame, text='Welcome to the Hammer 5 Tools Installer', font=('Helvetica', 14))
    intro_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))

    install_dir_label = ttk.Label(frame, text='Installation Directory:')
    install_dir_label.grid(row=1, column=0, sticky='E')

    install_dir_entry = ttk.Entry(frame, textvariable=install_dir_var, width=40)
    install_dir_entry.grid(row=1, column=1, padx=(5,5))

    browse_button = ttk.Button(frame, text='Browse...', command=browse_directory)
    browse_button.grid(row=1, column=2, padx=(5,0))

    # Checkboxes for shortcuts
    desktop_shortcut_check = ttk.Checkbutton(frame, text='Create Desktop Shortcut', variable=desktop_shortcut_var)
    desktop_shortcut_check.grid(row=2, column=0, columnspan=3, sticky='W', pady=(10,0))

    start_menu_shortcut_check = ttk.Checkbutton(frame, text='Add to Start Menu', variable=start_menu_shortcut_var)
    start_menu_shortcut_check.grid(row=3, column=0, columnspan=3, sticky='W')

    status_label = ttk.Label(frame, text='')
    status_label.grid(row=4, column=0, columnspan=3, pady=(10, 0))

    install_button = ttk.Button(frame, text='Install', command=lambda: threading.Thread(target=install).start())
    install_button.grid(row=5, column=0, columnspan=3, pady=(10, 0))

    # Center the window after widgets are added
    center_window()

    root.mainloop()

if __name__ == '__main__':
    main()
    """

    # Write the installer script to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_installer_script:
        temp_installer_script.write(installer_script)
        temp_installer_path = temp_installer_script.name

    try:
        # Use PyInstaller to create a self-contained executable installer
        subprocess.run([
            'pyinstaller', '--onefile', '--windowed', '--noconfirm',
            '--name', 'Hammer5ToolsInstaller',
            '--icon', 'src/appicon.ico',
            '--add-data', 'src/appicon.ico;.',
            '--hidden-import', 'win32com',
            '--hidden-import', 'win32com.shell',
            '--hidden-import', 'pythoncom',
            '--distpath', os.path.dirname(output_exe),  # Output in the same folder as hammer5tools.zip
            temp_installer_path
        ], check=True)

        print(f"Created installer: {output_exe}")
    finally:
        # Clean up temporary files
        if os.path.exists(temp_installer_path):
            os.remove(temp_installer_path)
        if os.path.exists(archive_name):
            os.remove(archive_name)
        # Remove build and spec files generated by PyInstaller
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

    # Kill the process
    stage_start_time = time.time()
    kill_process("Hammer5Tools.exe")
    print_elapsed_time("Kill process", stage_start_time)

    # Build components based on arguments
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

    # Determine output paths
    output_folder = 'hammer5tools'
    zip_output_path = os.path.join(output_folder, 'hammer5tools.zip')
    installer_output_path = os.path.join(output_folder, 'Hammer5ToolsInstaller.exe')

    # Archive files if requested
    if args.archive:
        stage_start_time = time.time()
        excluded_files = {'hammer5tools.7z', 'Hammer5ToolsInstaller.exe', 'hammer5tools.zip'}
        excluded_paths = ['SoundEventEditor\\sounds']
        archive_files(output_folder, zip_output_path, excluded_files, excluded_paths)
        print_elapsed_time("Archiving files", stage_start_time)

    # Create installer if requested
    if args.installer:
        stage_start_time = time.time()
        create_installer(output_folder, installer_output_path)
        print_elapsed_time("Creating installer", stage_start_time)

    print_elapsed_time("Overall process", overall_start_time)

if __name__ == "__main__":
    main()