import sys
import os
from PySide6.QtCore import Qt, QSize, QThreadPool, QRunnable, QObject, Signal, QFileSystemWatcher
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeView, QFileSystemModel, QSplitter, QLabel
from PySide6.QtGui import QPixmap, QIcon


class ThumbnailWorkerSignals(QObject):
    """Signals class for communicating between threads and the main UI."""
    result = Signal(str, QIcon)  # file path and QIcon


class ThumbnailWorker(QRunnable):
    """Worker thread for loading image thumbnails in the background."""
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.signals = ThumbnailWorkerSignals()

    def run(self):
        """Generate the thumbnail in a separate thread."""
        pixmap = QPixmap(self.file_path)
        if not pixmap.isNull():
            thumbnail = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon = QIcon(thumbnail)
            self.signals.result.emit(self.file_path, icon)


class ImageViewer(QMainWindow):
    def __init__(self, tree_directory=None):
        super().__init__()

        # Main widget
        self.setWindowTitle("Explorer")
        self.setGeometry(100, 100, 1000, 600)

        # Splitter to separate tree and image view
        splitter = QSplitter(self)

        # Tree View for the folder structure and image thumbnails
        self.tree_view = QTreeView()
        self.tree_view.setIconSize(QSize(128, 128))  # Set the icon size for large image thumbnails

        # File system model
        self.file_model = QFileSystemModelWithThumbnails(self)  # Custom file model to display thumbnails
        root_path = tree_directory  # Set the root path here
        self.file_model.setRootPath(root_path)  # Set the root path for the file system
        self.file_model.setNameFilters(["*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif", "*.tga"])  # Show only image files
        self.file_model.setNameFilterDisables(False)

        # Set the file model to the tree view
        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(root_path))  # Set initial directory
        self.tree_view.clicked.connect(self.on_item_click)

        # Image display label for selected image
        self.image_label = QLabel("Select an image to view", self)
        self.image_label.setAlignment(Qt.AlignCenter)

        # Add tree view and image display to the splitter
        splitter.addWidget(self.tree_view)
        splitter.addWidget(self.image_label)

        # Set the central widget
        self.setCentralWidget(self.tree_view)



        self.tree_view.header().setDefaultSectionSize(120)  # Set the default section size for all columns

        # Set the size for the first column specifically
        self.tree_view.header().resizeSection(0, 400)  # Adjust the size (200) as needed

        self.tree_view.header().hideSection(1)
        self.tree_view.header().hideSection(2)
        self.tree_view.header().hideSection(3)




    def on_item_click(self, index):
        # Get the file path of the clicked item
        file_path = self.file_model.filePath(index)

        # If the clicked item is a file (image), load it in the label
        if not self.file_model.isDir(index):
            pixmap = QPixmap(file_path)
            self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


# Rest of the code remains the same

    def on_item_click(self, index):
        # Get the file path of the clicked item
        file_path = self.file_model.filePath(index)

        # If the clicked item is a file (image), load it in the label
        if not self.file_model.isDir(index):
            pixmap = QPixmap(file_path)
            self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


class QFileSystemModelWithThumbnails(QFileSystemModel):
    """Custom QFileSystemModel that provides image thumbnails for the first column only, with async loading and caching."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thumbnail_cache = {}  # Cache for storing thumbnails
        self.thread_pool = QThreadPool()  # Thread pool for asynchronous thumbnail loading
        self.watcher = QFileSystemWatcher()  # File system watcher for monitoring changes

        self.watcher.fileChanged.connect(self.on_file_changed)  # Connect signal when a file is changed

    def data(self, index, role=Qt.DisplayRole):
        # Only provide thumbnail for the first column and decoration role (which sets icons)
        if index.column() == 0 and role == Qt.DecorationRole:
            file_path = self.filePath(index)
            if not self.isDir(index):
                # Add the file to the watcher to monitor changes
                if not self.watcher.files() or file_path not in self.watcher.files():
                    self.watcher.addPath(file_path)

                # Check if the thumbnail is already in cache
                if file_path in self.thumbnail_cache:
                    return self.thumbnail_cache[file_path]
                else:
                    # Schedule a background task to load the thumbnail
                    self.load_thumbnail_async(file_path)
        return super().data(index, role)

    def load_thumbnail_async(self, file_path):
        """Load thumbnail in a separate thread and cache it."""
        worker = ThumbnailWorker(file_path)
        worker.signals.result.connect(self.on_thumbnail_loaded)
        self.thread_pool.start(worker)

    def on_thumbnail_loaded(self, file_path, icon):
        """Callback when thumbnail is loaded and cached."""
        self.thumbnail_cache[file_path] = icon
        # Trigger the view to update and display the thumbnail
        index = self.index(file_path)
        self.dataChanged.emit(index, index, [Qt.DecorationRole])

    def on_file_changed(self, file_path):
        """Callback when the monitored file is changed."""
        if file_path in self.thumbnail_cache:
            # Remove the outdated thumbnail from the cache
            del self.thumbnail_cache[file_path]
            # Reload the thumbnail for the changed file
            self.load_thumbnail_async(file_path)
            # Emit a dataChanged signal to refresh the UI
            index = self.index(file_path)
            self.dataChanged.emit(index, index, [Qt.DecorationRole])



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageViewer()
    window.show()
    sys.exit(app.exec())
