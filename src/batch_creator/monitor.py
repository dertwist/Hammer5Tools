import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Signal, QObject, QThread, Qt

class FileSearcherThread(QThread):
    paths_found = Signal(set)

    def __init__(self, root_path, extension='.vmat', parent=None):
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
            for path in self.paths:
                if os.path.exists(path):
                    new_mtime = os.path.getmtime(path)
                    if new_mtime != self.watched_mtimes.get(path):
                        self.watched_mtimes[path] = new_mtime
                        self.file_modified.emit(path)
                else:
                    self.paths.remove(path)
                    self.file_modified.emit(path)
            self.msleep(500)

    def update_paths(self, paths):
        self.paths = paths
        for path in paths:
            if os.path.exists(path):
                self.watched_mtimes[path] = os.path.getmtime(path)

    def stop(self):
        self.stop_thread = True
        self.wait()

class FileWatcherExample(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File System Watcher")
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
        self.searcher_thread = None
        self.watcher_thread = None
        root_path = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\test"
        self.path_input.setText(root_path)
        self.set_root_path()

    def set_root_path(self):
        root_path = self.path_input.text()
        if not root_path or not os.path.isdir(root_path):
            return
        if self.searcher_thread:
            self.searcher_thread.stop()
        self.searcher_thread = FileSearcherThread(root_path)
        self.searcher_thread.paths_found.connect(self.on_paths_found)
        self.searcher_thread.start()

    def on_paths_found(self, paths):
        self.file_list.clear()
        for path in sorted(paths):
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.UserRole, path)
            self.file_list.addItem(item)
        if self.watcher_thread:
            self.watcher_thread.stop()
        self.watcher_thread = FileWatcherThread(list(paths))
        self.watcher_thread.file_modified.connect(self.on_file_modified)
        self.watcher_thread.start()

    def on_file_modified(self, path):
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.data(Qt.UserRole) == path:
                item.setText(f"{os.path.basename(path)} [Modified]")
                break

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