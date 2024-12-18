import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Signal, QThread, QFileSystemWatcher, QObject, QMutex, QMutexLocker

class FileSearcherThread(QThread):
    paths_found = Signal(set)

    def __init__(self, root_path, parent=None):
        super().__init__(parent)
        self.root_path = root_path
        self.stop_thread = False
        self.mutex = QMutex()

    def run(self):
        previous_paths = set()
        while not self.stop_thread:
            current_paths = set()
            for dirpath, _, filenames in os.walk(self.root_path):
                for filename in filenames:
                    if filename.endswith('.hbat'):
                        full_path = os.path.join(dirpath, filename)
                        current_paths.add(full_path)

            if current_paths != previous_paths:
                with QMutexLocker(self.mutex):
                    self.paths_found.emit(current_paths)
                previous_paths = current_paths

            self.msleep(500)  # Sleep for 500 ms to reduce CPU usage

    def stop(self):
        self.stop_thread = True
        self.wait()

class FileWatcherThread(QObject):
    file_changed = Signal(str)
    file_removed = Signal(str)
    file_added = Signal(str)

    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(self.on_file_changed)
        self.watcher.directoryChanged.connect(self.on_directory_changed)
        self.paths = paths
        self.update_watched_files(paths)

    def update_watched_files(self, paths):
        self.watcher.removePaths(self.watcher.files())
        self.watcher.addPaths(list(paths))

    def on_file_changed(self, path):
        if os.path.exists(path):
            self.file_changed.emit(path)
        else:
            self.file_removed.emit(path)

    def on_directory_changed(self, path):
        # Handle directory changes if needed
        pass

    def stop(self):
        self.watcher.removePaths(self.watcher.files())

class FileWatcherExample(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File System Watcher Example")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Enter root path to monitor")
        self.layout.addWidget(self.path_input)

        self.add_path_button = QPushButton("Set Root Path")
        self.layout.addWidget(self.add_path_button)
        self.add_path_button.clicked.connect(self.set_root_path)

        self.file_list = QListWidget()
        self.layout.addWidget(self.file_list)

        self.changed_files = {}

        self.searcher_thread = None
        self.watcher_thread = None

        # Initial path
        root_path = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\test"
        self.path_input.setText(root_path)
        self.set_root_path()

    def set_root_path(self):
        root_path = self.path_input.text()
        if not root_path or not os.path.isdir(root_path):
            return  # Invalid path

        if self.searcher_thread:
            self.searcher_thread.stop()

        self.searcher_thread = FileSearcherThread(root_path)
        self.searcher_thread.paths_found.connect(self.on_paths_found)
        self.searcher_thread.start()

    def on_paths_found(self, paths):
        # Update the file list
        self.file_list.clear()
        for path in paths:
            item = QListWidgetItem(os.path.basename(path))
            item.setData(1, path)  # Store the full path
            self.file_list.addItem(item)

        # Update the watcher
        if self.watcher_thread:
            self.watcher_thread.stop()

        self.watcher_thread = FileWatcherThread(paths)
        self.watcher_thread.file_changed.connect(self.on_file_changed)
        self.watcher_thread.file_removed.connect(self.on_file_removed)
        self.watcher_thread.file_added.connect(self.on_file_added)

    def on_file_changed(self, path):
        self.mark_file_changed(path)

    def on_file_removed(self, path):
        self.mark_file_removed(path)

    def on_file_added(self, path):
        self.mark_file_added(path)

    def mark_file_changed(self, path):
        # Find the item in the list and mark it
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.data(1) == path:
                item.setText(f"{os.path.basename(path)} [Modified]")
                break

    def mark_file_removed(self, path):
        # Remove the item from the list
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.data(1) == path:
                self.file_list.takeItem(i)
                break

    def mark_file_added(self, path):
        # Add the new item to the list
        item = QListWidgetItem(f"{os.path.basename(path)} [Added]")
        item.setData(1, path)
        self.file_list.addItem(item)

    def closeEvent(self, event):
        if self.searcher_thread:
            self.searcher_thread.stop()
        if self.watcher_thread:
            self.watcher_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileWatcherExample()
    window.show()
    sys.exit(app.exec())