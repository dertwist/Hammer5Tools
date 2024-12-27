import sys
import os
from PySide6.QtCore import Qt, QSize, QThreadPool, QRunnable, QObject, Signal, QFileSystemWatcher, QPointF
from PySide6.QtGui import QPixmap, QIcon, QAction, QKeySequence, QWheelEvent, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTreeView,
    QFileSystemModel,
    QSplitter,
    QLabel,
    QScrollArea,
    QMenu,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QFrame
)

from src.widgets import exception_handler
from src.preferences import debug
from src.batch_creator.process import StartProcess


class AdvancedImageViewer(QMainWindow):
    def __init__(self, image_directory=None):
        super().__init__()
        self.initUI()
        self.current_image_index = -1
        self.image_files = []
        self.panning = False
        self.pan_start_point = QPointF(0, 0)
        if image_directory:
            self.loadImagesFromDirectory(image_directory)

    def initUI(self):
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)
        self.set_placeholder_text()

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.image_label)

        self.setCentralWidget(self.scroll_area)

        self.current_pixmap = None
        self.zoom_level = 1.0

    def set_placeholder_text(self):
        self.image_label.setText("Select image in the screenshots")
        self.image_label.setStyleSheet("color: gray; font-size: 16px;")
        self.image_label.setPixmap(QPixmap())

    def clear_placeholder_text(self):
        self.image_label.setText("")
        self.image_label.setStyleSheet("")

    def loadImagesFromDirectory(self, directory):
        valid_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga"]
        try:
            self.image_files = [
                os.path.join(directory, f)
                for f in os.listdir(directory)
                if os.path.splitext(f)[1].lower() in valid_extensions
            ]
            debug(f"Loaded {len(self.image_files)} images from {directory}.")
            if self.image_files:
                self.current_image_index = 0
                self.showImage(self.image_files[self.current_image_index])
            else:
                self.set_placeholder_text()
        except Exception as e:
            debug(f"Error loading images from directory '{directory}': {e}")
            self.set_placeholder_text()

    def showImage(self, image_path):
        try:
            self.current_pixmap = QPixmap(image_path)
            if not self.current_pixmap.isNull():
                self.clear_placeholder_text()
                self.image_label.setPixmap(self.current_pixmap)
                self.image_label.adjustSize()
                self.zoom_level = 1.0
                self.updateWindowTitle(image_path)
                debug(f"Displayed image: {image_path}")
            else:
                debug(f"Failed to load image: {image_path}")
                self.set_placeholder_text()
        except Exception as e:
            debug(f"Error displaying image '{image_path}': {e}")
            self.set_placeholder_text()

    def updateWindowTitle(self, image_path):
        self.setWindowTitle(f"Advanced Image Viewer - {os.path.basename(image_path)}")

    def zoomIn(self):
        if self.current_pixmap:
            self.zoom_level *= 1.2
            self.updateImageDisplay()

    def zoomOut(self):
        if self.current_pixmap:
            self.zoom_level /= 1.2
            self.updateImageDisplay()

    def fitToWindow(self):
        if self.current_pixmap:
            try:
                self.zoom_level = min(
                    self.scroll_area.viewport().width() / self.current_pixmap.width(),
                    self.scroll_area.viewport().height() / self.current_pixmap.height()
                ) - 0.025
                self.updateImageDisplay()
            except Exception as e:
                debug(f"Error fitting image to window: {e}")

    def updateImageDisplay(self):
        if self.current_pixmap:
            try:
                scaled_pixmap = self.current_pixmap.scaled(
                    self.current_pixmap.size() * self.zoom_level,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.adjustSize()
                debug(f"Updated image display with zoom level: {self.zoom_level}")
            except Exception as e:
                debug(f"Error updating image display: {e}")

    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            self.zoomIn()
        else:
            self.zoomOut()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            self.panning = True
            self.pan_start_point = event.position()
            QApplication.setOverrideCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.panning:
            delta = event.position() - self.pan_start_point
            self.scroll_area.horizontalScrollBar().setValue(
                self.scroll_area.horizontalScrollBar().value() - delta.x()
            )
            self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().value() - delta.y()
            )
            self.pan_start_point = event.position()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            self.panning = False
            QApplication.restoreOverrideCursor()


class ThumbnailWorkerSignals(QObject):
    result = Signal(str, QIcon)


class ThumbnailWorker(QRunnable):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.signals = ThumbnailWorkerSignals()

    def run(self):
        try:
            pixmap = QPixmap(self.file_path)
            if not pixmap.isNull():
                thumbnail = pixmap.scaled(
                    128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                icon = QIcon(thumbnail)
                self.signals.result.emit(self.file_path, icon)
            else:
                debug(f"Failed to generate thumbnail for: {self.file_path}")
        except Exception as e:
            debug(f"Error generating thumbnail for '{self.file_path}': {e}")


class QFileSystemModelWithThumbnails(QFileSystemModel):
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
                if file_path not in self.watcher.files():
                    self.watcher.addPath(file_path)
                    debug(f"Added watcher for file: {file_path}")

                if file_path in self.thumbnail_cache:
                    return self.thumbnail_cache[file_path]
                else:
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
        debug(f"Loaded thumbnail for: {file_path}")

    def on_file_changed(self, file_path):
        if file_path in self.thumbnail_cache:
            del self.thumbnail_cache[file_path]
            self.load_thumbnail_async(file_path)
            index = self.index(file_path)
            self.dataChanged.emit(index, index, [Qt.DecorationRole])
            debug(f"Updated thumbnail for changed file: {file_path}")


class ExplorerImageViewer(QMainWindow):
    def __init__(self, tree_directory=None):
        super().__init__()
        self.setWindowTitle("Explorer")

        splitter = QSplitter(self)

        self.tree_view = QTreeView()
        self.tree_view.setIconSize(QSize(64, 64))

        self.file_model = QFileSystemModelWithThumbnails(self)
        root_path = tree_directory if tree_directory else os.path.expanduser("~")
        self.file_model.setRootPath(root_path)
        self.file_model.setNameFilters(["*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif", "*.tga"])
        self.file_model.setNameFilterDisables(False)

        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(root_path))
        self.tree_view.clicked.connect(self.on_item_click)

        self.image_viewer = AdvancedImageViewer()

        splitter.addWidget(self.tree_view)
        splitter.addWidget(self.image_viewer)

        self.setCentralWidget(splitter)

        self.tree_view.header().setDefaultSectionSize(120)
        self.tree_view.header().resizeSection(0, 160)
        self.tree_view.header().hideSection(1)
        self.tree_view.header().hideSection(2)
        self.tree_view.header().hideSection(3)

        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.openContextMenu)

    def on_item_click(self, index):
        file_path = self.file_model.filePath(index)
        if not self.file_model.isDir(index):
            self.image_viewer.showImage(file_path)
            self.image_viewer.fitToWindow()

    def openContextMenu(self, position):
        index = self.tree_view.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu(self)
        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(lambda: self.removeSelectedImage(index))
        menu.addAction(remove_action)

        menu.exec(self.tree_view.viewport().mapToGlobal(position))

    def removeSelectedImage(self, index):
        file_path = self.file_model.filePath(index)
        if not self.file_model.isDir(index):
            try:
                os.remove(file_path)
                self.file_model.remove(index)
                self.image_viewer.set_placeholder_text()
                self.setWindowTitle("Explorer")
                debug(f"Removed image: {file_path}")
            except Exception as e:
                debug(f"Error removing file '{file_path}': {e}")