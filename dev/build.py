import time
import os
import zipfile
import subprocess
import argparse
from typing import List, Set
from tabulate import tabulate

def print_elapsed_time(stage_name: str, start_time: float) -> None:
    """Prints the elapsed time for a given stage.

    Args:
        stage_name (str): The name of the stage.
        start_time (float): The start time of the stage.
    """
    elapsed_time = time.time() - start_time
    print(f"{stage_name} took {elapsed_time:.2f} seconds")

def kill_process(process_name: str) -> None:
    """Kills a process by its name.

    Args:
        process_name (str): The name of the process to kill.
    """
    subprocess.run(
        ["taskkill", "/F", "/IM", process_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def build_hammer5_tools() -> None:
    """Builds the Hammer 5 Tools application using PyInstaller."""
    subprocess.run([
        'pyinstaller',
        '--name=Hammer5Tools',
        '--noupx',
        '--distpath=hammer5tools',
        '--noconfirm',
        '--onefile',
        '--windowed',
        '--strip',
        '--optimize=2',
        '--icon=src/appicon.ico',
        '--add-data=src/appicon.ico;.',
        '--add-data=src/images;images/',
        '--add-data=src/styles;styles/',
        '--exclude-module=PyQt5',
        '--exclude-module=numba',
        '--exclude-module=scipy',
        '--exclude-module=pandas',
        '--exclude-module=tabulate',
        '--exclude-module=matplotlib',
        'src/main.py'
    ], check=True)

def archive_files(folder_path: str, output_path: str, excluded_files: Set[str], excluded_paths: List[str]) -> None:
    """Archives files from a folder into a zip file with maximum compression, excluding specified files and paths.

    Args:
        folder_path (str): The path to the folder to archive.
        output_path (str): The path where the zip file will be saved.
        excluded_files (Set[str]): A set of file names to exclude from the archive.
        excluded_paths (List[str]): A list of paths to exclude from the archive.
    """
    def should_exclude(file_name: str, file_path: str) -> bool:
        if file_name in excluded_files:
            return True
        for excluded_path in excluded_paths:
            if excluded_path in os.path.normpath(file_path):
                return True
        return False

    with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, folder_path)
                if should_exclude(file, rel_path):
                    continue
                try:
                    archive.write(file_path, rel_path)
                except OSError as e:
                    print(f"Warning: Could not add file {file_path}: {e}")

    original_size = sum(os.path.getsize(os.path.join(root, file))
                       for root, _, files in os.walk(folder_path)
                       for file in files
                       if not should_exclude(file, os.path.join(root, file)))
    compressed_size = os.path.getsize(output_path)
    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

    print(f"Archived files to {output_path}")
    print(f"Original size: {original_size / 1024 / 1024:.2f} MB")
    print(f"Compressed size: {compressed_size / 1024 / 1024:.2f} MB")
    print(f"Compression ratio: {compression_ratio:.1f}%")

def main() -> None:
    """Main function to parse arguments and execute build and packaging tasks."""
    parser = argparse.ArgumentParser(description="Build and archive Hammer 5 Tools.")
    parser.add_argument('--build-all', action='store_true', help="Build Hammer 5 Tools.")
    parser.add_argument('--build-app', action='store_true', help="Build only Hammer 5 Tools.")
    parser.add_argument('--archive', action='store_true', help="Archive the build outputs.")
    args = parser.parse_args()

    overall_start_time = time.time()

    stage_start_time = time.time()
    kill_process("Hammer5Tools.exe")
    print_elapsed_time("Kill process", stage_start_time)

    results = []

    try:
        if args.build_all or args.build_app:
            stage_start_time = time.time()
            build_hammer5_tools()
            elapsed_time = time.time() - stage_start_time
            results.append(["Hammer 5 Tools Build", f"{elapsed_time:.2f} seconds"])
    except subprocess.CalledProcessError as e:
        print(f"Error during build: {e}")
        return

    output_folder = 'hammer5tools'
    zip_output_path = os.path.join(output_folder, 'hammer5tools.zip')

    if args.archive:
        stage_start_time = time.time()
        excluded_files = {'hammer5tools.7z', 'hammer5tools_setup.exe', 'hammer5tools.zip', 'settings.ini'}
        excluded_paths = ['SoundEventEditor\\sounds']
        archive_files(output_folder, zip_output_path, excluded_files, excluded_paths)
        elapsed_time = time.time() - stage_start_time
        results.append(["Archiving files", f"{elapsed_time:.2f} seconds"])

    overall_elapsed_time = time.time() - overall_start_time
    results.append(["Overall process", f"{overall_elapsed_time:.2f} seconds"])

    print(tabulate(results, headers=["Stage", "Elapsed Time"], tablefmt="grid"))

if __name__ == "__main__":
    main()