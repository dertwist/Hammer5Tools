import os
import subprocess
import threading
from typing import List

def compile_ui(file: str, output_file: str) -> None:
    """
    Compiles a .ui file into a Python file using PySide6.

    Args:
        file (str): The path to the .ui file.
        output_file (str): The path where the compiled Python file will be saved.
    """
    subprocess.run(['pyside6-uic', file, '-o', output_file], check=True)
    print(f"Compiled {file} to {output_file}")

def compile_with_progress(file: str, output_file: str) -> None:
    """
    Compiles a .ui file with progress reporting.

    Args:
        file (str): The path to the .ui file.
        output_file (str): The path where the compiled Python file will be saved.
    """
    print(f'Compiling {file}...')
    compile_ui(file, output_file)
    print(f'{file} compiled successfully.')

def find_ui_files(directory: str) -> List[str]:
    """
    Searches for .ui files in the given directory and its subdirectories.

    Args:
        directory (str): The root directory to search for .ui files.

    Returns:
        List[str]: A list of paths to .ui files.
    """
    ui_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.ui') and file != 'ui_input.ui':
                ui_files.append(os.path.join(root, file))
    return ui_files

def main() -> None:
    """
    Main function to compile all .ui files found in the project directory.
    """
    ui_files = find_ui_files('../')
    threads = []

    for file in ui_files:
        filename = os.path.basename(file)
        filename = os.path.splitext(filename)[0]
        output_file = os.path.join(os.path.dirname(file), f'ui_{filename}.py')

        thread = threading.Thread(target=compile_with_progress, args=(file, output_file))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    subprocess.run(['pyside6-rcc', './src/resources.qrc', '-o', './src/resources_rc.py'], check=True)

if __name__ == "__main__":
    main()