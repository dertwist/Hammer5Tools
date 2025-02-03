import os
import shutil
from PySide6.QtCore import Qt, QSize, QThreadPool, QRunnable, QObject, Signal, QFileSystemWatcher, QPointF
from PySide6.QtGui import QPixmap, QIcon, QAction, QWheelEvent, QMouseEvent, QDragEnterEvent, QDropEvent
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
    QVBoxLayout
)
from src.settings.main import debug
from src.loading_editor.preview import preview_image

class NoWheelScrollArea(QScrollArea):
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()

class Viewport(QMainWindow):
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

        self.placeholder_label = QLabel(self.container)
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setText("Select image in the screenshots")
        self.placeholder_label.setStyleSheet("color: gray; font-size: 13px;")

        self.image_label = QLabel(self.container)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)

        self.scroll_area = NoWheelScrollArea(self.container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout.addWidget(self.placeholder_label)
        layout.addWidget(self.scroll_area)

        self.placeholder_label.show()
        self.scroll_area.hide()

    def set_placeholder_text(self):
        self.placeholder_label.setText("Select image in the screenshots")
        self.placeholder_label.setStyleSheet("color: gray; font-size: 16px;")
        self.placeholder_label.show()
        self.scroll_area.hide()
        self.image_label.clear()

    def clear_placeholder_text(self):
        self.placeholder_label.hide()
        self.placeholder_label.clear()
        self.placeholder_label.setStyleSheet("")
        self.scroll_area.show()

    def loadImagesFromDirectory(self, directory):
        valid_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga"]
        try:
            self.image_files = [
                os.path.join(directory, f)
                for f in os.listdir(directory)
                if os.path.splitext(f)[1].lower() in valid_extensions
            ]
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
            else:
                self.set_placeholder_text()
        except Exception as e:
            debug(f"Error displaying image '{image_path}': {e}")
            self.set_placeholder_text()

    def updateWindowTitle(self, image_path):
        self.setWindowTitle(f"Advanced Image Viewer - {os.path.basename(image_path)}")

    def zoomIn(self, mouse_pos=None):
        if self.current_pixmap:
            self.zoom_level *= 1.2
            self.updateImageDisplay(mouse_pos)

    def zoomOut(self, mouse_pos=None):
        if self.current_pixmap:
            self.zoom_level /= 1.2
            self.updateImageDisplay(mouse_pos)

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

    def updateImageDisplay(self, mouse_pos=None):
        if self.current_pixmap:
            try:
                old_size = self.image_label.size()
                scaled_pixmap = self.current_pixmap.scaled(
                    self.current_pixmap.size() * self.zoom_level,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.adjustSize()

                if mouse_pos:
                    new_size = self.image_label.size()
                    delta_size = new_size - old_size
                    scroll_bar_h = self.scroll_area.horizontalScrollBar()
                    scroll_bar_v = self.scroll_area.verticalScrollBar()

                    scroll_bar_h.setValue(
                        scroll_bar_h.value() + delta_size.width() * mouse_pos.x() / old_size.width()
                    )
                    scroll_bar_v.setValue(
                        scroll_bar_v.value() + delta_size.height() * mouse_pos.y() / old_size.height()
                    )
            except Exception as e:
                debug(f"Error updating image display: {e}")

    def wheelEvent(self, event: QWheelEvent):
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
            self.scroll_area.horizontalScrollBar().setValue(
                self.scroll_area.horizontalScrollBar().value() - delta.x()
            )
            self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().value() - delta.y()
            )
            self.pan_start_point = event.position()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            self.panning = False
            QApplication.restoreOverrideCursor()

    def processAndPreviewImage(self, image_path, svg_icon_path, description_text, output_path, viewport_size=(1280, 720)):
        preview_image(image_path, svg_icon_path, description_text, output_path, viewport_size)
        self.showImage(output_path)
        self.fitToWindow()

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    explorer = ImageExplorer()
    explorer.show()
    sys.exit(app.exec())

class ImageExplorer(QMainWindow):
    def __init__(self, tree_directory=None):
        super().__init__()
        self.setWindowTitle("Explorer")
        root_path = tree_directory if tree_directory else os.path.expanduser("~")
        self.root_directory = root_path  # Save the root path for copying files

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

        self.tree_view.header().setDefaultSectionSize(120)
        self.tree_view.header().resizeSection(0, 160)
        self.tree_view.header().hideSection(1)
        self.tree_view.header().hideSection(2)
        self.tree_view.header().hideSection(3)

        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.openContextMenu)

        # Enable drag and drop support
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            valid_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga")
            for url in event.mimeData().urls():
                if url.isLocalFile() and os.path.splitext(url.toLocalFile())[1].lower() in valid_extensions:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            valid_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga")
            copied_files = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    source_file = url.toLocalFile()
                    ext = os.path.splitext(source_file)[1].lower()
                    if ext in valid_extensions:
                        destination_file = os.path.join(self.root_directory, os.path.basename(source_file))
                        try:
                            shutil.copy(source_file, destination_file)
                            copied_files.append(destination_file)
                            debug(f"Copied file {source_file} to {destination_file}")
                        except Exception as e:
                            debug(f"Error copying file '{source_file}': {e}")
            if copied_files:
                # Refresh the model to show new files
                self.file_model.refresh()
                # Optionally, display the first copied image
                self.image_viewer.showImage(copied_files[0])
                self.image_viewer.fitToWindow()
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

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
                    128, 128,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
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

if __name__ == "__main__":
    # Example usage for testing ImageExplorer
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    explorer = ImageExplorer()
    explorer.show()
    sys.exit(app.exec())