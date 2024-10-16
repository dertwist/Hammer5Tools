import sys
import os
from PySide6.QtCore import Qt, QSize, QThreadPool, QRunnable, QObject, Signal, QFileSystemWatcher, QPointF
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeView, QFileSystemModel, QSplitter, QLabel, QFrame, QScrollArea, QStackedLayout, QVBoxLayout, QWidget, QPushButton
from PySide6.QtGui import QPixmap, QIcon, QAction, QKeySequence

import sys
import os
from PySide6.QtCore import Qt, QDir, QPoint
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QScrollArea, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QToolBar
from PySide6.QtGui import QPixmap, QIcon, QKeySequence, QWheelEvent, QMouseEvent



class AdvancedImageViewer(QMainWindow):
    def __init__(self, image_directory=None):
        super().__init__()
        self.initUI()
        self.current_image_index = -1
        self.image_files = []
        self.panning = False  # Variable to track panning state
        self.pan_start_point = QPointF(0, 0)  # Starting point for the pan
        if image_directory:
            self.loadImagesFromDirectory(image_directory)

    def initUI(self):

        # Main Image Display
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)  # Keeps original formatting when fitting to window

        # Scroll Area to support large images
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.image_label)

        # Set the central widget
        self.setCentralWidget(self.scroll_area)

        self.current_pixmap = None
        self.zoom_level = 1.0

    def loadImagesFromDirectory(self, directory):
        """Load images from the specified directory and set the first image."""
        valid_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga"]
        self.image_files = [os.path.join(directory, f) for f in os.listdir(directory)
                            if os.path.splitext(f)[1].lower() in valid_extensions]

        if self.image_files:
            self.current_image_index = 0
            self.showImage(self.image_files[self.current_image_index])

    def showImage(self, image_path):
        """Display the selected image."""
        self.current_pixmap = QPixmap(image_path)
        if not self.current_pixmap.isNull():
            self.image_label.setPixmap(self.current_pixmap)
            self.image_label.adjustSize()  # Adjust the QLabel to fit the pixmap size
            self.zoom_level = 1.0  # Reset zoom level after loading a new image
            self.updateWindowTitle(image_path)

    def updateWindowTitle(self, image_path):
        """Update the window title with the image file name."""
        self.setWindowTitle(f"Advanced Image Viewer - {os.path.basename(image_path)}")

    def zoomIn(self):
        """Increase zoom level."""
        if self.current_pixmap:
            self.zoom_level *= 1.2
            self.updateImageDisplay()

    def zoomOut(self):
        """Decrease zoom level."""
        if self.current_pixmap:
            self.zoom_level /= 1.2
            self.updateImageDisplay()

    def fitToWindow(self):
        """Fit the image to the size of the scroll area, keeping the original aspect ratio."""
        if self.current_pixmap:
            self.zoom_level = min(self.scroll_area.viewport().width() / self.current_pixmap.width(),
                                  self.scroll_area.viewport().height() / self.current_pixmap.height())
            self.updateImageDisplay()

    def updateImageDisplay(self):
        """Update the image display based on the current zoom level."""
        if self.current_pixmap:
            scaled_pixmap = self.current_pixmap.scaled(self.current_pixmap.size() * self.zoom_level,
                                                       Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.adjustSize()  # Adjust the QLabel size

    def wheelEvent(self, event: QWheelEvent):
        """Handle zooming with the mouse wheel."""
        if event.angleDelta().y() > 0:
            self.zoomIn()
        else:
            self.zoomOut()

    def mousePressEvent(self, event: QMouseEvent):
        """Handle middle mouse button press for panning."""
        if event.button() == Qt.MiddleButton:
            self.panning = True
            self.pan_start_point = event.position()
            QApplication.setOverrideCursor(Qt.ClosedHandCursor)  # Change cursor to hand

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle image panning when middle mouse button is pressed."""
        if self.panning:
            delta = event.position() - self.pan_start_point
            self.scroll_area.horizontalScrollBar().setValue(self.scroll_area.horizontalScrollBar().value() - delta.x())
            self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().value() - delta.y())
            self.pan_start_point = event.position()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Stop panning when middle mouse button is released."""
        if event.button() == Qt.MiddleButton:
            self.panning = False
            QApplication.restoreOverrideCursor()  # Restore the default cursor


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


class ExplorerImageViewer(QMainWindow):
    def __init__(self, tree_directory=None):
        super().__init__()

        # Main widget
        self.setWindowTitle("Explorer")
        # self.setGeometry(100, 100, 1000, 600)

        # Splitter to separate tree and image view
        splitter = QSplitter(self)

        # Tree View for the folder structure and image thumbnails
        self.tree_view = QTreeView()
        self.tree_view.setIconSize(QSize(64, 64))  # Set the icon size for large image thumbnails

        # File system model
        self.file_model = QFileSystemModelWithThumbnails(self)  # Custom file model to display thumbnails
        root_path = tree_directory if tree_directory else os.path.expanduser("~")  # Default to user's home directory
        self.file_model.setRootPath(root_path)  # Set the root path for the file system
        self.file_model.setNameFilters(["*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif", "*.tga"])  # Show only image files
        self.file_model.setNameFilterDisables(False)

        # Set the file model to the tree view
        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(root_path))  # Set initial directory
        self.tree_view.clicked.connect(self.on_item_click)

        # Image display viewer for selected image
        self.image_viewer = AdvancedImageViewer()

        # Add tree view and image display to the splitter
        splitter.addWidget(self.tree_view)
        splitter.addWidget(self.image_viewer)

        # Set the central widget
        self.setCentralWidget(splitter)

        # Tree view customization
        self.tree_view.header().setDefaultSectionSize(120)  # Set the default section size for all columns
        self.tree_view.header().resizeSection(0, 160)  # Adjust the size (400) for the first column
        self.tree_view.header().hideSection(1)
        self.tree_view.header().hideSection(2)
        self.tree_view.header().hideSection(3)
        self.tree_explorer = self.tree_view

    def on_item_click(self, index):
        # Get the file path of the clicked item
        file_path = self.file_model.filePath(index)

        # If the clicked item is a file (image), load it in the image viewer
        if not self.file_model.isDir(index):
            self.image_viewer.showImage(file_path)
            self.image_viewer.fitToWindow()


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
                if file_path not in self.watcher.files():
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
    window = ExplorerImageViewer()
    window.show()
    sys.exit(app.exec())
