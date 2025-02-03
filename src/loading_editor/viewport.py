import os
import shutil
import sys
import tempfile

from PySide6.QtCore import (
    Qt,
    QSize,
    QThreadPool,
    QRunnable,
    QObject,
    Signal,
    QFileSystemWatcher,
    QPointF,
    QRectF
)
from PySide6.QtGui import (
    QPixmap,
    QIcon,
    QWheelEvent,
    QMouseEvent,
    QDragEnterEvent,
    QDropEvent,
    QImage,
    QPainter,
    QColor,
    QFont,
    QFontMetrics,
    QTransform,
    QGuiApplication,
    QAction
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTreeView,
    QFileSystemModel,
    QSplitter,
    QLabel,
    QScrollArea,
    QMenu,
    QWidget,
    QVBoxLayout,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsBlurEffect
)

##############################################################################
# Utility functions for image processing
##############################################################################

import os
import sys
import tempfile
import random

from PySide6.QtCore import Qt, QRectF, QPointF, QSize
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QFontMetrics, QPen, QBrush, QLinearGradient
from PySide6.QtSvg import QSvgRenderer
from src.loading_editor.preview import *

class NoWheelScrollArea(QScrollArea):
    """
    Custom scroll area that ignores wheel events.
    This ensures that zooming is managed by the Viewport.
    """
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()

class Viewport(QMainWindow):
    """
    Main image viewer providing zoom, panning, and image processing.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.panning = False
        self.pan_start_point = QPointF(0, 0)
        self.current_pixmap = None
        self.zoom_level = 1.0
        self.image_files = []
        self.current_image_index = 0

        self.setupUI()

    def setupUI(self):
        self.container = QWidget(self)
        self.setCentralWidget(self.container)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Placeholder when no image is loaded
        self.placeholder_label = QLabel(self.container)
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setText("Select an image from the explorer")
        self.placeholder_label.setStyleSheet("color: gray; font-size: 13px;")

        # Label used to display the actual image
        self.image_label = QLabel(self.container)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)

        # Scroll area to enable panning
        self.scroll_area = NoWheelScrollArea(self.container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout.addWidget(self.placeholder_label)
        layout.addWidget(self.scroll_area)

        # Initially, display placeholder
        self.placeholder_label.show()
        self.scroll_area.hide()

    def set_placeholder_text(self):
        """
        Display the placeholder and hide the image view.
        """
        self.placeholder_label.setText("Select an image from the explorer")
        self.placeholder_label.setStyleSheet("color: gray; font-size: 16px;")
        self.placeholder_label.show()
        self.scroll_area.hide()
        self.image_label.clear()

    def clear_placeholder_text(self):
        """
        Hide the placeholder and show the image view.
        """
        self.placeholder_label.hide()
        self.placeholder_label.clear()
        self.placeholder_label.setStyleSheet("")
        self.scroll_area.show()

    def loadImagesFromDirectory(self, directory):
        """
        Load images from a directory with valid image extensions.
        """
        valid_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga"]
        if not os.path.isdir(directory):
            self.set_placeholder_text()
            return

        try:
            self.image_files = [
                os.path.join(directory, f)
                for f in os.listdir(directory)
                if os.path.splitext(f)[1].lower() in valid_extensions
            ]
            if self.image_files:
                self.current_image_index = 0
                self.processAndPreviewImage(self.image_files[self.current_image_index], "", "Processed by Hammer5")
            else:
                self.set_placeholder_text()
        except Exception as e:
            print(f"Error loading images from directory '{directory}': {e}")
            self.set_placeholder_text()

    def showImage(self, image_path):
        """
        Load and display an image using QPixmap.
        """
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.set_placeholder_text()
            return
        self.current_pixmap = pixmap
        self.clear_placeholder_text()
        self.image_label.setPixmap(self.current_pixmap)
        self.zoom_level = 1.0
        self.updateWindowTitle(image_path)
        self.fitToWindow()

    def updateWindowTitle(self, image_path):
        """
        Update the window title using the image base name.
        """
        base_name = os.path.basename(image_path)
        self.setWindowTitle(f"Advanced Image Viewer - {base_name}")

    def zoomIn(self, mouse_pos=None):
        """
        Increase zoom by 20% and update the display.
        """
        if self.current_pixmap:
            self.zoom_level *= 1.2
            self.updateImageDisplay(mouse_pos)

    def zoomOut(self, mouse_pos=None):
        """
        Decrease zoom by 20%, ensuring a minimum zoom level, then update.
        """
        if self.current_pixmap:
            self.zoom_level /= 1.2
            if self.zoom_level < 0.1:
                self.zoom_level = 0.1
            self.updateImageDisplay(mouse_pos)

    def fitToWindow(self):
        """
        Adjust zoom level so the image fits within the viewport.
        """
        if self.current_pixmap:
            try:
                w_ratio = self.scroll_area.viewport().width() / self.current_pixmap.width()
                h_ratio = self.scroll_area.viewport().height() / self.current_pixmap.height()
                self.zoom_level = min(w_ratio, h_ratio)
                # Slight reduction to avoid overflow
                if self.zoom_level > 0.025:
                    self.zoom_level -= 0.025
                self.updateImageDisplay()
            except Exception as e:
                print(f"Error fitting image to window: {e}")

    def updateImageDisplay(self, mouse_pos=None):
        """
        Redraw the image based on current zoom level. Adjust scrollbars if mouse_pos provided.
        """
        if not self.current_pixmap:
            return

        old_size = self.image_label.size()
        new_width = int(self.current_pixmap.width() * self.zoom_level)
        new_height = int(self.current_pixmap.height() * self.zoom_level)

        scaled_pixmap = self.current_pixmap.scaled(
            new_width, new_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.adjustSize()

        # Adjust scrollbars based on mouse position for smooth panning effect
        if mouse_pos:
            new_size = self.image_label.size()
            delta_size = new_size - old_size
            scroll_bar_h = self.scroll_area.horizontalScrollBar()
            scroll_bar_v = self.scroll_area.verticalScrollBar()

            if old_size.width() != 0:
                scroll_bar_h.setValue(
                    scroll_bar_h.value() + delta_size.width() * mouse_pos.x() / old_size.width()
                )
            if old_size.height() != 0:
                scroll_bar_v.setValue(
                    scroll_bar_v.value() + delta_size.height() * mouse_pos.y() / old_size.height()
                )

    def wheelEvent(self, event: QWheelEvent):
        """
        Overridden wheel event to perform zooming.
        """
        mouse_pos = self.image_label.mapFromGlobal(event.globalPosition().toPoint())
        if event.angleDelta().y() > 0:
            self.zoomIn(mouse_pos)
        else:
            self.zoomOut(mouse_pos)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            self.panning = True
            self.pan_start_point = event.position()
            QApplication.setOverrideCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.panning:
            delta = event.position() - self.pan_start_point
            h_bar = self.scroll_area.horizontalScrollBar()
            v_bar = self.scroll_area.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())
            self.pan_start_point = event.position()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            self.panning = False
            QApplication.restoreOverrideCursor()

    def processAndPreviewImage(self, image_path, svg_icon_path, description_text, viewport_size=(1280,720)):
        """
        Process the image using preview_image() and display the result.
        Uses a dedicated 'Hammer5Tools' temporary subfolder.
        """
        # Create a dedicated subfolder for temporary files in the system temp directory
        temp_folder = os.path.join(tempfile.gettempdir(), "Hammer5Tools")
        os.makedirs(temp_folder, exist_ok=True)
        # Create a temporary file in the dedicated folder
        fd, temp_output = tempfile.mkstemp(dir=temp_folder, suffix=".png")
        os.close(fd)
        preview_image(image_path, svg_icon_path, description_text, temp_output, viewport_size)
        self.showImage(temp_output)
        # Cleanup: remove the temp file after loading
        try:
            os.remove(temp_output)
        except Exception as e:
            print(f"Error removing temp file '{temp_output}': {e}")

##############################################################################
# Explorer and Thumbnail Loading
##############################################################################

class ThumbnailWorkerSignals(QObject):
    result = Signal(str, QIcon)

class ThumbnailWorker(QRunnable):
    """
    Worker thread to generate a scaled thumbnail off the main thread.
    """
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.signals = ThumbnailWorkerSignals()

    def run(self):
        pixmap = QPixmap(self.file_path)
        if not pixmap.isNull():
            thumbnail = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon = QIcon(thumbnail)
            self.signals.result.emit(self.file_path, icon)

class QFileSystemModelWithThumbnails(QFileSystemModel):
    """
    Custom file system model that loads thumbnails asynchronously.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thumbnail_cache = {}
        self.thread_pool = QThreadPool()
        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(self.on_file_changed)

    def data(self, index, role=Qt.DisplayRole):
        if index.column() == 0 and role == Qt.DecorationRole:
            file_path = self.filePath(index)
            if not self.isDir(index):
                # Add file to watcher to detect changes
                if file_path not in self.watcher.files():
                    self.watcher.addPath(file_path)
                if file_path in self.thumbnail_cache:
                    return self.thumbnail_cache[file_path]
                self.load_thumbnail_async(file_path)
        return super().data(index, role)

    def load_thumbnail_async(self, file_path):
        worker = ThumbnailWorker(file_path)
        worker.signals.result.connect(self.on_thumbnail_loaded)
        self.thread_pool.start(worker)

    def on_thumbnail_loaded(self, file_path, icon):
        self.thumbnail_cache[file_path] = icon
        index = self.index(file_path)
        self.dataChanged.emit(index, index, [Qt.DecorationRole])

    def on_file_changed(self, file_path):
        if file_path in self.thumbnail_cache:
            del self.thumbnail_cache[file_path]
            self.load_thumbnail_async(file_path)
            index = self.index(file_path)
            self.dataChanged.emit(index, index, [Qt.DecorationRole])

class ImageExplorer(QMainWindow):
    """
    File explorer application with a tree view to select images and an
    embedded Viewport to display processed images.
    """
    def __init__(self, tree_directory=None):
        super().__init__()
        self.setWindowTitle("Explorer")
        root_path = tree_directory if tree_directory else os.path.expanduser("~")
        self.root_directory = root_path

        splitter = QSplitter(self)

        self.tree_view = QTreeView()
        self.tree_view.setIconSize(QSize(64, 64))

        self.file_model = QFileSystemModelWithThumbnails(self)
        self.file_model.setRootPath(root_path)
        self.file_model.setNameFilters(["*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif", "*.tga"])
        self.file_model.setNameFilterDisables(False)
        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(root_path))
        self.tree_view.clicked.connect(self.on_item_click)

        self.image_viewer = Viewport()

        splitter.addWidget(self.tree_view)
        splitter.addWidget(self.image_viewer)
        self.setCentralWidget(splitter)

        # Adjust tree view header
        self.tree_view.header().setDefaultSectionSize(120)
        self.tree_view.header().resizeSection(0, 160)
        self.tree_view.header().hideSection(1)
        self.tree_view.header().hideSection(2)
        self.tree_view.header().hideSection(3)

        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.openContextMenu)

        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """
        Accept drag events if files have valid image extensions.
        """
        if event.mimeData().hasUrls():
            valid_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga")
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    ext = os.path.splitext(url.toLocalFile())[1].lower()
                    if ext in valid_extensions:
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """
        Handle file drop events, copying images to the root directory.
        """
        if event.mimeData().hasUrls():
            copied_files = []
            valid_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga")
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    source_file = url.toLocalFile()
                    ext = os.path.splitext(source_file)[1].lower()
                    if ext in valid_extensions:
                        destination_file = os.path.join(self.root_directory, os.path.basename(source_file))
                        try:
                            shutil.copy(source_file, destination_file)
                            copied_files.append(destination_file)
                        except Exception as e:
                            print(f"Error copying file '{source_file}': {e}")

            if copied_files:
                self.file_model.refresh()
                self.image_viewer.processAndPreviewImage(copied_files[0], "", "Processed by Hammer5")
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def on_item_click(self, index):
        """
        Process and display the image when an item is clicked.
        """
        file_path = self.file_model.filePath(index)
        if not self.file_model.isDir(index):
            self.image_viewer.processAndPreviewImage(file_path, "", "Processed by Hammer5")

    def openContextMenu(self, position):
        """
        Open a context menu for file removal.
        """
        index = self.tree_view.indexAt(position)
        if not index.isValid():
            return
        file_path = self.file_model.filePath(index)
        if not self.file_model.isDir(index):
            menu = QMenu(self)
            remove_action = QAction("Remove", self)
            remove_action.triggered.connect(lambda: self.removeSelectedImage(file_path, index))
            menu.addAction(remove_action)
            menu.exec(self.tree_view.viewport().mapToGlobal(position))

    def removeSelectedImage(self, file_path, index):
        """
        Remove the selected image file.
        """
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                self.file_model.remove(index)
                self.image_viewer.set_placeholder_text()
                print(f"Removed image: {file_path}")
            except Exception as e:
                print(f"Error removing file '{file_path}': {e}")

##############################################################################
# Main Entry Point
##############################################################################

if __name__ == "__main__":
    app = QApplication(sys.argv)
    explorer = ImageExplorer()
    explorer.show()
    sys.exit(app.exec())