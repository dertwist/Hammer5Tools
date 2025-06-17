import os
import sys
import subprocess
import threading
from typing import List
from tqdm import tqdm
from threading import Lock

IGNORED_FOLDERS = ["venv", "__pycache__"]


def compile_ui(ui_file: str, out_file: str) -> None:
    try:
        subprocess.run(['pyside6-uic', ui_file, '-o', out_file], check=True)
        print(f"Compiled {ui_file} -> {out_file}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to compile {ui_file}: {e}")
        raise

def compile_with_progress(ui_file: str, out_file: str, progress_bar: tqdm, lock: Lock) -> None:
    try:
        compile_ui(ui_file, out_file)
    finally:
        with lock:
            progress_bar.update(1)

def find_ui_files(directory: str) -> List[str]:
    ui_files = []
    for root, dirs, files in os.walk(directory):
        for ignore_folder in IGNORED_FOLDERS:
            if ignore_folder in dirs:
                dirs.remove(ignore_folder)
        for file_name in files:
            if file_name.endswith('.ui'):
                ui_files.append(os.path.join(root, file_name))
    return ui_files

def compile_qrc(qrc_file: str, out_file: str) -> None:
    """
    Compile a Qt .qrc file to a Python resources_rc.py file using pyside6-rcc.
    """
    try:
        subprocess.run(['pyside6-rcc', qrc_file, '-o', out_file], check=True)
        print(f"Compiled {qrc_file} -> {out_file}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to compile {qrc_file}: {e}")
        raise

def main(directory: str) -> None:
    if not os.path.isdir(directory):
        print(f"'{directory}' does not exist.")
        sys.exit(1)

    ui_files = find_ui_files(directory)
    if not ui_files:
        print("No .ui files found.")
        return

    lock = Lock()
    progress_bar = tqdm(total=len(ui_files), desc="Compiling UI files")
    threads = []

    for ui_path in ui_files:
        base_name = os.path.basename(ui_path)
        name_no_ext = os.path.splitext(base_name)[0]
        out_file = os.path.join(os.path.dirname(ui_path), f"ui_{name_no_ext}.py")

        thread = threading.Thread(
            target=compile_with_progress,
            args=(ui_path, out_file, progress_bar, lock),
            daemon=True
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    progress_bar.close()
    print("All .ui files compiled successfully.")

    # Compile resources.qrc if present in the directory
    directory_root = os.path.join(directory)
    directory = os.path.join(directory_root, 'src')

    qrc_path = os.path.join(directory, "resources.qrc")
    if os.path.isfile(qrc_path):
        out_rc = os.path.join(directory, 'resources_rc',"__init__.py")
        compile_qrc(qrc_path, out_rc)

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    main(target_dir)