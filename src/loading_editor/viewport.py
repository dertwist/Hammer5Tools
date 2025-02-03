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
import io
from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageOps

try:
    from cairosvg import svg2png
except ImportError:
    svg2png = None
    print("Error: cairosvg module is required for SVG conversion. Please install it using 'pip install cairosvg'.")

def load_svg_as_image(svg_path, target_width):
    """
    Convert an SVG file to a PIL Image resized to target_width while preserving its aspect ratio.
    """
    if not os.path.exists(svg_path):
        print(f"SVG icon not found: {svg_path}")
        return None
    if svg2png is None:
        print("cairosvg is required to convert SVG to PNG.")
        return None
    try:
        png_data = svg2png(url=svg_path, output_width=target_width)
        icon = Image.open(io.BytesIO(png_data))
        if icon.mode != "RGBA":
            icon = icon.convert("RGBA")
        return icon
    except Exception as e:
        print(f"Error converting SVG: {e}")
        return None

def preview_image(image_path, svg_icon_path, description_text, output_path, viewport_size=(1280, 720)):
    """
    Processes and annotates the image, then saves a final version to output_path.
    """
    if not os.path.exists(image_path):
        print(f"Input image not found: {image_path}")
        return

    try:
        image = Image.open(image_path).convert("RGBA")
    except Exception as e:
        print(f"Failed to load image: {image_path}, error: {e}")
        return

    # Resize image to fit within viewport while preserving aspect ratio.
    image = ImageOps.contain(image, viewport_size)
    width, height = image.size

    # Define a blurred rectangle area on the right side.
    rect_left   = int(width * 0.87)
    rect_top    = int(height * 0.05)
    rect_right  = int(width * 0.96)
    rect_bottom = int(height * 0.95)
    region_width = rect_right - rect_left
    region_height = rect_bottom - rect_top

    if region_width <= 0 or region_height <= 0:
        print("Invalid rectangle dimensions calculated.")
        return

    region = image.crop((rect_left, rect_top, rect_right, rect_bottom))
    blurred_region = region.filter(ImageFilter.GaussianBlur(radius=5))
    image.paste(blurred_region, (rect_left, rect_top))

    # Load and place SVG icon if present.
    max_icon_width = int(region_width * 0.8)
    icon = load_svg_as_image(svg_icon_path, max_icon_width)
    if icon is None:
        print("Failed to load SVG icon.")
        return

    icon_width, icon_height = icon.size
    icon_x = rect_left + (region_width - icon_width) // 2
    icon_padding_top = 10
    icon_y = rect_top + icon_padding_top
    image.paste(icon, (icon_x, icon_y), icon)

    # Draw text annotations.
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()

    label_text = "Casual"
    text_width, text_height = draw.textsize(label_text, font=font)
    label_x = rect_left + (region_width - text_width) // 2
    label_y = icon_y + icon_height + 5
    draw.text((label_x, label_y), label_text, font=font, fill="white")

    # Divider line
    divider_padding = 10
    divider_y = label_y + text_height + divider_padding
    draw.line((rect_left + 5, divider_y, rect_right - 5, divider_y), fill="gray", width=2)

    # Static text "test"
    test_padding = 10
    test_y = divider_y + test_padding + text_height
    draw.text((rect_left + 10, test_y), "test", font=font, fill="white")

    # Description text
    base_text = "A community map created by:"
    combined_text = f"{base_text} {description_text}"
    desc_padding = 10
    desc_y = test_y + text_height + desc_padding
    draw.text((rect_left + 10, desc_y), combined_text, font=font_small, fill="white")

    # Save to output_path
    try:
        image.save(output_path)
        print(f"Processed image saved to: {output_path}")
    except Exception as e:
        print(f"Error saving processed image to: {output_path}, error: {e}")

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
        Automatically fits the image to the window for better viewing.
        """
        try:
            self.current_pixmap = QPixmap(image_path)
            if not self.current_pixmap.isNull():
                self.clear_placeholder_text()
                self.image_label.setPixmap(self.current_pixmap)
                # Reset zoom whenever a new image is loaded.
                self.zoom_level = 1.0
                self.updateWindowTitle(image_path)
                # Automatically fit to window for improved preview.
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

    def updateImageDisplay(self, mouse_pos=None):
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

    def processAndPreviewImage(self, image_path, svg_icon_path, description_text, output_path, viewport_size=(1280, 720)):
        """
        Process the image externally using 'preview_image' (adds icon & text),
        then display the processed file.
        """
        preview_image(image_path, svg_icon_path, description_text, output_path, viewport_size)
        self.showImage(output_path)

class ImageExplorer(QMainWindow):
    """
    A simple file explorer with a tree view and an embedded Viewport to show images.
    Supports drag/drop for new images.
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