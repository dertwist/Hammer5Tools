# src/batch_creator/monitor.py

import os
import json
from PySide6.QtWidgets import (
    QListWidget, QListWidgetItem, QWidget, QLabel, QPushButton, QHBoxLayout
)
from PySide6.QtCore import Signal, QSize, QFileSystemWatcher
from PySide6.QtGui import QIcon
from src.preferences import get_addon_dir
from src.batch_creator.process import StartProcess

def read_reference_from_file(config_path):
    try:
        with open(config_path, 'r') as file:
            data = json.load(file)
            process = data.get('process', {})
            reference = process.get('reference', '')
            if reference:
                return os.path.join(get_addon_dir(), reference)
    except Exception as e:
        print(f"Error reading {config_path}: {e}")
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

        self.label = QLabel(os.path.basename(self.file_path))
        self.play_button = QPushButton()
        self.open_button = QPushButton()

        self.play_button.setIcon(QIcon(":/valve_common/icons/tools/common/control_play.png"))
        self.open_button.setIcon(QIcon(":/valve_common/icons/tools/common/edit.png"))

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

    def mark_modified(self):
        self.label.setText(f"{os.path.basename(self.file_path)} [Modified]")

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
        self.initialize_watcher()

    def initialize_watcher(self):
        if not self.root_path or not os.path.isdir(self.root_path):
            return

        self.update_file_list()
        self.file_system_watcher.directoryChanged.connect(self.on_directory_changed)
        self.file_system_watcher.fileChanged.connect(self.on_file_changed)
        self.file_system_watcher.addPath(self.root_path)

    def update_file_list(self):
        current_files = set(self.file_widgets.keys())
        found_files = set()

        for dirpath, _, filenames in os.walk(self.root_path):
            for filename in filenames:
                if filename.lower().endswith('.hbat'):
                    full_path = os.path.join(dirpath, filename)
                    found_files.add(full_path)
                    if full_path not in self.file_widgets:
                        self.add_file_widget(full_path)

        # Remove widgets for files that no longer exist
        for path in current_files - found_files:
            self.remove_file_widget(path)

        # Update watchers for new files
        new_files = found_files - current_files
        for path in new_files:
            if path not in self.file_system_watcher.files():
                self.file_system_watcher.addPath(path)
                self.update_reference(path)

    def add_file_widget(self, path):
        item = QListWidgetItem(self)
        widget = FileItemWidget(path)
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)
        self.file_widgets[path] = (item, widget)

        widget.open_requested.connect(self.open_file.emit)
        widget.process_requested.connect(self.start_processing)

        self.update_reference(path)
        self.file_system_watcher.addPath(path)

    def remove_file_widget(self, path):
        self.stop_processing(path)
        if path in self.file_system_watcher.files():
            self.file_system_watcher.removePath(path)
        item, _ = self.file_widgets.pop(path, (None, None))
        if item:
            self.takeItem(self.row(item))
        self.untrack_reference(path)

    def update_reference(self, config_path):
        reference_path = read_reference_from_file(config_path)
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

    def on_directory_changed(self, path):
        self.update_file_list()

    def on_file_changed(self, path):
        if os.path.exists(path):
            if path in self.file_widgets:
                # Config file changed
                self.update_reference(path)
                _, widget = self.file_widgets[path]
                widget.mark_modified()
                self.stop_processing(path)
                self.start_processing(path)
            elif path in self.reference_configs:
                # Reference file changed
                configs = self.reference_configs[path]
                for config_path in configs:
                    _, widget = self.file_widgets.get(config_path, (None, None))
                    if widget:
                        widget.mark_modified()
                    self.stop_processing(config_path)
                    self.start_processing(config_path)
        else:
            if path in self.file_widgets:
                self.remove_file_widget(path)
            elif path in self.reference_configs:
                configs = self.reference_configs.pop(path)
                for config_path in configs:
                    self.config_references.pop(config_path, None)
                    _, widget = self.file_widgets.get(config_path, (None, None))
                    if widget:
                        widget.mark_modified()
                    self.stop_processing(config_path)
                if path in self.file_system_watcher.files():
                    self.file_system_watcher.removePath(path)

    def start_processing(self, config_path):
        # Start processing in a separate thread
        if config_path in self.process_threads:
            # If already processing, do nothing
            return
        process_thread = StartProcess(config_path)
        process_thread.finished.connect(lambda: self.on_process_finished(config_path))
        process_thread.start()
        self.process_threads[config_path] = process_thread

    def stop_processing(self, config_path):
        if config_path in self.process_threads:
            thread = self.process_threads.pop(config_path)
            if thread.isRunning():
                thread.stop()
                thread.wait()

    def on_process_finished(self, config_path):
        self.process_threads.pop(config_path, None)
        print(f"Finished processing {config_path}")

    def closeEvent(self, event):
        self.file_system_watcher.directoryChanged.disconnect(self.on_directory_changed)
        self.file_system_watcher.fileChanged.disconnect(self.on_file_changed)
        for thread in self.process_threads.values():
            if thread.isRunning():
                thread.stop()
                thread.wait()
        event.accept()