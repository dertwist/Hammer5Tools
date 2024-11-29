import os
import shutil
import psutil
import requests
import zipfile
import io
from tqdm import tqdm
import webbrowser
import tkinter as tk
from tkinter import messagebox

version = 'v3.0.0'
print(f'Updater version: {version}')

def kill_main_app():
    processes = [process for process in psutil.process_iter() if process.name() == 'Hammer5Tools.exe']
    if processes:
        for process in processes:
            process.kill()
            print('Hammer5Tools.exe process killed successfully.')
    else:
        print('Hammer5Tools.exe process not found.')

def download_and_extract(url, path):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        total_size = int(response.headers.get('content-length', 0))
        zip_file = io.BytesIO()

        with tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024, desc="Downloading") as pbar:
            for data in response.iter_content(chunk_size=1024):
                zip_file.write(data)
                pbar.update(len(data))

        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(path)
        print('Download successful.')
    else:
        print('Failed to download the update')
        return False
    return True

def update_files(path, path_program):
    success = True
    folders = [os.path.join(path, 'presets'), os.path.join(path, 'hotkeys'), os.path.join(path, 'SoundEventEditor')]
    new_elements = []

    for path_folder in folders:
        try:
            for path_item in os.listdir(path_folder):
                full_path_item = os.path.join(path_folder, path_item)
                new_elements.append(full_path_item)
        except FileNotFoundError:
            pass

    for item in new_elements:
        rem_path = os.path.join(path_program, os.path.relpath(item, path))
        try:
            if os.path.isdir(rem_path):
                shutil.rmtree(rem_path)
            else:
                os.remove(rem_path)
            print(f'Removed: {rem_path}')
            shutil.move(item, rem_path)
            print(f'Moved: {item} to {rem_path}')
        except Exception as e:
            print(f'Error with removing: {rem_path}, {e}')
            success = False

    try:
        os.remove(os.path.join(path_program, 'Hammer5Tools.exe'))
        print('Hammer5Tools.exe Removed')
    except Exception as e:
        print(f"An error occurred: {e}")
        success = False

    try:
        shutil.move(os.path.join(path, 'Hammer5Tools.exe'), os.path.join(path_program, 'Hammer5Tools.exe'))
        print('Hammer5Tools.exe Moved')
    except Exception as e:
        print(f"An error occurred: {e}")
        success = False

    return success

def main():
    kill_main_app()

    def init_paths (dev=False):
        if dev:
            path = 'hammer5tools/DOWNLOAD_TMP'
            path_program = os.path.normpath("D:/CG/Projects/Other/Hammer5Tools/hammer5tools")
        else:
            path = 'DOWNLOAD_TMP'
            path_program = os.getcwd()
        return path, path_program

    path, path_program = init_paths(True)

    url = 'https://github.com/dertwist/Hammer5Tools/releases/latest/download/Hammer5Tools.zip'

    if not download_and_extract(url, path):
        return

    with open(os.path.join(path, 'updater.cfg'), 'r') as file:
        updater_version = file.read().strip()

    if updater_version > version:
        print('A newer version of updater is available. Please update your program manually.')
        webbrowser.open('https://github.com/dertwist/Hammer5Tools/releases/latest')
        shutil.rmtree(path)
        input('Press Enter to close updater...')
        return

    if os.path.exists(path):
        success = update_files(path, path_program)
        if success:
            print("Successful update")
            os.startfile(os.path.join(path_program, 'Hammer5Tools.exe'))
        else:
            print("Update was unsuccessful, try to update manually")
            input('Press Enter to close updater...')
        shutil.rmtree(path)

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    try:
        main()
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
    finally:
        root.destroy()