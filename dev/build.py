import zipfile
import os
import subprocess
import time
import argparse

def print_elapsed_time(stage_name, start_time):
    elapsed_time = time.time() - start_time
    print(f"{stage_name} took {elapsed_time:.2f} seconds")

def kill_process(process_name):
    subprocess.run(["taskkill", "/IM", process_name])

def build_hammer5_tools():
    subprocess.run([
        'pyinstaller', '--name=Hammer5Tools', '--noconfirm', '--onefile', '--windowed',
        '--optimize=2', '--icon=src/appicon.ico', '--add-data=src/appicon.ico:.',
        '--add-data=src/images;images/', '--add-data=src/qt_styles;qt_styles/',
        '--noupx', '--distpath=hammer5tools', '--exclude-module=PyQt5', 'src/main.py'
    ])

def build_updater():
    subprocess.run([
        'pyinstaller', '--name=Hammer5Tools_Updater', '--noconfirm', '--onefile',
        '--optimize=2', '--icon=src/appicon.ico', '--noupx', '--distpath=hammer5tools',
        '--exclude-module=PySide6', '--exclude-module=PyQt5', '--exclude-module=numpy',
        '--exclude-module=PIL', '--exclude', 'matplotlib', '--exclude', 'pandas', 'src/updater.py'
    ])


# def build_hammer5_tools():
#     subprocess.run([
#         'python', '-m', 'nuitka', '--standalone', '--onefile', '--output-dir=hammer5tools',
#         '--remove-output', '--include-data-file=src/appicon.ico=appicon.ico',
#         '--include-data-dir=src/images=images', '--include-data-dir=src/qt_styles=qt_styles',
#         '--disable-console', '--nofollow-import-to=PyQt5', 'src/main.py'
#     ])
#
# def build_updater():
#     subprocess.run([
#         'python', '-m', 'nuitka', '--standalone', '--onefile', '--output-dir=hammer5tools',
#         '--remove-output', '--include-data-file=src/appicon.ico=appicon.ico',
#         '--nofollow-import-to=PySide6', '--nofollow-import-to=PyQt5',
#         '--nofollow-import-to=numpy', '--nofollow-import-to=PIL',
#         '--nofollow-import-to=matplotlib', '--nofollow-import-to=pandas',
#         'src/updater.py'
#     ])

def archive_files(folder_path, output_path):
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

def main():
    parser = argparse.ArgumentParser(description="Build and archive Hammer 5 Tools and Updater.")
    parser.add_argument('--build-all', action='store_true', help="Build both Hammer 5 Tools and Updater.")
    parser.add_argument('--build-hammer5', action='store_true', help="Build only Hammer 5 Tools.")
    parser.add_argument('--build-updater', action='store_true', help="Build only Updater.")
    parser.add_argument('--archive', action='store_true', help="Archive the build outputs.")
    args = parser.parse_args()

    overall_start_time = time.time()

    # Kill the process
    stage_start_time = time.time()
    kill_process("Hammer5Tools.exe")
    print_elapsed_time("Kill process", stage_start_time)

    # Build components based on arguments
    if args.build_all or args.build_hammer5:
        stage_start_time = time.time()
        build_hammer5_tools()
        print_elapsed_time("Hammer 5 Tools Build", stage_start_time)

    if args.build_all or args.build_updater:
        stage_start_time = time.time()
        build_updater()
        print_elapsed_time("Updater Build", stage_start_time)

    # Archive files if requested
    if args.archive:
        stage_start_time = time.time()
        archive_files('hammer5tools', 'hammer5tools/hammer5tools.zip')
        print_elapsed_time("Archiving files", stage_start_time)

    print_elapsed_time("Overall process", overall_start_time)

if __name__ == "__main__":
    main()