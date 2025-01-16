import sys
import time
from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget, QMessageBox
from PySide6.QtCore import QDir
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileWatcherExample(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File System Watcher Example")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.layout.addWidget(self.text_edit)

        self.last_event_time = {}
        self.debounce_time = 0.5  # 500 milliseconds

        root_path = r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\batch_creator"

        if QDir(root_path).exists():
            self.start_watching(root_path)
        else:
            QMessageBox.critical(self, "Error", f"The directory {root_path} does not exist.")
            self.close()

    def start_watching(self, path):
        event_handler = FileSystemEventHandler()
        event_handler.on_modified = self.on_modified
        event_handler.on_created = self.on_created
        event_handler.on_deleted = self.on_deleted
        event_handler.on_moved = self.on_moved

        self.observer = Observer()
        self.observer.schedule(event_handler, path, recursive=True)
        self.observer.start()

    def should_process_event(self, event):
        current_time = time.time()
        last_time = self.last_event_time.get(event.src_path, 0)
        if current_time - last_time > self.debounce_time:
            self.last_event_time[event.src_path] = current_time
            return True
        return False

    def on_modified(self, event):
        if self.should_process_event(event):
            self.text_edit.append(f"Modified: {event.src_path}")

    def on_created(self, event):
        if self.should_process_event(event):
            self.text_edit.append(f"Created: {event.src_path}")

    def on_deleted(self, event):
        if self.should_process_event(event):
            self.text_edit.append(f"Deleted: {event.src_path}")

    def on_moved(self, event):
        if self.should_process_event(event):
            self.text_edit.append(f"Moved: from {event.src_path} to {event.dest_path}")

    def closeEvent(self, event):
        self.observer.stop()
        self.observer.join()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileWatcherExample()
    window.show()
    sys.exit(app.exec())