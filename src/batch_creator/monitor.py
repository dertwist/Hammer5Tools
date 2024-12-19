import os
import json
from PySide6.QtWidgets import (
    QListWidget, QListWidgetItem, QWidget, QLabel, QPushButton, QHBoxLayout
)
from PySide6.QtCore import QThread, Signal, QSize
from PySide6.QtGui import QIcon
from src.preferences import get_addon_dir
from src.batch_creator.process import StartProcess

def read_reference_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            process = data.get('process', {})
            reference = process.get('reference', '')
            return reference
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return ''

class FileSearcherThread(QThread):
    paths_found = Signal(set)

    def __init__(self, root_path, extension='.hbat', parent=None):
        super().__init__(parent)
        self.root_path = root_path
        self.extension = extension
        self.stop_thread = False

    def run(self):
        previous_paths = set()
        while not self.stop_thread:
            current_paths = set()
            for dirpath, _, filenames in os.walk(self.root_path):
                for filename in filenames:
                    if filename.endswith(self.extension):
                        full_path = os.path.join(dirpath, filename)
                        current_paths.add(full_path)
            if current_paths != previous_paths:
                self.paths_found.emit(current_paths)
                previous_paths = current_paths
            self.msleep(500)

    def stop(self):
        self.stop_thread = True
        self.wait()

class FileWatcherThread(QThread):
    file_modified = Signal(str)
    reference_found = Signal(str, str)

    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self.paths = paths
        self.stop_thread = False
        self.watched_mtimes = {}

    def run(self):
        for path in self.paths:
            if os.path.exists(path):
                self.watched_mtimes[path] = os.path.getmtime(path)
        while not self.stop_thread:
            for path in list(self.paths):
                if os.path.exists(path):
                    new_mtime = os.path.getmtime(path)
                    if new_mtime != self.watched_mtimes.get(path, 0):
                        self.watched_mtimes[path] = new_mtime
                        self.file_modified.emit(path)

                        # Check for a reference in the modified file
                        reference = read_reference_from_file(path)
                        if reference:
                            reference_path = os.path.join(get_addon_dir(), reference)
                            self.reference_found.emit(path, reference_path)
                else:
                    self.paths.remove(path)
                    self.file_modified.emit(path)
            self.msleep(500)

    def stop(self):
        self.stop_thread = True
        self.wait()

class ReferenceWatcherThread(QThread):
    reference_modified = Signal(str)

    def __init__(self, reference_path, original_path, parent=None):
        super().__init__(parent)
        self.reference_path = reference_path
        self.original_path = original_path
        self.stop_thread = False
        self.last_mtime = None

    def run(self):
        if os.path.exists(self.reference_path):
            self.last_mtime = os.path.getmtime(self.reference_path)
        else:
            self.last_mtime = 0

        while not self.stop_thread:
            if os.path.exists(self.reference_path):
                new_mtime = os.path.getmtime(self.reference_path)
                if new_mtime != self.last_mtime:
                    self.last_mtime = new_mtime
                    self.reference_modified.emit(self.original_path)
            else:
                # Reference file has been deleted
                self.reference_modified.emit(self.original_path)
                self.stop_thread = True
            self.msleep(500)

    def stop(self):
        self.stop_thread = True
        self.wait()

class FileItemWidget(QWidget):
    open = Signal(str)
    realtime_toggle = Signal(str)

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.is_playing = True
        self.init_ui()
        self.setStyleSheet("""
            QWidget {
                background-color: None;
                outline: none;
            }
        """)

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.label = QLabel(os.path.basename(self.file_path))
        self.label.setContentsMargins(0, 0, 0, 0)

        self.button_realtime_toggle = QPushButton()
        self.button_open = QPushButton()

        self.button_realtime_toggle.setIcon(QIcon(":/valve_common/icons/tools/common/control_play.png"))
        self.button_open.setIcon(QIcon(":/valve_common/icons/tools/common/edit.png"))

        button_size = QSize(24, 24)
        self.button_realtime_toggle.setFixedSize(button_size)
        self.button_open.setFixedSize(button_size)

        icon_size = QSize(16, 16)
        self.button_realtime_toggle.setIconSize(icon_size)
        self.button_open.setIconSize(icon_size)

        button_stylesheet = """
            QPushButton {
                border: none;
                background: none;
            }
            QPushButton:hover {
                background-color: None;
            }
            QPushButton:pressed {
                background-color: None;
                margin: 0px;
            }
        """
        self.button_realtime_toggle.setStyleSheet(button_stylesheet)
        self.button_open.setStyleSheet(button_stylesheet)

        layout.addWidget(self.label)
        layout.addWidget(self.button_realtime_toggle)
        layout.addWidget(self.button_open)

        self.setLayout(layout)
        self.setContentsMargins(0, 2, 0, 2)

        self.button_realtime_toggle.clicked.connect(self.action_realtime_toggle)
        self.button_open.clicked.connect(self.action_open)

    def action_realtime_toggle(self):
        if self.is_playing:
            self.button_realtime_toggle.setIcon(QIcon(":/valve_common/icons/tools/common/control_pause.png"))
        else:
            self.button_realtime_toggle.setIcon(QIcon(":/valve_common/icons/tools/common/control_play.png"))
        self.is_playing = not self.is_playing
        self.realtime_toggle.emit(self.file_path)

    def action_open(self):
        self.open.emit(self.file_path)

    def mark_modified(self):
        self.label.setText(f"{os.path.basename(self.file_path)} [Modified]")

class MonitoringFileWatcher(QListWidget):
    def __init__(self, root_path):
        super().__init__()
        self.root_path = root_path
        self.searcher_thread = None
        self.watcher_thread = None
        self.reference_watchers = {}
        self.process_threads = {}
        self.file_widgets = {}
        self.set_root_path(root_path)

    def set_root_path(self, root_path):
        if not root_path or not os.path.isdir(root_path):
            return
        if self.searcher_thread:
            self.searcher_thread.stop()
            self.searcher_thread.wait()
        self.searcher_thread = FileSearcherThread(root_path)
        self.searcher_thread.paths_found.connect(self.on_paths_found)
        self.searcher_thread.start()

    def on_paths_found(self, paths):
        set_paths = set(paths)
        current_file_paths = set(self.file_widgets.keys())

        # Remove widgets for files that no longer exist
        for path in current_file_paths - set_paths:
            self.remove_file_widget(path)

        # Add widgets for new files
        for path in set_paths - current_file_paths:
            self.add_file_widget(path)

        # Update the watcher thread with the new paths
        if self.watcher_thread:
            self.watcher_thread.stop()
            self.watcher_thread.wait()
        sorted_paths = sorted(set_paths)
        self.watcher_thread = FileWatcherThread(sorted_paths)
        self.watcher_thread.file_modified.connect(self.on_file_modified)
        self.watcher_thread.reference_found.connect(self.on_reference_found)
        self.watcher_thread.start()

    def add_file_widget(self, path):
        item = QListWidgetItem(self)
        widget = FileItemWidget(path)
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)
        self.file_widgets[path] = (item, widget)

    def remove_file_widget(self, path):
        item, _ = self.file_widgets.pop(path, (None, None))
        if item:
            row = self.row(item)
            self.takeItem(row)

    def on_file_modified(self, path):
        if path in self.file_widgets:
            _, widget = self.file_widgets[path]
            widget.mark_modified()

    def on_reference_found(self, original_path, reference_path):
        print(f'Found reference in {original_path}, monitoring {reference_path}')

        # Ensure only one watcher per reference file
        if original_path in self.reference_watchers:
            watcher = self.reference_watchers[original_path]
            watcher.stop()
            watcher.wait()
            del self.reference_watchers[original_path]

        # Start monitoring the reference file
        watcher = ReferenceWatcherThread(reference_path, original_path)
        watcher.reference_modified.connect(self.on_reference_modified)
        watcher.start()
        self.reference_watchers[original_path] = watcher

    def on_reference_modified(self, original_path):
        print(f'Reference file modified, processing {original_path}')

        # Stop existing process thread if running
        if original_path in self.process_threads:
            thread = self.process_threads[original_path]
            if thread.isRunning():
                thread.stop()
                thread.wait()
            del self.process_threads[original_path]

        # Start processing in a new thread
        process_thread = StartProcess(original_path)
        process_thread.finished.connect(lambda: self.on_process_finished(original_path))
        process_thread.start()
        self.process_threads[original_path] = process_thread

    def on_process_finished(self, original_path):
        print(f'Processing of {original_path} finished.')
        # Remove the process thread from the dictionary
        if original_path in self.process_threads:
            del self.process_threads[original_path]

    def closeEvent(self, event):
        # Stop all threads when closing
        if self.searcher_thread:
            self.searcher_thread.stop()
            self.searcher_thread.wait()
        if self.watcher_thread:
            self.watcher_thread.stop()
            self.watcher_thread.wait()
        for watcher in self.reference_watchers.values():
            watcher.stop()
            watcher.wait()
        for process_thread in self.process_threads.values():
            process_thread.stop()
            process_thread.wait()
        event.accept()

import os
import json
from PySide6.QtWidgets import (
    QListWidget, QListWidgetItem, QWidget, QLabel, QPushButton, QHBoxLayout
)
from PySide6.QtCore import QThread, Signal, QSize
from PySide6.QtGui import QIcon
from src.preferences import get_addon_dir
from src.batch_creator.process import StartProcess

def read_reference_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            process = data.get('process', {})
            reference = process.get('reference', '')
            return reference
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return ''

class ReferencesWatcherThread(QThread):
    file_modified = Signal(str)
    reference_found = Signal(str, str)

    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self.paths = paths
        self.stop_thread = False
        self.watched_mtimes = {}

    def run(self):
        for path in self.paths:
            if os.path.exists(path):
                self.watched_mtimes[path] = os.path.getmtime(path)
        while not self.stop_thread:
            for path in list(self.paths):
                if os.path.exists(path):
                    new_mtime = os.path.getmtime(path)
                    if new_mtime != self.watched_mtimes.get(path, 0):
                        self.watched_mtimes[path] = new_mtime
                        self.file_modified.emit(path)

                        # Check for a reference in the modified file
                        reference = read_reference_from_file(path)
                        if reference:
                            reference_path = os.path.join(get_addon_dir(), reference)
                            self.reference_found.emit(path, reference_path)
                else:
                    self.paths.remove(path)
                    self.file_modified.emit(path)
            self.msleep(500)

    def stop(self):
        self.stop_thread = True
        self.wait()