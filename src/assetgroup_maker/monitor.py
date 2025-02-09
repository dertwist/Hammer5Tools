import os
import json
from pathlib import Path
from collections import defaultdict
from typing import Optional, Dict, Tuple, List

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QMenu, QListWidget, QListWidgetItem, QApplication
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Signal, QSize, QFileSystemWatcher, QTimer

from src.settings.main import get_addon_dir, debug
from src.styles.common import qt_stylesheet_button, qt_stylesheet_widgetlist
from src.assetgroup_maker.process import StartProcess
from src.settings.common import get_settings_value


def read_reference_from_file(config_path: str) -> Optional[str]:
    """
    Read the reference path from a configuration file.
    """
    try:
        with open(config_path, 'r') as file:
            data = json.load(file)
            process = data.get('process', {})
            reference = process.get('reference', '')
            if reference:
                return str(Path(get_addon_dir()) / reference)
    except Exception as e:
        debug(f"Error reading {config_path}: {e}")
    return None


def validate_reference_file(reference_path: str) -> bool:
    """
    Validates the referenced file.
    - Must exist.
    - Must not be binary (checked via presence of null bytes in first 1024 bytes).
    - Must not be empty (after decoding as UTF-8).
    Returns True if valid, else False.
    """
    ref_path = Path(reference_path)
    if not ref_path.exists():
        debug(f"Reference file does not exist: {reference_path}")
        return False
    try:
        with ref_path.open('rb') as f:
            sample = f.read(1024)
            if b'\0' in sample:
                debug(f"Reference file is binary: {reference_path}")
                return False
            content = sample.decode('utf-8', errors='replace')
            if not any(char for char in content if not char.isspace()):
                remaining = f.read()
                if not any(char for char in remaining.decode('utf-8', errors='replace') if not char.isspace()):
                    debug(f"Reference file is empty or contains only whitespace: {reference_path}")
                    return False
        return True
    except Exception as e:
        debug(f"Error validating reference file {reference_path}: {e}")
        return False


class FileItemWidget(QWidget):
    """
    Widget representing a file item with options to open or process the file.
    """
    open_requested = Signal(str)
    process_requested = Signal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.setup_ui()

    def setup_ui(self):
        """
        Set up the user interface for the file item widget.
        """
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        addon_dir = get_addon_dir()
        relative_path = os.path.relpath(self.file_path, addon_dir)
        path_parts = relative_path.split(os.sep)
        text = os.sep.join(path_parts[-2:]) if len(path_parts) >= 2 else relative_path

        self.label = QLabel(text)
        self.setToolTip(self.file_path)

        self.play_button = QPushButton()
        self.open_button = QPushButton()

        self.play_button.setIcon(QIcon(":/valve_common/icons/tools/common/control_play.png"))
        self.open_button.setIcon(QIcon(":/valve_common/icons/tools/common/edit.png"))
        self.play_button.setStyleSheet(qt_stylesheet_button)
        self.open_button.setStyleSheet(qt_stylesheet_button)

        button_size = QSize(24, 24)
        self.play_button.setFixedSize(button_size)
        self.open_button.setFixedSize(button_size)

        layout.addWidget(self.label)
        layout.addWidget(self.play_button)
        layout.addWidget(self.open_button)

        self.setLayout(layout)

        self.play_button.clicked.connect(self.start_process)
        self.open_button.clicked.connect(self.open_file)

    def start_process(self):
        """
        Emit a signal to start processing the file.
        """
        self.process_requested.emit(self.file_path)

    def open_file(self):
        """
        Emit a signal to open the file.
        """
        self.open_requested.emit(self.file_path)

    def contextMenuEvent(self, event):
        """
        Create a context menu for additional actions.
        """
        menu = QMenu(self)
        open_folder_action = QAction("Open Folder", self)
        open_folder_action.triggered.connect(self.open_folder)
        menu.addAction(open_folder_action)
        menu.exec(event.globalPos())

    def open_folder(self):
        """
        Open the folder containing the file.
        """
        folder_path = os.path.dirname(self.file_path)
        os.startfile(folder_path)


class MonitoringFileWatcher(QListWidget):
    """
    Widget to monitor file changes and manage file processing, enforcing an exact folder match.
    It collects all .hbat files under the root path from allowed folders, validates referenced files before processing,
    and uses a 3-second debounce delay for updates.
    """
    open_file = Signal(str)

    def __init__(self, root_path: str):
        super().__init__()
        self.root_path: Path = Path(root_path)
        self.file_system_watcher = QFileSystemWatcher()
        self.file_widgets: Dict[str, Tuple[QListWidgetItem, FileItemWidget]] = {}
        self.config_references: Dict[str, str] = {}
        self.reference_configs: Dict[str, set] = {}
        self.process_threads: Dict[str, StartProcess] = {}
        self.watched_directories: set = set()

        # Debounce timer for update delays (3 seconds)
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.update_file_list)

        self.initialize_watcher()
        self.setStyleSheet(qt_stylesheet_widgetlist)

    def initialize_watcher(self):
        """
        Initialize the file system watcher for the root path using optimized scanning.
        """
        if not self.root_path.exists() or not self.root_path.is_dir():
            debug("Invalid root path provided to MonitoringFileWatcher.")
            return

        # Watch the root directory; additional directories will be added later if necessary.
        self.add_directory_watch(str(self.root_path))
        self.update_file_list()
        self.file_system_watcher.directoryChanged.connect(lambda _: self.debounce_timer.start(3000))
        self.file_system_watcher.fileChanged.connect(self.on_file_changed)

    def add_directory_watch(self, directory: str):
        """
        Add a directory to the file system watcher if not already watched.
        """
        if directory not in self.watched_directories:
            self.file_system_watcher.addPath(directory)
            self.watched_directories.add(directory)

    def remove_directory_watch(self, directory: str):
        """
        Remove a directory from the file system watcher.
        """
        if directory in self.watched_directories:
            self.file_system_watcher.removePath(directory)
            self.watched_directories.remove(directory)

    def is_file_in_allowed_folder(self, file_path: str) -> bool:
        """
        Check if the file is in one of the allowed folders.
        Allowed folders are retrieved from configuration 'AssetGroupMaker/monitor_folders'.
        Only files whose relative path (from the add-on directory) contains one of the allowed folder names are accepted.
        """
        allowed = get_settings_value('AssetGroupMaker', 'monitor_folders') or "models, materials, smartprops"
        allowed_set = {x.strip().lower() for x in allowed.split(',')}
        try:
            relative_path = os.path.relpath(file_path, get_addon_dir())
        except Exception as e:
            debug(f"Error obtaining relative path for {file_path}: {e}")
            return False
        path_parts = relative_path.split(os.sep)
        for folder in path_parts:
            if folder.lower() in allowed_set:
                return True
        return False

    def collect_hbat_files(self) -> List[str]:
        """
        Collect all .hbat files under the root path from allowed folders.
        Uses os.scandir for a faster directory traversal.
        """
        collected_files = []

        def scan_dir(path: Path):
            try:
                with os.scandir(path) as it:
                    for entry in it:
                        entry_path = Path(entry.path)
                        if entry.is_dir(follow_symlinks=False):
                            scan_dir(entry_path)
                        elif entry.is_file() and entry.name.lower().endswith('.hbat') and self.is_file_in_allowed_folder(str(entry_path)):
                            collected_files.append(str(entry_path))
            except OSError as e:
                debug(f"Error scanning directory {path}: {e}")

        scan_dir(self.root_path)
        debug(f"Collected {len(collected_files)} .hbat files in allowed folders.")
        return collected_files

    def update_file_list(self):
        """
        Update the list of file widgets based on current .hbat files in allowed folders of the project.
        """
        current_files = set(self.file_widgets.keys())
        found_files = set(self.collect_hbat_files())

        new_files = found_files - current_files
        removed_files = current_files - found_files

        for path in new_files:
            self.add_file_widget(path)
        for path in removed_files:
            self.remove_file_widget(path)
        for path in found_files & current_files:
            self.update_reference(path)

        # Add new directories from found files if not already watched.
        for file_path in found_files:
            directory = os.path.dirname(file_path)
            self.add_directory_watch(directory)

    def track_new_file(self, file_path: str) -> bool:
        """
        Public method to allow external modules (like the assetgroup maker main file or src.explorer)
        to add a new file to tracking immediately.
        Returns True if the file was added, False otherwise.
        """
        file_path = str(Path(file_path))
        if not file_path.lower().endswith('.hbat'):
            return False

        if not self.is_file_in_allowed_folder(file_path):
            return False

        if file_path not in self.file_widgets:
            self.add_file_widget(file_path)
            return True
        return False

    def add_file_widget(self, path: str):
        """
        Add a file widget for a new .hbat file.
        """
        item = QListWidgetItem(self)
        widget = FileItemWidget(path)
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)
        self.file_widgets[path] = (item, widget)

        widget.open_requested.connect(self.open_file.emit)
        widget.process_requested.connect(self.start_processing)

        # Watch the file for changes if not already watched.
        if path not in self.file_system_watcher.files():
            self.file_system_watcher.addPath(path)
        # Initial reference update.
        self.update_reference(path)

    def remove_file_widget(self, path: str):
        """
        Remove a file widget for a deleted or disallowed .hbat.
        """
        self.stop_processing(path)
        if path in self.file_system_watcher.files():
            self.file_system_watcher.removePath(path)
        item, _ = self.file_widgets.pop(path, (None, None))
        if item:
            self.takeItem(self.row(item))
        self.untrack_reference(path)

    def update_reference(self, config_path: str):
        """
        Update the reference path for a .hbat file. Validate the referenced file
        and track it if valid.
        """
        reference_path = read_reference_from_file(config_path)
        if reference_path and validate_reference_file(reference_path):
            self.track_reference(config_path, reference_path)
        else:
            self.untrack_reference(config_path)

    def track_reference(self, config_path: str, reference_path: str):
        """
        Track a reference path for a configuration file and watch it.
        """
        old_ref = self.config_references.get(config_path)
        if old_ref and old_ref != reference_path:
            self.untrack_reference(config_path)
        self.config_references[config_path] = reference_path
        if reference_path not in self.reference_configs:
            self.reference_configs[reference_path] = set()
            if reference_path not in self.file_system_watcher.files():
                self.file_system_watcher.addPath(reference_path)
        self.reference_configs[reference_path].add(config_path)

    def untrack_reference(self, config_path: str):
        """
        Untrack a reference path for a configuration file.
        """
        reference_path = self.config_references.pop(config_path, None)
        if reference_path:
            configs = self.reference_configs.get(reference_path)
            if configs:
                configs.discard(config_path)
                if not configs:
                    self.reference_configs.pop(reference_path, None)
                    if reference_path in self.file_system_watcher.files():
                        self.file_system_watcher.removePath(reference_path)

    def on_directory_changed(self, path: str):
        """
        Handle directory change events using debouncing to minimize rescans.
        """
        self.debounce_timer.start(3000)

    def on_file_changed(self, path: str):
        """
        Handle file change events.
        For .hbat files or reference files, trigger appropriate updates.
        """
        debug(f"File changed: {path}")
        if os.path.exists(path):
            if path in self.file_widgets:
                self.update_reference(path)
                _, widget = self.file_widgets[path]
                self.stop_processing(path)
                self.start_processing(path)
            elif path in self.reference_configs:
                configs = self.reference_configs[path]
                for config_path in configs:
                    self.stop_processing(config_path)
                    self.start_processing(config_path)
        else:
            if path in self.file_widgets:
                self.remove_file_widget(path)
            elif path in self.reference_configs:
                configs = self.reference_configs.pop(path, set())
                for config_path in configs:
                    self.config_references.pop(config_path, None)
                    self.stop_processing(config_path)
                if path in self.file_system_watcher.files():
                    self.file_system_watcher.removePath(path)
                    debug(f"Removed non-existent reference: {path}")

    def start_processing(self, config_path: str):
        """
        Start processing a config file using StartProcess.
        Avoid duplicate processing threads.
        """
        if config_path in self.process_threads:
            debug(f"Processing already started for: {config_path}")
            return
        process_thread = StartProcess(config_path)
        process_thread.finished.connect(lambda: self.on_process_finished(config_path))
        process_thread.start()
        self.process_threads[config_path] = process_thread

    def stop_processing(self, config_path: str):
        """
        Stop processing if the thread is running.
        """
        if config_path in self.process_threads:
            thread = self.process_threads.pop(config_path)
            if thread.isRunning():
                thread.stop()
                thread.wait()

    def on_process_finished(self, config_path: str):
        """
        Clean up a finished processing thread.
        """
        self.process_threads.pop(config_path, None)
        debug(f"Finished processing: {config_path}")

    def closeEvent(self, event):
        """
        Gracefully close all running threads and disconnect signals.
        """
        debug("Closing MonitoringFileWatcher.")
        try:
            self.debounce_timer.stop()
            self.file_system_watcher.directoryChanged.disconnect()
            self.file_system_watcher.fileChanged.disconnect()
        except Exception as e:
            debug(f"Error disconnecting signals: {e}")
        for thread in list(self.process_threads.values()):
            if thread.isRunning():
                thread.stop()
                thread.wait()
        event.accept()


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    root = os.getcwd()
    watcher = MonitoringFileWatcher(root)
    watcher.show()
    sys.exit(app.exec())