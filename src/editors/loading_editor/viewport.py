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
import sys

class NoWheelScrollArea(QScrollArea):
    """
    Custom scroll area that ignores wheel events to delegate zooming to the main viewport instead.
    """
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()

class Viewport(QMainWindow):
    """
    A QMainWindow subclass providing an image-viewing area with zoom, panning,
    and the ability to process images before displaying them.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.panning = False
        self.pan_start_point = QPointF(0, 0)
        self.current_pixmap = None
        self.zoom_level = 1.0
        self.image_files = []
        self.current_image_index = 0
        
        # Saved camera state - shared across all images
        self.saved_zoom_level = None
        self.saved_h_scroll = None
        self.saved_v_scroll = None
        self.current_image_path = None

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
        """
        Show a placeholder label and hide the scroll area when no valid image is loaded.
        """
        self.placeholder_label.setText("Select image in the screenshots")
        self.placeholder_label.setStyleSheet("color: gray; font-size: 16px;")
        self.placeholder_label.show()
        self.scroll_area.hide()
        self.image_label.clear()

    def clear_placeholder_text(self):
        """
        Clear placeholder text and reveal the scroll area when a valid image is displayed.
        """
        self.placeholder_label.hide()
        self.placeholder_label.clear()
        self.placeholder_label.setStyleSheet("")
        self.scroll_area.show()

    def loadImagesFromDirectory(self, directory):
        """
        Load all valid images from the specified directory into a list
        and display the first image if available.
        """
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
        """
        Load a QPixmap from the given path and display it in the label.
        Maintains the current camera position when switching images.
        """
        try:
            # Save current camera position before switching
            if self.current_pixmap:
                self.saveCameraPosition()
            
            # Store the current zoom and scroll positions
            current_zoom = self.zoom_level
            current_h_scroll = self.scroll_area.horizontalScrollBar().value() if self.current_pixmap else None
            current_v_scroll = self.scroll_area.verticalScrollBar().value() if self.current_pixmap else None
            
            self.current_pixmap = QPixmap(image_path)
            if not self.current_pixmap.isNull():
                self.clear_placeholder_text()
                self.image_label.setPixmap(self.current_pixmap)
                self.current_image_path = image_path
                self.updateWindowTitle(image_path)
                
                # If we had a previous image, maintain the camera position
                if current_h_scroll is not None:
                    # Restore the zoom level
                    self.zoom_level = current_zoom
                    self.updateImageDisplay(save_position=False)
                    
                    # Restore scroll positions after processing events
                    QApplication.processEvents()
                    self.scroll_area.horizontalScrollBar().setValue(current_h_scroll)
                    self.scroll_area.verticalScrollBar().setValue(current_v_scroll)
                    
                    debug(f"Maintained camera position for {os.path.basename(image_path)} - Zoom: {current_zoom}")
                else:
                    # First image, check if we have a saved position
                    if self.saved_zoom_level is not None:
                        self.zoom_level = self.saved_zoom_level
                        self.updateImageDisplay(save_position=False)
                        
                        QApplication.processEvents()
                        if self.saved_h_scroll is not None:
                            self.scroll_area.horizontalScrollBar().setValue(self.saved_h_scroll)
                        if self.saved_v_scroll is not None:
                            self.scroll_area.verticalScrollBar().setValue(self.saved_v_scroll)
                    else:
                        # No saved position, fit to window
                        self.zoom_level = 1.0
                        self.fitToWindow()
            else:
                self.set_placeholder_text()
        except Exception as e:
            debug(f"Error displaying image '{image_path}': {e}")
            self.set_placeholder_text()

    def updateWindowTitle(self, image_path):
        """
        Update the main window title bar with the base name of the displayed image.
        """
        self.setWindowTitle(f"Advanced Image Viewer - {os.path.basename(image_path)}")

    def zoomIn(self, mouse_pos=None):
        """
        Zoom in by 20%. Optionally keep the zoom focus around a specific mouse position.
        """
        if self.current_pixmap:
            self.zoom_level *= 1.2
            self.updateImageDisplay(mouse_pos)

    def zoomOut(self, mouse_pos=None):
        """
        Zoom out by 20%. Optionally keep the zoom focus around a specific mouse position.
        """
        if self.current_pixmap:
            self.zoom_level /= 1.2
            if self.zoom_level < 0.1:
                self.zoom_level = 0.1
            self.updateImageDisplay(mouse_pos)

    def fitToWindow(self):
        """
        Fit the current image to the window for a convenient view.
        """
        if self.current_pixmap:
            try:
                w_ratio = self.scroll_area.viewport().width() / self.current_pixmap.width()
                h_ratio = self.scroll_area.viewport().height() / self.current_pixmap.height()
                self.zoom_level = min(w_ratio, h_ratio)
                # Slight offset to avoid accidental scrollbars.
                self.zoom_level = self.zoom_level - 0.025 if self.zoom_level > 0.025 else self.zoom_level
                self.updateImageDisplay()
            except Exception as e:
                debug(f"Error fitting image to window: {e}")

    def updateImageDisplay(self, mouse_pos=None, save_position=True):
        """
        Scale the displayed pixmap according to the current zoom_level.
        If a mouse_pos is provided, keep the scroll offset around that position.
        """
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
                
                # Auto-save camera position after zoom (if enabled)
                if save_position:
                    self.saveCameraPosition()
            except Exception as e:
                debug(f"Error updating image display: {e}")

    def wheelEvent(self, event: QWheelEvent):
        """
        Override the main window wheel event to provide zooming
        using the wheel, based on scroll direction.
        """
        mouse_pos = self.image_label.mapFromGlobal(event.globalPosition().toPoint())
        if event.angleDelta().y() > 0:
            self.zoomIn(mouse_pos)
        else:
            self.zoomOut(mouse_pos)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        """
        Activate panning when the user right-clicks inside the viewer.
        """
        if event.button() == Qt.RightButton:
            self.panning = True
            self.pan_start_point = event.position()
            QApplication.setOverrideCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        """
        On mouse move, shift the scrollbars to implement manual panning.
        """
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
        """
        Disable panning when the user releases the right mouse button.
        """
        if event.button() == Qt.RightButton:
            self.panning = False
            QApplication.restoreOverrideCursor()
            # Save camera position after panning
            self.saveCameraPosition()
    
    def saveCameraPosition(self):
        """
        Save the current camera position (shared across all images).
        """
        if self.current_pixmap:
            self.saved_zoom_level = self.zoom_level
            self.saved_h_scroll = self.scroll_area.horizontalScrollBar().value()
            self.saved_v_scroll = self.scroll_area.verticalScrollBar().value()
            debug(f"Saved shared camera position - Zoom: {self.saved_zoom_level}, H: {self.saved_h_scroll}, V: {self.saved_v_scroll}")
    
    def restoreCameraPosition(self):
        """
        Restore the saved camera position (shared across all images).
        """
        if self.current_pixmap and self.saved_zoom_level is not None:
            # Restore zoom level without saving position again
            self.zoom_level = self.saved_zoom_level
            self.updateImageDisplay(save_position=False)
            
            # Restore scroll positions after processing events
            QApplication.processEvents()
            
            if self.saved_h_scroll is not None:
                self.scroll_area.horizontalScrollBar().setValue(self.saved_h_scroll)
            if self.saved_v_scroll is not None:
                self.scroll_area.verticalScrollBar().setValue(self.saved_v_scroll)
                
            debug(f"Restored shared camera position - Zoom: {self.saved_zoom_level}, H: {self.saved_h_scroll}, V: {self.saved_v_scroll}")

class ImageExplorer(QMainWindow):
    """
    A simple file explorer with a tree view and an embedded Viewport to show images.
    Supports drag/drop for new images.
    Now supports removing folders and displays smaller icons for folders.
    """
    FOLDER_ICON_SIZE = QSize(32, 32)
    FILE_ICON_SIZE = QSize(32, 32)

    def __init__(self, tree_directory=None):
        super().__init__()
        self.setWindowTitle("Explorer")
        root_path = tree_directory if tree_directory else os.path.expanduser("~")
        self.root_directory = root_path

        splitter = QSplitter(self)

        self.tree_view = QTreeView()
        self.tree_view.setIconSize(self.FILE_ICON_SIZE)

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

        # Set a delegate to adjust folder icon size
        self.tree_view.setItemDelegate(FolderIconSizeDelegate(self.file_model, self.FOLDER_ICON_SIZE, self.FILE_ICON_SIZE, self.tree_view))

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
                self.file_model.refresh()
                # Display the first copied image
                self.image_viewer.showImage(copied_files[0])
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def on_item_click(self, index):
        file_path = self.file_model.filePath(index)
        if not self.file_model.isDir(index):
            self.image_viewer.showImage(file_path)

    def openContextMenu(self, position):
        index = self.tree_view.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu(self)
        if self.file_model.isDir(index):
            remove_action = QAction("Remove Folder", self)
            remove_action.triggered.connect(lambda: self.removeSelectedFolder(index))
            menu.addAction(remove_action)
        else:
            remove_action = QAction("Remove Image", self)
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

    def removeSelectedFolder(self, index):
        folder_path = self.file_model.filePath(index)
        if self.file_model.isDir(index):
            try:
                shutil.rmtree(folder_path)
                self.file_model.remove(index)
                self.image_viewer.set_placeholder_text()
                self.setWindowTitle("Explorer")
                debug(f"Removed folder: {folder_path}")
            except Exception as e:
                debug(f"Error removing folder '{folder_path}': {e}")

from PySide6.QtWidgets import QStyledItemDelegate
from PySide6.QtCore import QSize

class FolderIconSizeDelegate(QStyledItemDelegate):
    """
    Custom delegate to set a smaller icon size for folders in the tree view.
    """
    def __init__(self, model, folder_icon_size, file_icon_size, parent=None):
        super().__init__(parent)
        self.model = model
        self.folder_icon_size = folder_icon_size
        self.file_icon_size = file_icon_size

    def sizeHint(self, option, index):
        if self.model.isDir(index):
            return self.folder_icon_size
        return self.file_icon_size

class ThumbnailWorkerSignals(QObject):
    result = Signal(str, QIcon)

class ThumbnailWorker(QRunnable):
    """
    Worker thread that loads and scales a thumbnail off the main thread.
    """
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.signals = ThumbnailWorkerSignals()

    def run(self):
        try:
            pixmap = QPixmap(self.file_path)
            if not pixmap.isNull():
                thumbnail = pixmap.scaled(
                    128,
                    128,
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
    """
    Custom QFileSystemModel that loads thumbnails asynchronously and updates the model.
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
    app = QApplication(sys.argv)
    explorer = ImageExplorer()
    explorer.show()
    sys.exit(app.exec())