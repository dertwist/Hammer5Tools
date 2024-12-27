# src/batch_creator/monitor.py

import os
import json
from PySide6.QtWidgets import (
    QListWidget, QListWidgetItem, QWidget, QLabel, QPushButton, QHBoxLayout, QMenu
)
from PySide6.QtCore import Signal, QSize, QFileSystemWatcher
from PySide6.QtGui import QIcon, QAction
from src.preferences import get_addon_dir
from src.batch_creator.process import StartProcess
import os
from PySide6.QtCore import Signal, QSize
from PySide6.QtGui import QIcon
from src.preferences import get_addon_dir, debug
from src.qt_styles.common import *

def read_reference_from_file(config_path):
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
    open_requested = Signal(str)
    process_requested = Signal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        relative_path = os.path.relpath(self.file_path, get_addon_dir())
        path_parts = relative_path.split(os.sep)
        if len(path_parts) >= 2:
            text = os.sep.join(path_parts[-2:])
        else:
            text = relative_path
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
        self.process_requested.emit(self.file_path)

    def open_file(self):
        self.open_requested.emit(self.file_path)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        open_folder_action = QAction("Open Folder", self)
        open_folder_action.triggered.connect(self.open_folder)
        menu.addAction(open_folder_action)
        menu.exec(event.globalPos())

    def open_folder(self):
        folder_path = os.path.dirname(self.file_path)
        os.startfile(folder_path)

import os
from PySide6.QtCore import QFileSystemWatcher, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem
from src.widgets import exception_handler
from src.preferences import debug
from src.batch_creator.process import StartProcess
from src.qt_styles.qt_global_stylesheet import *


class MonitoringFileWatcher(QListWidget):
    open_file = Signal(str)

    def __init__(self, root_path):
        super().__init__()
        self.root_path = root_path
        self.file_system_watcher = QFileSystemWatcher()
        self.file_widgets = {}
        self.config_references = {}
        self.reference_configs = {}
        self.process_threads = {}
        self.watched_directories = set()
        self.initialize_watcher()
        self.setStyleSheet(qt_stylesheet_widgetlist)

    def initialize_watcher(self):
        if not self.root_path or not os.path.isdir(self.root_path):
            debug("Invalid root path provided to MonitoringFileWatcher.")
            return

        # Recursively add all directories to the watcher
        for dirpath, dirnames, _ in os.walk(self.root_path):
            self.add_directory_watch(dirpath)

        self.update_file_list()
        self.file_system_watcher.directoryChanged.connect(self.on_directory_changed)
        self.file_system_watcher.fileChanged.connect(self.on_file_changed)

    def add_directory_watch(self, directory):
        if directory not in self.watched_directories:
            self.file_system_watcher.addPath(directory)
            self.watched_directories.add(directory)
            debug(f"Watching directory: {directory}")

    def remove_directory_watch(self, directory):
        if directory in self.watched_directories:
            self.file_system_watcher.removePath(directory)
            self.watched_directories.remove(directory)
            debug(f"Stopped watching directory: {directory}")

    def collect_hbat_files(self):
        """
        Collect all .hbat files under self.root_path, returning them as a list.
        """
        collected_files = []
        for dirpath, _, filenames in os.walk(self.root_path):
            for filename in filenames:
                if filename.lower().endswith('.hbat'):
                    full_path = os.path.join(dirpath, filename)
                    collected_files.append(full_path)
        debug(f"Collected {len(collected_files)} .hbat files.")
        return collected_files

    def update_file_list(self):
        current_files = set(self.file_widgets.keys())
        found_files = set(self.collect_hbat_files())

        # Add new files
        new_files = found_files - current_files
        for path in new_files:
            self.add_file_widget(path)

        # Remove deleted files
        removed_files = current_files - found_files
        for path in removed_files:
            self.remove_file_widget(path)

        # Update references for existing files
        for path in found_files & current_files:
            self.update_reference(path)

        # Watch new directories if any
        for path in found_files:
            directory = os.path.dirname(path)
            self.add_directory_watch(directory)

    def add_file_widget(self, path):
        item = QListWidgetItem(self)
        widget = FileItemWidget(path)  # Assuming FileItemWidget is defined elsewhere
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)
        self.file_widgets[path] = (item, widget)

        widget.open_requested.connect(self.open_file.emit)
        widget.process_requested.connect(self.start_processing)

        self.update_reference(path)
        self.file_system_watcher.addPath(path)
        debug(f"Added watcher for file: {path}")

    def remove_file_widget(self, path):
        self.stop_processing(path)
        if path in self.file_system_watcher.files():
            self.file_system_watcher.removePath(path)
            debug(f"Removed watcher for file: {path}")
        item, _ = self.file_widgets.pop(path, (None, None))
        if item:
            self.takeItem(self.row(item))
        self.untrack_reference(path)
        debug(f"Removed file widget for: {path}")

    def update_reference(self, config_path):
        reference_path = read_reference_from_file(config_path)  # Assuming this function is defined
        if reference_path:
            self.track_reference(config_path, reference_path)
        else:
            self.untrack_reference(config_path)

    def track_reference(self, config_path, reference_path):
        old_reference = self.config_references.get(config_path)
        if old_reference and old_reference != reference_path:
            self.untrack_reference(config_path)

        self.config_references[config_path] = reference_path
        if reference_path not in self.reference_configs:
            self.reference_configs[reference_path] = set()
            self.file_system_watcher.addPath(reference_path)
            debug(f"Tracking new reference: {reference_path}")
        self.reference_configs[reference_path].add(config_path)

    def untrack_reference(self, config_path):
        reference_path = self.config_references.pop(config_path, None)
        if reference_path:
            configs = self.reference_configs.get(reference_path)
            if configs:
                configs.discard(config_path)
                if not configs:
                    self.reference_configs.pop(reference_path)
                    if reference_path in self.file_system_watcher.files():
                        self.file_system_watcher.removePath(reference_path)
                        debug(f"Stopped tracking reference: {reference_path}")

    def on_directory_changed(self, path):
        debug(f"Directory changed: {path}")
        self.update_file_list()

        # Check for new subdirectories and add them to the watcher
        for dirpath, dirnames, _ in os.walk(self.root_path):
            for dirname in dirnames:
                full_dir_path = os.path.join(dirpath, dirname)
                self.add_directory_watch(full_dir_path)

    def on_file_changed(self, path):
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
                configs = self.reference_configs.pop(path)
                for config_path in configs:
                    self.config_references.pop(config_path, None)
                    self.stop_processing(config_path)
                if path in self.file_system_watcher.files():
                    self.file_system_watcher.removePath(path)
                    debug(f"Removed non-existent reference: {path}")

    def start_processing(self, config_path):
        if config_path in self.process_threads:
            debug(f"Processing already started for: {config_path}")
            return
        process_thread = StartProcess(config_path)  # Assuming StartProcess is defined
        process_thread.finished.connect(lambda: self.on_process_finished(config_path))
        process_thread.start()
        self.process_threads[config_path] = process_thread
        debug(f"Started processing for: {config_path}")

    def stop_processing(self, config_path):
        if config_path in self.process_threads:
            thread = self.process_threads.pop(config_path)
            if thread.isRunning():
                thread.stop()  # Assuming StartProcess has a stop method
                thread.wait()
                debug(f"Stopped processing for: {config_path}")

    def on_process_finished(self, config_path):
        self.process_threads.pop(config_path, None)
        debug(f"Finished processing: {config_path}")

    def closeEvent(self, event):
        debug("Closing MonitoringFileWatcher.")
        self.file_system_watcher.directoryChanged.disconnect(self.on_directory_changed)
        self.file_system_watcher.fileChanged.disconnect(self.on_file_changed)
        for thread in list(self.process_threads.values()):
            if thread.isRunning():
                thread.stop()
                thread.wait()
        event.accept()