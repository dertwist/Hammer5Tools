import os
import json
from typing import Optional, Dict, Set, Tuple
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QMenu, QListWidget, QListWidgetItem
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Signal, QSize, QFileSystemWatcher
from src.settings.main import get_addon_dir, debug
from src.styles.common import qt_stylesheet_button, qt_stylesheet_widgetlist
from src.assetgroup_maker.process import StartProcess
from src.settings.common import get_config_value


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
                return os.path.join(get_addon_dir(), reference)
    except Exception as e:
        debug(f"Error reading {config_path}: {e}")
    return None


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

        relative_path = os.path.relpath(self.file_path, get_addon_dir())
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
    """
    open_file = Signal(str)

    def __init__(self, root_path: str):
        super().__init__()
        self.root_path = root_path
        self.file_system_watcher = QFileSystemWatcher()
        self.file_widgets: Dict[str, Tuple[QListWidgetItem, FileItemWidget]] = {}
        self.config_references: Dict[str, str] = {}
        self.reference_configs: Dict[str, Set[str]] = {}
        self.process_threads: Dict[str, StartProcess] = {}
        self.watched_directories: Set[str] = set()

        self.initialize_watcher()
        self.setStyleSheet(qt_stylesheet_widgetlist)

    def initialize_watcher(self):
        """
        Initialize the file system watcher for the root path.
        """
        if not self.root_path or not os.path.isdir(self.root_path):
            debug("Invalid root path provided to MonitoringFileWatcher.")
            return

        # Add all directories under the root_path
        for dirpath, _, _ in os.walk(self.root_path):
            self.add_directory_watch(dirpath)

        self.update_file_list()
        self.file_system_watcher.directoryChanged.connect(self.on_directory_changed)
        self.file_system_watcher.fileChanged.connect(self.on_file_changed)

    def add_directory_watch(self, directory: str):
        """
        Add a directory to the file system watcher.
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
        Verify that the file is in one of the allowed monitoring folders, matching exactly.
        Allowed folders come from 'monitor_folders' (comma-separated) under AssetGroupMaker,
        in the format 'folder' or 'addon_name/folder'. The top-level folder must match exactly.
        """
        allowed_folders_str = get_config_value('AssetGroupMaker', 'monitor_folders') or "models, materials, smartprops"
        allowed_folders = [fld.strip() for fld in allowed_folders_str.split(',') if fld.strip()]

        print(allowed_folders)

        # If no allowed folders are set, permit all files
        if not allowed_folders:
            return True

        # Convert to absolute for comparison
        addon_dir = os.path.abspath(get_addon_dir())
        file_path_abs = os.path.abspath(file_path)
        print(file_path_abs)
        # If the file isn't under the addon's directory, disallow
        if not os.path.commonpath([file_path_abs, addon_dir]) == addon_dir:
            return False

        # Convert path to relative from addon's dir
        relative_path = os.path.relpath(file_path_abs, addon_dir)
        segments = relative_path.split(os.sep)
        if not segments:
            return False

        # Top folder is the first path segment
        top_folder = segments[0]

        # We require an exact match of top_folder in the allowed_folders list
        return top_folder in allowed_folders

    def collect_hbat_files(self) -> list:
        """
        Collect all .hbat files under the root path that are in allowed folders.
        """
        collected_files = []
        for dirpath, _, filenames in os.walk(self.root_path):
            for filename in filenames:
                if filename.lower().endswith('.hbat'):
                    full_path = os.path.join(dirpath, filename)
                    if self.is_file_in_allowed_folder(full_path):
                        collected_files.append(full_path)
        debug(f"Collected {len(collected_files)} .hbat files after filtering allowed folders.")
        return collected_files

    def update_file_list(self):
        """
        Update the list of file widgets based on current .hbat files in allowed folders.
        """
        current_files = set(self.file_widgets.keys())
        found_files = set(self.collect_hbat_files())

        # Calculate new and removed
        new_files = found_files - current_files
        removed_files = current_files - found_files

        # Add new
        for path in new_files:
            self.add_file_widget(path)

        # Remove old
        for path in removed_files:
            self.remove_file_widget(path)

        # Update references for existing
        for path in (found_files & current_files):
            self.update_reference(path)

        # Add watchers for directories containing these files
        for path in found_files:
            directory = os.path.dirname(path)
            self.add_directory_watch(directory)

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

        # Track references and watch file
        self.update_reference(path)
        self.file_system_watcher.addPath(path)

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
        Update the reference path for a .hbat file, if it has one.
        """
        reference_path = read_reference_from_file(config_path)
        if reference_path:
            self.track_reference(config_path, reference_path)
        else:
            self.untrack_reference(config_path)

    def track_reference(self, config_path: str, reference_path: str):
        """
        Track a reference path for a configuration file, watch it too.
        """
        old_reference = self.config_references.get(config_path)
        if old_reference and old_reference != reference_path:
            self.untrack_reference(config_path)

        self.config_references[config_path] = reference_path
        if reference_path not in self.reference_configs:
            self.reference_configs[reference_path] = set()
            self.file_system_watcher.addPath(reference_path)
        self.reference_configs[reference_path].add(config_path)

    def untrack_reference(self, config_path: str):
        """
        Untrack a reference path for a config file if present.
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
        Handle directory change events.
        """
        self.update_file_list()

        # Watch any new subdirectories
        for dirpath, dirnames, _ in os.walk(self.root_path):
            for dirname in dirnames:
                full_dir_path = os.path.join(dirpath, dirname)
                self.add_directory_watch(full_dir_path)

    def on_file_changed(self, path: str):
        """
        Handle file change events (modified, renamed, or removed).
        """
        debug(f"File changed: {path}")
        if os.path.exists(path):
            # If it still exists, update references and re-run processes
            if path in self.file_widgets:
                self.update_reference(path)
                _, widget = self.file_widgets[path]
                self.stop_processing(path)
                self.start_processing(path)
            elif path in self.reference_configs:
                # If it's a referenced file, re-process all configs that depend on it
                configs = self.reference_configs[path]
                for config_path in configs:
                    self.stop_processing(config_path)
                    self.start_processing(config_path)
        else:
            # If it's gone, remove from watchers
            if path in self.file_widgets:
                self.remove_file_widget(path)
            elif path in self.reference_configs:
                configs = self.reference_configs.pop(path, None)
                for config_path in configs or []:
                    self.config_references.pop(config_path, None)
                    self.stop_processing(config_path)
                if path in self.file_system_watcher.files():
                    self.file_system_watcher.removePath(path)
                    debug(f"Removed non-existent reference: {path}")

    def start_processing(self, config_path: str):
        """
        Start processing a config file with StartProcess.
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
        Once processing completes, clean up references to the thread.
        """
        self.process_threads.pop(config_path, None)
        debug(f"Finished processing: {config_path}")

    def closeEvent(self, event):
        """
        Gracefully close all running threads and disconnect signals.
        """
        debug("Closing MonitoringFileWatcher.")
        self.file_system_watcher.directoryChanged.disconnect(self.on_directory_changed)
        self.file_system_watcher.fileChanged.disconnect(self.on_file_changed)
        for thread in list(self.process_threads.values()):
            if thread.isRunning():
                thread.stop()
                thread.wait()
        event.accept()


if __name__ == "__main__":
    # For testing purposes, create an instance if needed.
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    root = os.getcwd()  # Replace with an appropriate root path if desired
    watcher = MonitoringFileWatcher(root)
    watcher.show()
    sys.exit(app.exec())