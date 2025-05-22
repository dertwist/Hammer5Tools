import os
import json
from typing import Optional, Dict, List, Tuple, Set
from PySide6.QtCore import Signal, QThread
from src.settings.main import get_addon_name, get_cs2_path, get_addon_dir, debug
from src.editors.assetgroup_maker.objects import get_default_file


class StartProcess(QThread):
    """Thread to handle the start of a processing task."""

    finished = Signal()

    def __init__(self, filepath: str, parent=None):
        """
        Initialize the StartProcess thread.

        :param filepath: Path to the file to be processed.
        :param parent: Optional parent for the thread.
        """
        super().__init__(parent)
        self.filepath = filepath
        self.stop_thread = False

    def update_reference_content(self, reference: str) -> str:
        """
        Update the content from a reference file.

        :param reference: Reference file path.
        :return: Content of the reference file or an empty string if not found.
        """
        reference_path = os.path.join(get_addon_dir(), reference)
        try:
            with open(reference_path, 'r') as file:
                data = file.read()
            return data
        except FileNotFoundError:
            debug(f"Reference file not found: {reference_path}")
            return ""
        except Exception as e:
            debug(f"Error reading reference file {reference_path}: {e}")
            return ""

    def load_file(self, filepath: str) -> Tuple[Dict, Dict, str]:
        """
        Load a JSON file and extract process, replacements, and content.

        :param filepath: Path to the JSON file.
        :return: Tuple containing process, replacements, and content.
        """
        try:
            with open(filepath, 'r') as file:
                data = json.load(file)
            process = data.get('process', {})
            replacements = data.get('replacements', {})
            content = data.get('file', {}).get('content', '')
            return process, replacements, content
        except FileNotFoundError:
            debug(f"File to load not found: {filepath}")
            return {}, {}, ""
        except json.JSONDecodeError as e:
            debug(f"JSON decode error in file {filepath}: {e}")
            return {}, {}, ""
        except Exception as e:
            debug(f"Error loading file {filepath}: {e}")
            return {}, {}, ""

    def run(self):
        """Execute the processing task."""
        try:
            if self.stop_thread:
                return

            process, replacements, content = self.load_file(self.filepath)
            if not process:
                debug("No process configuration found. Aborting.")
                return

            reference = process.get('reference')
            if reference:
                content = self.update_reference_content(reference)

            if self.stop_thread:
                return

            perform_batch_processing(
                file_path=self.filepath,
                process=process,
                preview=False,
                replacements=replacements,
                content_template=content
            )

            self.finished.emit()

        except Exception as e:
            debug(f"Error in StartProcess: {e}")

    def stop(self):
        """Stop the processing thread."""
        self.stop_thread = True
        self.quit()
        self.wait()


def perform_batch_processing(file_path: str, process: Dict, preview: bool, replacements: Dict,
                             content_template: Optional[str] = None) -> List[str]:
    """
    Perform batch processing of files based on the provided process configuration.

    :param file_path: Path to the file being processed.
    :param process: Process configuration dictionary.
    :param preview: Flag to indicate if this is a preview operation.
    :param replacements: Dictionary of replacements to apply.
    :param content_template: Optional content template for file creation.
    :return: List of created file paths.
    """
    base_directory = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name())
    if not os.path.isdir(base_directory):
        debug(f"Base directory does not exist: {base_directory}")
        return []

    batch_directory = os.path.splitext(file_path)[0]
    if not os.path.isdir(batch_directory):
        os.makedirs(batch_directory)

    relative_batch_path = os.path.relpath(batch_directory, base_directory).replace('\\', '/')

    algorithm = int(process.get('algorithm', get_default_file()['process']['algorithm']))
    file_extension = process.get('extension', get_default_file()['process']['extension'])
    ignore_extensions = [ext.strip() for ext in process.get('ignore_extensions', '').split(',')]
    reference = process.get('reference')
    reference = os.path.join(get_addon_dir(), reference) if reference else None

    load_from_the_folder = bool(process.get('load_from_the_folder'))
    output_to_the_folder = bool(process.get('output_to_the_folder'))

    # Gather input files
    if load_from_the_folder:
        files_to_process = search_files(batch_directory, algorithm, ignore_extensions, process)
    else:
        # Use a custom list if not loading from folder
        files_to_process = process.get('custom_files', [])

    created_files = []
    if preview:
        return preview_processing_files(files_to_process, batch_directory, file_extension, process)
    else:
        if output_to_the_folder:
            output_directory = batch_directory
        else:
            custom_output = process.get('custom_output', '')
            output_directory = os.path.join(get_addon_dir(), custom_output)

        if not os.path.isdir(output_directory):
            try:
                os.makedirs(output_directory, exist_ok=True)
                debug(f"Created output directory: {output_directory}")
            except Exception as e:
                debug(f"Failed to create output directory {output_directory}: {e}")
                return created_files

        execute_file_creation(
            files=files_to_process,
            output_path=output_directory,
            relative_path=relative_batch_path,
            extension=file_extension,
            created_files=created_files,
            replacements=replacements,
            reference=reference,
            content_template=content_template,
            load_from_the_folder=load_from_the_folder,
            base_directory=base_directory
        )
        return created_files


def execute_file_creation(files: List[str], output_path: str, relative_path: str, extension: str,
                          created_files: List[str], replacements: Dict, reference: Optional[str],
                          content_template: Optional[str], load_from_the_folder: bool,
                          base_directory: Optional[str] = None):
    """
    Execute the creation of files based on the provided parameters.

    :param files: List of files to process.
    :param output_path: Path to the output directory.
    :param relative_path: Relative path for file creation.
    :param extension: File extension for created files.
    :param created_files: List to store paths of created files.
    :param replacements: Dictionary of replacements to apply.
    :param reference: Optional reference file path.
    :param content_template: Content template for file creation.
    :param load_from_the_folder: Flag to indicate if files should be loaded from the folder.
    :param base_directory: Optional base directory for relative path calculation.
    """
    if content_template is None:
        debug("Content template is missing. Skipping file creation.")
        return

    for file_name in files:
        data_replacements = content_template
        if replacements:
            for key, replacement in replacements.items():
                old, new = replacement.get('replacement', ['', ''])
                if old:
                    data_replacements = data_replacements.replace(old, new)

        if load_from_the_folder:
            # For folder-based processing, #$ASSET_NAME$# is the actual file name,
            # while #$FOLDER_PATH$# is the relative path to the base directory.
            data = data_replacements.replace("#$FOLDER_PATH$#", relative_path)
            data = data.replace("#$ASSET_NAME$#", file_name)
            output_file_path = os.path.join(output_path, f"{file_name}.{extension}")
        else:
            # For custom file lists, figure out any subfolder from the original path
            original_dir = os.path.dirname(file_name)
            base_name = os.path.splitext(os.path.basename(file_name))[0]

            dynamic_relative_path = os.path.relpath(original_dir, base_directory).replace('\\', '/')
            data = data_replacements.replace("#$FOLDER_PATH$#", dynamic_relative_path)
            data = data.replace("#$ASSET_NAME$#", base_name)
            output_file_path = os.path.join(output_path, f"{base_name}.{extension}")

        output_path_resolved = os.path.abspath(output_file_path)
        reference_path_resolved = os.path.abspath(reference) if reference else None

        # Adjust the path check to be case-insensitive on Windows
        if reference_path_resolved:
            if os.name == 'nt':  # Windows
                if output_path_resolved.lower() == reference_path_resolved.lower():
                    debug(f"Skipped writing to the reference file to prevent infinite loop: {output_file_path}")
                    continue
            else:
                # On non-Windows, paths are case-sensitive, so comparing them directly is sufficient
                if output_path_resolved == reference_path_resolved:
                    debug(f"Skipped writing to the reference file to prevent infinite loop: {output_file_path}")
                    continue

        try:
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            with open(output_file_path, 'w') as output_file:
                output_file.write(data)
            debug(f"File created: {output_file_path}")
            created_files.append(output_file_path)
        except PermissionError as e:
            debug(f"Permission denied: {output_file_path}\n{e}")
        except Exception as e:
            debug(f"Failed to create file {output_file_path}\n{e}")


def get_basename_without_extension(file_path: str) -> str:
    """
    Get the base name of a file without its extension.

    :param file_path: Path to the file.
    :return: Base name without extension.
    """
    return os.path.splitext(os.path.basename(file_path))[0]


def preview_processing_files(files: List[str], base_directory: str, extension: str,
                             process: Dict) -> Tuple[List[str], Optional[List[str]], str, str]:
    """
    Preview the processing of files without actual creation.

    :param files: List of files to process.
    :param base_directory: Base directory for file processing.
    :param extension: File extension for created files.
    :param process: Process configuration dictionary.
    :return: Tuple containing base names, optional file list, extension, and base directory.
    """
    if process.get('load_from_the_folder'):
        files_list_out = []
        for root, _, files_in_dir in os.walk(base_directory):
            for file in files_in_dir:
                if (
                    file not in process.get('ignore_list', [])
                    and not any(file.endswith(ext) for ext in process.get('ignore_extensions', '').split(','))
                ):
                    files_list_out.append(file)
        return files, files_list_out, extension, base_directory
    else:
        return [get_basename_without_extension(f) for f in files], None, extension, base_directory


def extract_base_names(names: List[str]) -> Set[str]:
    """
    Extract base names from a list of file names.

    :param names: List of file names.
    :return: Set of base names.
    """
    return set(os.path.basename(name) for name in names)


def extract_base_names_underscore(names: List[str]) -> Set[str]:
    """
    Extract base names from a list of file names, removing underscores.

    :param nwames: List of file names.
    :return: Set of base names with underscores removed.
    """
    return set(name.rsplit('_', 1)[0] if '_' in name else name for name in names)


def search_files(directory: str, algorithm: int, ignore_extensions: List[str], process: Dict) -> Set[str]:
    """
    Search for files in a directory based on the provided algorithm and ignore list.

    :param directory: Directory to search for files.
    :param algorithm: Algorithm to use for file searching.
    :param ignore_extensions: List of extensions to ignore.
    :param process: Process configuration dictionary.
    :return: Set of found file base names.
    """
    ignore_list = [item.strip() for item in process.get('ignore_list', '').split(',')]
    files_found = []
    for root, _, files_in_dir in os.walk(directory):
        for file in files_in_dir:
            if file not in ignore_list and not any(file.endswith(ext) for ext in ignore_extensions):
                base_name, _ = os.path.splitext(file)
                files_found.append(base_name)

    if algorithm == 0:
        return extract_base_names(files_found)
    elif algorithm == 1:
        return extract_base_names_underscore(files_found)
    else:
        debug(f"Unknown algorithm: {algorithm}")
        return set()