import os
import shutil
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple
from PIL import Image
import re

from PySide6.QtCore import Qt, QSize, QThreadPool, QRunnable, QObject, Signal, QTimer
from PySide6.QtGui import QPixmap, QIcon, QAction, QFont
from PySide6.QtWidgets import QStyle
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTreeWidget,
    QTreeWidgetItem,
    QSplitter,
    QLabel,
    QScrollArea,
    QMenu,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
    QProgressDialog,
    QFileDialog
)
from src.settings.main import debug

class TimelineExportSignals(QObject):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

class TimelineExportWorker(QRunnable):
    """Worker thread for exporting timeline sequences to GIF"""
    def __init__(self, camera_name: str, image_paths: List[str], output_path: str):
        super().__init__()
        self.camera_name = camera_name
        self.image_paths = image_paths
        self.output_path = output_path
        self.signals = TimelineExportSignals()

    def run(self):
        try:
            if not self.image_paths:
                self.signals.error.emit("No images to export")
                return

            images = []
            total_images = len(self.image_paths)
            
            # First pass: determine the maximum resolution
            max_width, max_height = 0, 0
            for image_path in self.image_paths:
                try:
                    with Image.open(image_path) as img:
                        max_width = max(max_width, img.width)
                        max_height = max(max_height, img.height)
                except Exception as e:
                    debug(f"Error checking image size {image_path}: {e}")
                    continue
            
            if max_width == 0 or max_height == 0:
                self.signals.error.emit("No valid images found")
                return
            
            # Second pass: load and resize images
            for i, image_path in enumerate(self.image_paths):
                try:
                    img = Image.open(image_path)
                    
                    # Resize to maximum resolution if needed
                    if img.width != max_width or img.height != max_height:
                        img = img.resize((max_width, max_height), Image.Resampling.LANCZOS)
                    
                    # Convert to RGB if necessary (GIF doesn't support RGBA)
                    if img.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'RGBA':
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img, mask=img.split()[-1])
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    images.append(img)
                    progress = int((i + 1) / total_images * 90)  # 90% for loading images
                    self.signals.progress.emit(progress)
                except Exception as e:
                    debug(f"Error loading image {image_path}: {e}")
                    continue

            if not images:
                self.signals.error.emit("No valid images could be loaded")
                return

            # Save as GIF
            gif_path = os.path.join(self.output_path, f"{self.camera_name}_timeline.gif")
            images[0].save(
                gif_path,
                save_all=True,
                append_images=images[1:],
                duration=500,  # 500ms per frame
                loop=0
            )
            
            self.signals.progress.emit(100)
            self.signals.finished.emit(gif_path)
            
        except Exception as e:
            self.signals.error.emit(f"Error creating GIF: {str(e)}")

class TimelineTreeWidget(QTreeWidget):
    """Custom tree widget for timeline view with thumbnail support"""
    
    image_selected = Signal(str)  # Signal emitted when an image is selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Timeline")
        self.setIconSize(QSize(32, 32))
        self.setIndentation(20)
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Connect item selection
        self.itemClicked.connect(self.on_item_clicked)
        
        # Thread pool for thumbnail generation
        self.thread_pool = QThreadPool()
        self.thumbnail_cache = {}
        
        # Timer for delayed thumbnail loading
        self.thumbnail_timer = QTimer()
        self.thumbnail_timer.setSingleShot(True)
        self.thumbnail_timer.timeout.connect(self.load_pending_thumbnails)
        self.pending_thumbnails = []

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click - emit signal if it's an image item"""
        if hasattr(item, 'image_path'):
            self.image_selected.emit(item.image_path)

    def show_context_menu(self, position):
        """Show context menu for timeline items"""
        item = self.itemAt(position)
        if not item:
            return
            
        menu = QMenu(self)
        
        if hasattr(item, 'camera_name'):  # Camera folder
            export_action = QAction("Export to GIF", self)
            export_action.triggered.connect(lambda: self.export_camera_to_gif(item))
            menu.addAction(export_action)
        elif hasattr(item, 'image_path'):  # Image item
            show_action = QAction("Show in Viewport", self)
            show_action.triggered.connect(lambda: self.image_selected.emit(item.image_path))
            menu.addAction(show_action)
            
            open_folder_action = QAction("Open Containing Folder", self)
            open_folder_action.triggered.connect(lambda: self.open_containing_folder(item.image_path))
            menu.addAction(open_folder_action)
        
        if menu.actions():
            menu.exec(self.mapToGlobal(position))

    def open_containing_folder(self, image_path: str):
        """Open the folder containing the image"""
        folder_path = os.path.dirname(image_path)
        if os.path.exists(folder_path):
            os.startfile(folder_path)

    def export_camera_to_gif(self, camera_item: QTreeWidgetItem):
        """Export all images for a camera to GIF format"""
        if not hasattr(camera_item, 'camera_name'):
            return
            
        # Collect all image paths for this camera
        image_paths = []
        for i in range(camera_item.childCount()):
            child = camera_item.child(i)
            if hasattr(child, 'image_path'):
                image_paths.append(child.image_path)
        
        if not image_paths:
            QMessageBox.warning(self, "Export Error", "No images found for this camera.")
            return
        
        # Sort by timestamp (oldest first)
        image_paths.sort(key=lambda x: self.extract_timestamp_from_path(x))
        
        # Ask user for output directory
        output_dir = QFileDialog.getExistingDirectory(
            self, 
            "Select Output Directory", 
            os.path.expanduser("~/Desktop")
        )
        
        if not output_dir:
            return
        
        # Create progress dialog
        progress_dialog = QProgressDialog("Exporting to GIF...", "Cancel", 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        # Create worker
        worker = TimelineExportWorker(camera_item.camera_name, image_paths, output_dir)
        worker.signals.progress.connect(progress_dialog.setValue)
        worker.signals.finished.connect(lambda path: self.on_export_finished(progress_dialog, path))
        worker.signals.error.connect(lambda error: self.on_export_error(progress_dialog, error))
        
        # Connect cancel button
        progress_dialog.canceled.connect(lambda: self.thread_pool.clear())
        
        # Start export
        self.thread_pool.start(worker)

    def on_export_finished(self, progress_dialog: QProgressDialog, gif_path: str):
        """Handle successful GIF export"""
        progress_dialog.close()
        QMessageBox.information(
            self, 
            "Export Complete", 
            f"GIF exported successfully to:\n{gif_path}"
        )

    def on_export_error(self, progress_dialog: QProgressDialog, error: str):
        """Handle GIF export error"""
        progress_dialog.close()
        QMessageBox.critical(self, "Export Error", f"Failed to export GIF:\n{error}")

    def extract_timestamp_from_path(self, image_path: str) -> datetime:
        """Extract timestamp from image path"""
        # Extract timestamp from folder name (e.g., "2025-06-14_18-28-36")
        folder_name = os.path.basename(os.path.dirname(image_path))
        try:
            return datetime.strptime(folder_name, "%Y-%m-%d_%H-%M-%S")
        except ValueError:
            return datetime.min

    def load_timeline_data(self, history_path: str):
        """Load timeline data from History folder"""
        self.clear()
        self.thumbnail_cache.clear()
        
        if not os.path.exists(history_path):
            debug(f"History path does not exist: {history_path}")
            return
        
        # Group images by camera name
        camera_data = defaultdict(list)
        
        try:
            # Iterate through timestamp folders
            for timestamp_folder in os.listdir(history_path):
                timestamp_path = os.path.join(history_path, timestamp_folder)
                if not os.path.isdir(timestamp_path):
                    continue
                
                # Parse timestamp
                try:
                    timestamp = datetime.strptime(timestamp_folder, "%Y-%m-%d_%H-%M-%S")
                except ValueError:
                    debug(f"Invalid timestamp folder format: {timestamp_folder}")
                    continue
                
                # Find images in this timestamp folder
                for filename in os.listdir(timestamp_path):
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tga')):
                        # Extract camera name from filename (e.g., "CT Spawn_0000.jpg" -> "CT Spawn")
                        camera_name = self.extract_camera_name(filename)
                        if camera_name:
                            image_path = os.path.join(timestamp_path, filename)
                            camera_data[camera_name].append((timestamp, image_path))
        
        except Exception as e:
            debug(f"Error loading timeline data: {e}")
            return
        
        # Create tree structure
        for camera_name, images in camera_data.items():
            # Sort images by timestamp (oldest first)
            images.sort(key=lambda x: x[0])
            
            # Create camera folder item
            camera_item = QTreeWidgetItem(self)
            camera_item.setText(0, f"{camera_name} ({len(images)} images)")
            camera_item.camera_name = camera_name
            camera_item.setExpanded(False)
            
            # Set folder icon - use a simple folder icon
            try:
                camera_item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
            except AttributeError:
                # Fallback: create a simple folder icon from text
                folder_icon = QIcon()
                camera_item.setIcon(0, folder_icon)
            
            # Add image items
            for timestamp, image_path in images:
                image_item = QTreeWidgetItem(camera_item)
                image_item.setText(0, timestamp.strftime("%Y-%m-%d %H:%M:%S"))
                image_item.image_path = image_path
                image_item.timestamp = timestamp
                
                # Schedule thumbnail loading
                self.schedule_thumbnail_load(image_item, image_path)
        
        debug(f"Loaded timeline data: {len(camera_data)} cameras")

    def extract_camera_name(self, filename: str) -> str:
        """Extract camera name from filename, treating different numbered cameras as separate"""
        # Remove extension
        base_name = os.path.splitext(filename)[0]

        # Extract camera name and number (e.g., "Site_0000" -> "Site", "Site_0001" -> "Site 1")
        match = re.match(r'^(.+?)_(\d+)$', base_name)
        if match:
            camera_base = match.group(1)
            camera_number = int(match.group(2))
            
            if camera_number == 0:
                return camera_base  # "Site_0000" -> "Site"
            else:
                return f"{camera_base} {camera_number}"  # "Site_0001" -> "Site 1"

        # If no underscore pattern, return the base name
        return base_name

    def schedule_thumbnail_load(self, item: QTreeWidgetItem, image_path: str):
        """Schedule thumbnail loading for an item"""
        self.pending_thumbnails.append((item, image_path))
        self.thumbnail_timer.start(100)  # Delay to batch thumbnail loading

    def load_pending_thumbnails(self):
        """Load thumbnails for pending items"""
        if not self.pending_thumbnails:
            return
        
        # Process a batch of thumbnails
        batch_size = 5
        batch = self.pending_thumbnails[:batch_size]
        self.pending_thumbnails = self.pending_thumbnails[batch_size:]
        
        for item, image_path in batch:
            if image_path not in self.thumbnail_cache:
                worker = ThumbnailWorker(image_path, item)
                worker.signals.result.connect(self.on_thumbnail_loaded)
                self.thread_pool.start(worker)
        
        # Schedule next batch if there are more pending
        if self.pending_thumbnails:
            self.thumbnail_timer.start(100)

    def on_thumbnail_loaded(self, image_path: str, icon: QIcon, item: QTreeWidgetItem):
        """Handle thumbnail loaded"""
        self.thumbnail_cache[image_path] = icon
        if item and not item.isHidden():
            item.setIcon(0, icon)

class ThumbnailWorkerSignals(QObject):
    result = Signal(str, QIcon, QTreeWidgetItem)

class ThumbnailWorker(QRunnable):
    """Worker thread for loading thumbnails"""
    def __init__(self, image_path: str, item: QTreeWidgetItem):
        super().__init__()
        self.image_path = image_path
        self.item = item
        self.signals = ThumbnailWorkerSignals()

    def run(self):
        try:
            pixmap = QPixmap(self.image_path)
            if not pixmap.isNull():
                thumbnail = pixmap.scaled(
                    64, 64,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                icon = QIcon(thumbnail)
                self.signals.result.emit(self.image_path, icon, self.item)
        except Exception as e:
            debug(f"Error generating thumbnail for {self.image_path}: {e}")

class TimelineExplorer(QMainWindow):
    """Timeline explorer widget for viewing image sequences"""
    
    image_selected = Signal(str)  # Signal emitted when an image is selected
    
    def __init__(self, history_directory: str = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Timeline Explorer")
        self.history_directory = history_directory
        
        self.setup_ui()
        
        if history_directory:
            self.load_timeline_data()

    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create timeline tree widget
        self.timeline_tree = TimelineTreeWidget()
        self.timeline_tree.image_selected.connect(self.image_selected.emit)
        
        layout.addWidget(self.timeline_tree)

    def set_history_directory(self, directory: str):
        """Set the history directory and reload data"""
        self.history_directory = directory
        self.load_timeline_data()

    def load_timeline_data(self):
        """Load timeline data from history directory"""
        if not self.history_directory:
            return
        
        self.timeline_tree.load_timeline_data(self.history_directory)

    def export_all_to_gif(self):
        """Export all camera sequences to GIF files"""
        if not self.history_directory:
            QMessageBox.warning(self, "Export Error", "No history directory set.")
            return
        
        # Ask user for output directory
        output_dir = QFileDialog.getExistingDirectory(
            self, 
            "Select Output Directory for All GIFs", 
            os.path.expanduser("~/Desktop")
        )
        
        if not output_dir:
            return
        
        # Collect all camera data
        camera_data = defaultdict(list)
        
        try:
            for timestamp_folder in os.listdir(self.history_directory):
                timestamp_path = os.path.join(self.history_directory, timestamp_folder)
                if not os.path.isdir(timestamp_path):
                    continue
                
                try:
                    timestamp = datetime.strptime(timestamp_folder, "%Y-%m-%d_%H-%M-%S")
                except ValueError:
                    continue
                
                for filename in os.listdir(timestamp_path):
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tga')):
                        camera_name = self.timeline_tree.extract_camera_name(filename)
                        if camera_name:
                            image_path = os.path.join(timestamp_path, filename)
                            camera_data[camera_name].append((timestamp, image_path))
        
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error collecting camera data: {e}")
            return
        
        if not camera_data:
            QMessageBox.warning(self, "Export Error", "No camera data found.")
            return
        
        # Export each camera sequence
        total_cameras = len(camera_data)
        progress_dialog = QProgressDialog("Exporting all cameras to GIF...", "Cancel", 0, total_cameras, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        exported_count = 0
        for camera_name, images in camera_data.items():
            if progress_dialog.wasCanceled():
                break
            
            # Sort by timestamp (oldest first)
            images.sort(key=lambda x: x[0])
            image_paths = [img[1] for img in images]
            
            # Create GIF for this camera with image rescaling
            try:
                pil_images = []
                
                # First pass: determine the maximum resolution
                max_width, max_height = 0, 0
                for image_path in image_paths:
                    try:
                        with Image.open(image_path) as img:
                            max_width = max(max_width, img.width)
                            max_height = max(max_height, img.height)
                    except Exception as e:
                        debug(f"Error checking image size {image_path}: {e}")
                        continue
                
                if max_width == 0 or max_height == 0:
                    debug(f"No valid images for camera {camera_name}")
                    continue
                
                # Second pass: load and resize images
                for image_path in image_paths:
                    try:
                        img = Image.open(image_path)
                        
                        # Resize to maximum resolution if needed
                        if img.width != max_width or img.height != max_height:
                            img = img.resize((max_width, max_height), Image.Resampling.LANCZOS)
                        
                        if img.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'RGBA':
                                background.paste(img, mask=img.split()[-1])
                            else:
                                background.paste(img, mask=img.split()[-1])
                            img = background
                        elif img.mode != 'RGB':
                            img = img.convert('RGB')
                        pil_images.append(img)
                    except Exception as e:
                        debug(f"Error processing image {image_path}: {e}")
                        continue
                
                if pil_images:
                    gif_path = os.path.join(output_dir, f"{camera_name}_timeline.gif")
                    pil_images[0].save(
                        gif_path,
                        save_all=True,
                        append_images=pil_images[1:],
                        duration=500,
                        loop=0
                    )
                    debug(f"Exported GIF: {gif_path}")
            
            except Exception as e:
                debug(f"Error exporting {camera_name}: {e}")
            
            exported_count += 1
            progress_dialog.setValue(exported_count)
            QApplication.processEvents()
        
        progress_dialog.close()
        
        if exported_count > 0:
            QMessageBox.information(
                self, 
                "Export Complete", 
                f"Exported {exported_count} camera sequences to GIF files in:\n{output_dir}"
            )
        else:
            QMessageBox.warning(self, "Export Error", "No GIF files were created.")

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    
    # Test with a sample directory
    timeline = TimelineExplorer("D:/test/History")
    timeline.show()
    
    sys.exit(app.exec())