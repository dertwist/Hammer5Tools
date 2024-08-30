import os.path
import shutil
from turtle import pu
import psutil
import requests
import zipfile
import io
from tqdm import tqdm
import webbrowser
version = 'v2.0.0'
print(f'Updater version: {version}')


def kill_main_app():
    processes = [process for process in psutil.process_iter() if process.name() == 'Hammer5Tools.exe']

    if processes:
        for process in processes:
            process.kill()
            print('Hammer5Tools.exe process killed successfully.')
    else:
        print('Hammer5Tools.exe process not found.')


kill_main_app()

path = 'DOWNLOAD_TMP'
# path = 'hammer5tools/DOWNLOAD_TMP'
# URL of the GitHub repository
url = 'https://github.com/dertwist/Hammer5Tools/releases/latest/download/Hammer5Tools.zip'

# Send a GET request to the URL
response = requests.get(url, stream=True)  # Set stream=True to enable streaming
if response.status_code == 200:
    # Get the total file size for progress bar
    total_size = int(response.headers.get('content-length', 0))

    # Create a BytesIO object from the response content
    zip_file = io.BytesIO()

    # Use tqdm to display progress
    with tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024) as pbar:
        for data in response.iter_content(chunk_size=1024):
            zip_file.write(data)
            pbar.update(len(data))

    # Unzip the contents
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(path)  # Specify the path where you want to extract the contents
    print('Download successful.')
else:
    print('Failed to download the update')


# Read the version from updater.cfg file
with open('updater.cfg', 'r') as file:
    updater_version = file.read().strip()  # Assuming the version is stored as plain text in the file

# Compare the versions
if updater_version > version:
    print('A newer version of updater is available. Please update your program manually from https://github.com/dertwist/Hammer5Tools/releases/latest.')
    webbrowser.open('https://github.com/dertwist/Hammer5Tools/releases/latest/download/hammer5tools.zip')
    webbrowser.open('https://github.com/dertwist/Hammer5Tools/releases/latest')
    shutil.rmtree(path)
    input('Press Enter to close updater...')

if os.path.exists(path):
    success = True
    for process in psutil.process_iter():
        if process.name() == 'Hammer5Tools.exe':
            process.kill()
            print('Hammer5Tools.exe process killed successfully.')

    # collect new files
    folders = [os.path.join(path, 'presets'),os.path.join(path, 'hotkeys'), os.path.join(path, 'smartprop_editor_templates'), os.path.join(path, 'soundevent_editor_presets')]
    new_elements = []
    for path_folder in folders:
        for path_item in os.listdir(path_folder):
            full_path_item = os.path.join(path_folder, path_item)
            new_elements.append(full_path_item)
    # process
    path_program = os.getcwd()
    for item in new_elements:
        print(path_program)
        rem_path = os.path.join(path_program, (os.path.relpath(item, path)))
        if os.path.isdir(rem_path):
            shutil.rmtree(rem_path)
        else:
            os.remove(rem_path)
        print(f'\033[91mRemoved: {rem_path}\033[0m')
        shutil.move(item, rem_path)
        print(f'\033[92mMoved: {item} to {rem_path}\033[0m')
    # app
    try:
        os.remove(os.path.join('Hammer5Tools.exe'))
        print('\033[92mHammer5Tools.exe Removed\033[0m')
    except Exception as e:
        print(f"An error occurred: {e}")
        success = False  # Set flag to False if an error occurs

    try:
        shutil.move(os.path.join(path, 'Hammer5Tools.exe'), os.path.join(os.getcwd(), 'Hammer5Tools.exe'))
        print('\033[92mHammer5Tools.exe Moved\033[0m')
    except Exception as e:
        print(f"An error occurred: {e}")
        success = False  # Set flag to False if an error occurs

    if success:
        print("\033[92mSuccessful updated\033[0m")
        os.startfile('Hammer5Tools.exe')
    else:
        print("\033[91mUpdate was unsuccessful, try to update manually\033[0m")
        input('Press Enter to close updater...')

    shutil.rmtree(path)