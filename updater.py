import os.path
import shutil
from turtle import pu
import psutil
import requests
import zipfile
import io
from tqdm import tqdm

version = 'v1.0.0'
print(f'Updater version: {version}')

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
    shutil.rmtree(path)
    input('Press Enter to close updater...')  # Pause the program and wait for user input

if os.path.exists(path):
    preset_path = os.path.join(path, 'presets')
    for process in psutil.process_iter():
        if process.name() == 'Hammer5Tools.exe':
            process.kill()
            print('Hammer5Tools.exe process killed successfully.')
    presets = []
    success = True  # Flag to track if all operations are successful
    for preset in os.listdir(preset_path):
        path_to_remove = os.path.abspath(os.path.join('presets', preset))
        try:
            shutil.rmtree(path_to_remove)
        except (PermissionError, FileNotFoundError) as e:
            print(f"Error while removing directory: {e}")
            success = False  # Set flag to False if an error occurs
        presets.append(preset)

    try:
        os.remove(os.path.join('Hammer5Tools.exe'))
    except Exception as e:
        print(f"An error occurred: {e}")
        success = False  # Set flag to False if an error occurs

    try:
        shutil.move(os.path.join(path, 'Hammer5Tools.exe'), os.path.join(os.getcwd(), 'Hammer5Tools.exe'))
    except Exception as e:
        print(f"An error occurred: {e}")
        success = False  # Set flag to False if an error occurs

    for preset in presets:
        shutil.move(os.path.join(path, 'presets', preset), os.path.join('presets'))

    if success:
        print("Successful updated")
        os.startfile('Hammer5Tools.exe')

    shutil.rmtree(path)