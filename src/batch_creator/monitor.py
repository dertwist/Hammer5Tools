import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem, QLabel, QHBoxLayout
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
            for path in list(self.paths):
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

class FileItemWidget(QWidget):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        self.label = QLabel(os.path.basename(self.file_path))
        self.button1 = QPushButton("Action 1")
        self.button2 = QPushButton("Action 2")

        layout.addWidget(self.label)
        layout.addWidget(self.button1)
        layout.addWidget(self.button2)

        self.setLayout(layout)

        # Connect buttons to their actions
        self.button1.clicked.connect(self.action1)
        self.button2.clicked.connect(self.action2)

    def action1(self):
        # Implement action 1
        print(f"Action 1 triggered for {self.file_path}")

    def action2(self):
        # Implement action 2
        print(f"Action 2 triggered for {self.file_path}")

    def mark_modified(self):
        self.label.setText(f"{os.path.basename(self.file_path)} [Modified]")

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
        self.file_widgets = {}

        # Set initial root path if needed
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
        sorted_paths = sorted(set_paths)
        self.watcher_thread = FileWatcherThread(sorted_paths)
        self.watcher_thread.file_modified.connect(self.on_file_modified)
        self.watcher_thread.start()

    def add_file_widget(self, path):
        item = QListWidgetItem(self.file_list)
        widget = FileItemWidget(path)
        item.setSizeHint(widget.sizeHint())
        self.file_list.addItem(item)
        self.file_list.setItemWidget(item, widget)
        self.file_widgets[path] = (item, widget)

    def remove_file_widget(self, path):
        item, _ = self.file_widgets.pop(path)
        row = self.file_list.row(item)
        self.file_list.takeItem(row)

    def on_file_modified(self, path):
        if path in self.file_widgets:
            _, widget = self.file_widgets[path]
            widget.mark_modified()

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