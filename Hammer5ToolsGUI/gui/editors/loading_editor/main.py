import os
import shutil

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QDialog,
    QFileDialog,
    QPlainTextEdit,
    QVBoxLayout,
    QProgressBar,
    QPushButton,
    QLabel,
    QWidget,
    QFrame,
    QSizePolicy,
    QHBoxLayout,
    QComboBox,
    QDockWidget,
    QTabWidget,
    QCheckBox,
)
from PySide6.QtCore import Qt, QRect, QObject, Signal, QRunnable, QThreadPool, QTimer, QSize, QByteArray
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor, QKeyEvent, QIcon, QCloseEvent
from PySide6.QtSvgWidgets import QSvgWidget

from gui.settings.common import (
    addon_content_dir,
    addon_game_dir,
    get_addon_name,
    get_addon_dir,
    get_settings_value,
    set_settings_value,
)
from gui.editors.loading_editor.viewport import ImageExplorer, extract_camera_name, is_generic_camera_name
from gui.editors.loading_editor.timeline import TimelineExplorer
from gui.common import compile
from gui.widgets import ErrorInfo
from gui.editors.loading_editor.commands import generate_commands
from gui.editors.loading_editor.svg_utils import rescale_svg
from gui.other.cs2_netcon import CS2Netcon
from gui.styles.common import set_style_property


class SvgPreviewWidget(QFrame):
    """
    A widget for drag and drop of SVG files. Displays a styled drop zone until an SVG is loaded.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.file_path = None
        self.setProperty("h5Component", "loadingSvgDropArea")
        self.setProperty("h5DragOver", "false")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)
        main_layout.setAlignment(Qt.AlignCenter)

        # Placeholder State Container
        self.placeholder_widget = QWidget(self)
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_layout.setContentsMargins(0, 0, 0, 0)
        placeholder_layout.setSpacing(6)
        placeholder_layout.setAlignment(Qt.AlignCenter)

        self.placeholder_icon = QLabel(self.placeholder_widget)
        self.placeholder_icon.setPixmap(QIcon(":/icons/upload_2_16dp.svg").pixmap(28, 28))
        self.placeholder_icon.setAlignment(Qt.AlignCenter)
        placeholder_layout.addWidget(self.placeholder_icon)

        self.info_label = QLabel("Drag and drop a SVG", self.placeholder_widget)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setProperty("h5Component", "loadingSvgDropLabel")
        placeholder_layout.addWidget(self.info_label)

        main_layout.addWidget(self.placeholder_widget)

        # Loaded SVG Preview (transparent background, replaces placeholder)
        self.svg_preview = QSvgWidget(self)
        self.svg_preview.setFixedSize(140, 140)
        self.svg_preview.setAttribute(Qt.WA_TranslucentBackground, True)
        main_layout.addWidget(self.svg_preview, alignment=Qt.AlignCenter)
        self.svg_preview.hide()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(url.toLocalFile().lower().endswith('.svg') for url in urls):
                self.setProperty("h5DragOver", "true")
                self.style().unpolish(self)
                self.style().polish(self)
                event.acceptProposedAction()
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("h5DragOver", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        event.accept()

    def dropEvent(self, event):
        self.setProperty("h5DragOver", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith('.svg'):
                    self.load_svg(file_path)
                    break
            else:
                self.info_label.setText("Only SVG files are accepted.")
            event.acceptProposedAction()
        else:
            event.ignore()

    def get_svg_path(self):
        if not self.file_path or not self.file_path.lower().endswith('.svg'):
            raise ValueError("The file is not an SVG file.")
        return self.file_path

    def load_svg(self, svg_path: str):
        if os.path.exists(svg_path) and svg_path.lower().endswith('.svg'):
            self.file_path = svg_path
            self.svg_preview.load(svg_path)
            self.placeholder_widget.hide()
            self.svg_preview.show()

    def clear_svg(self):
        self.file_path = None
        self.svg_preview.hide()
        self.info_label.setText("Drag and drop a SVG")
        self.placeholder_widget.show()


class ApplyScreenshotsSignals(QObject):
    progress = Signal(int)
    error = Signal(str)
    finished = Signal()
    log = Signal(str)


class ApplyScreenshotsWorker(QRunnable):
    def __init__(self, game_screenshot_path: str, delete_existing: bool, camera_name_mode: bool = False):
        super().__init__()
        self.game_screenshot_path = game_screenshot_path
        self.delete_existing = delete_existing
        self.camera_name_mode = camera_name_mode
        self.signals = ApplyScreenshotsSignals()
        self._is_aborted = False
        content_dir = addon_content_dir()
        self.addon_path = str(content_dir) if content_dir else ""

    def run(self):
        try:
            if self._is_aborted:
                return

            res_folder = os.path.join(self.addon_path, "res")
            if os.path.exists(res_folder):
                shutil.rmtree(res_folder)
                self.signals.log.emit(f"Deleted res folder at {res_folder}")

            self.clean_resolution_folders()
            self.signals.log.emit("Cleaned resolution folders.")
            file_list = self.collect_files()
            self.signals.progress.emit(40)

            if self._is_aborted:
                return
            self.delete_old_vtex()
            self.signals.progress.emit(60)

            if self._is_aborted:
                return
            self.process_files(file_list)
            self.signals.progress.emit(100)

            self.signals.finished.emit()
        except Exception:
            import traceback
            error_message = traceback.format_exc()
            self.signals.error.emit(error_message)
            self.signals.log.emit(f"Error occurred: {error_message}")

    def clean_resolution_folders(self):
        resolutions = ["1080p", "720p", "360p"]
        base_folder = os.path.join(self.addon_path, "panorama", "images", "map_icons", "screenshots")
        for res in resolutions:
            target_folder = os.path.join(base_folder, res)
            if os.path.exists(target_folder):
                for filename in os.listdir(target_folder):
                    file_path = os.path.join(target_folder, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.remove(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                        self.signals.log.emit(f"Deleted {file_path}")
                    except Exception as e:
                        self.signals.log.emit(f"Failed to delete {file_path}: {e}")
            else:
                os.makedirs(target_folder, exist_ok=True)
                self.signals.log.emit(f"Created folder {target_folder}")

    def collect_files(self) -> list:
        self.signals.log.emit("Collecting image files from game screenshot folder")
        file_list = []
        try:
            files = sorted([f for f in os.listdir(self.game_screenshot_path)
                            if os.path.isfile(os.path.join(self.game_screenshot_path, f))])
        except Exception as e:
            self.signals.log.emit(f"Error listing files: {e}")
            files = []
        for idx, file_name in enumerate(files):
            original_path = os.path.join(self.game_screenshot_path, file_name)
            new_base_name = f"{get_addon_name()}_png" if idx == 0 else f"{get_addon_name()}_{idx}_png"
            camera_name = None
            if self.camera_name_mode:
                camera_name = extract_camera_name(file_name, get_addon_name())
            file_list.append((original_path, new_base_name, camera_name))
        self.signals.log.emit(f"Collected file list: {file_list}")
        return file_list

    def delete_old_vtex(self):
        self.signals.log.emit("Deleting old vtex files")
        try:
            shutil.rmtree(os.path.join(self.addon_path, "panorama", "images", "map_icons", "screenshots", "1080p"))
            self.signals.log.emit("Deleted old vtex files from primary location")
        except Exception as e:
            self.signals.log.emit(f"Error deleting old vtex files: {e}")
        if self.delete_existing:
            self.signals.log.emit("Deleting compiled vtex_c files because delete_existing is True")
            try:
                game_dir = addon_game_dir()
                if not game_dir:
                    return
                base = str(game_dir / "panorama" / "images" / "map_icons" / "screenshots")
                for res in ["1080p", "720p", "360p"]:
                    shutil.rmtree(os.path.join(base, res))
                self.signals.log.emit("Deleted compiled vtex_c files from game location")
            except Exception as e:
                self.signals.log.emit(f"Error deleting compiled vtex_c files: {e}")

    def process_files(self, file_list: list):
        total_files = len(file_list)
        for index, file_info in enumerate(file_list):
            if self._is_aborted:
                self.signals.log.emit("Processing aborted.")
                return
            original_file = file_info[0]
            new_base_name = file_info[1]
            camera_name = file_info[2] if len(file_info) > 2 else None
            self.signals.log.emit(f"Processing file: {original_file} as {new_base_name}")
            self.creating_vtex(original_file, new_base_name, camera_name)
            progress = 60 + int(40 * (index + 1) / total_files)
            self.signals.progress.emit(progress)

    def creating_vtex(self, original_file_path: str, new_base_name: str, camera_name: str = None):
        resolutions = {
            "1080p": 1080,
            "720p": 720,
            "360p": 360,
        }
        pixmap = QPixmap(original_file_path)
        if pixmap.isNull():
            msg = f"Error loading image {original_file_path} with QPixmap."
            self.signals.log.emit(msg)
            return

        if self.camera_name_mode and camera_name:
            pixmap = self.add_camera_name_label(pixmap, camera_name)

        vtex_template = (
            """<!-- dmx encoding keyvalues2_noids 1 format vtex 1 -->
"CDmeVtex"
{
    "m_inputTextureArray" "element_array"
    [
        "CDmeInputTexture"
        {
            "m_name" "string" "SheetTexture"
            "m_fileName" "string" "%%PATH%%"
            "m_colorSpace" "string" "linear"
            "m_typeString" "string" "2D"
            "m_imageProcessorArray" "element_array"
            [
            ]
        }
    ]
    "m_outputTypeString" "string" "2D"
    "m_outputFormat" "string" "BC7"
    "m_outputClearColor" "vector4" "0 0 0 0"
    "m_nOutputMinDimension" "int" "0"
    "m_nOutputMaxDimension" "int" "2048"
    "m_textureOutputChannelArray" "element_array"
    [
        "CDmeTextureOutputChannel"
        {
            "m_inputTextureArray" "string_array"
            [
                "SheetTexture"
            ]
            "m_srcChannels" "string" "rgba"
            "m_dstChannels" "string" "rgba"
            "m_mipAlgorithm" "CDmeImageProcessor"
            {
                "m_algorithm" "string" ""
                "m_stringArg" "string" ""
                "m_vFloat4Arg" "vector4" "0 0 0 0"
            }
            "m_outputColorSpace" "string" "linear"
        }
    ]
    "m_vClamp" "vector3" "0 0 0"
    "m_bNoLod" "bool" "1"
}
"""
        )
        for res_folder, max_height in resolutions.items():
            target_folder = os.path.join(self.addon_path, "panorama", "images", "map_icons", "screenshots", res_folder)
            os.makedirs(target_folder, exist_ok=True)
            scaled_pixmap = pixmap.scaledToHeight(max_height, Qt.SmoothTransformation)
            output_image_path = os.path.join(target_folder, f"{new_base_name}.png")
            if not scaled_pixmap.save(output_image_path, "PNG"):
                err_msg = f"Error saving downscaled image {output_image_path}"
                self.signals.log.emit(err_msg)
                continue

            relative_image_path = os.path.relpath(output_image_path, self.addon_path).replace("\\", "/")
            vtex_content = vtex_template.replace("%%PATH%%", relative_image_path)
            vtex_path = os.path.join(target_folder, f"{new_base_name}.vtex")
            try:
                with open(vtex_path, "w") as file:
                    file.write(vtex_content)
                self.signals.log.emit(f"Created vtex file at {vtex_path}")
            except Exception as e:
                err_msg = f"Error writing vtex file {vtex_path}: {e}"
                self.signals.log.emit(err_msg)
                continue
            compile(vtex_path)
            self.signals.log.emit(f"Compiled vtex file {vtex_path}")

    def add_camera_name_label(self, pixmap: QPixmap, camera_name: str) -> QPixmap:
        if not camera_name or is_generic_camera_name(camera_name):
            return pixmap
        result = QPixmap(pixmap)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        scale = result.height() / 1080.0
        font_size = max(8, int(31 * scale))

        font = QFont("Bahnschrift")
        font.setStyleName("Light SemiCondensed")
        if not font.exactMatch():
            font = QFont("Bahnschrift Light SemiCondensed")
        if not font.exactMatch():
            font = QFont("Noto Sans")
        font.setPixelSize(font_size)

        painter.setFont(font)

        cam_x = int(46 * scale)
        cam_y = int(1010 * scale)
        cam_h = int(31 * scale)
        cam_rect = QRect(cam_x, cam_y, result.width() // 2, cam_h)

        painter.setPen(QColor(255, 255, 255))
        painter.drawText(cam_rect, Qt.AlignLeft | Qt.AlignVCenter, camera_name)

        painter.end()
        return result

    def abort(self):
        self._is_aborted = True
        self.signals.log.emit("Abort signal received. Terminating processing.")


class UnifiedProcessingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing")
        self.setMinimumSize(880, 300)
        layout = QVBoxLayout(self)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)
        self.log_text = QPlainTextEdit(self)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        self.cancel_button = QPushButton("Cancel", self)
        layout.addWidget(self.cancel_button)

    def update_progress(self, value: int):
        self.progress_bar.setValue(value)

    def append_log(self, message: str):
        self.log_text.appendPlainText(message)

    def reset(self):
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self.cancel_button.setText("Cancel")
        set_style_property(self.cancel_button, "h5State", "idle")


class LoadingEditorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.threadpool = QThreadPool()
        game_dir, content_dir = addon_game_dir(), addon_content_dir()
        if game_dir and content_dir:
            self.game_screenshot_path = str(game_dir / "screenshots" / "Hammer5Tools")
            self.loadingscreen_path = os.path.join(self.game_screenshot_path, "LoadingScreen")
            self.history_path = os.path.join(self.game_screenshot_path, "History")
            self.content_history_path = str(content_dir / "panorama" / "history_screenshots")
            os.makedirs(self.loadingscreen_path, exist_ok=True)
            os.makedirs(self.content_history_path, exist_ok=True)
        else:
            self.game_screenshot_path = ""
            self.loadingscreen_path = ""
            self.history_path = ""
            self.content_history_path = ""

        self._build_ui()
        self._wire_signals()

        self.unified_dialog = UnifiedProcessingDialog(self)

        self.load_existing_icon()
        self.load_existing_description()

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._save_layout_state)

    def _build_ui(self):
        self.setWindowTitle("Loading Screen Editor")
        self.setObjectName("LoadingEditor_MainWindow")

        self.setDockOptions(
            QMainWindow.AnimatedDocks |
            QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks |
            QMainWindow.GroupedDragging
        )
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)

        dock_features = QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable

        # --- Views and Central Viewport ---
        self.explorer_view = ImageExplorer(
            history_dir=self.content_history_path,
            loadingshots_dir=self.loadingscreen_path,
        )
        self.timeline_view = TimelineExplorer(history_directory=self.content_history_path)

        self.image_viewer = self.explorer_view.image_viewer
        self.image_viewer.set_preview_data_provider(self.get_loading_preview_data)
        self.setCentralWidget(self.image_viewer)

        # --- Left Dock: Screenshots ---
        self.screenshots_dock = QDockWidget("Screenshots", self)
        self.screenshots_dock.setObjectName("LoadingEditor_ScreenshotsDock")
        self.screenshots_dock.setFeatures(dock_features)

        screenshots_widget = QWidget()
        screenshots_layout = QVBoxLayout(screenshots_widget)
        screenshots_layout.setContentsMargins(4, 4, 4, 4)
        screenshots_layout.setSpacing(4)

        self.screenshots_tabwidget = QTabWidget()
        self.screenshots_tabwidget.setObjectName("screenshots_tabwidget")

        # Explorer Tab
        explorer_tab = QWidget()
        explorer_layout = QVBoxLayout(explorer_tab)
        explorer_layout.setContentsMargins(0, 0, 0, 0)
        explorer_layout.setSpacing(0)
        explorer_layout.addWidget(self.explorer_view)
        self.screenshots_tabwidget.addTab(explorer_tab, "Explorer")

        # Timeline Tab
        timeline_tab = QWidget()
        timeline_layout = QVBoxLayout(timeline_tab)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.setSpacing(4)

        timeline_top_row = QHBoxLayout()
        timeline_top_row.setContentsMargins(0, 0, 0, 0)
        timeline_top_row.setSpacing(4)

        self.refresh = QPushButton("Refresh")
        self.refresh.setIcon(QIcon(":/valve_common/icons/tools/common/refresh.png"))
        self.refresh.setIconSize(QSize(20, 20))
        self.refresh.setMinimumHeight(32)
        self.refresh.setToolTip("Refresh timeline screenshots")

        self.animation_format_combo = QComboBox()
        self.animation_format_combo.addItems(["GIF", "WEBP", "MP4"])
        self.animation_format_combo.setToolTip("Animation output format")
        self.animation_format_combo.setMinimumHeight(32)

        self.animation_quality_combo = QComboBox()
        self.animation_quality_combo.addItems(["Low", "Medium", "High"])
        self.animation_quality_combo.setCurrentText("High")
        self.animation_quality_combo.setToolTip("Animation quality (WEBP/MP4 only, ignored for GIF)")
        self.animation_quality_combo.setMinimumHeight(32)

        self.generate_gifs = QPushButton("Create animation")
        self.generate_gifs.setIcon(QIcon(":/valve_common/icons/tools/common/control_play.png"))
        self.generate_gifs.setIconSize(QSize(20, 20))
        self.generate_gifs.setMinimumHeight(32)
        self.generate_gifs.setToolTip("Create animations for all cameras")

        timeline_top_row.addWidget(self.refresh)
        timeline_top_row.addWidget(self.animation_format_combo)
        timeline_top_row.addWidget(self.animation_quality_combo)
        timeline_top_row.addWidget(self.generate_gifs)

        timeline_layout.addLayout(timeline_top_row)
        timeline_layout.addWidget(self.timeline_view, 1)

        self.screenshots_tabwidget.addTab(timeline_tab, "Timeline")
        screenshots_layout.addWidget(self.screenshots_tabwidget, 1)

        # Capture Actions
        shots_row = QHBoxLayout()
        shots_row.setContentsMargins(0, 0, 0, 0)
        shots_row.setSpacing(4)

        self.take_history_shots = QPushButton("Take History Shots")
        self.take_history_shots.setIcon(QIcon(":/icons/acute_24dp.svg"))
        self.take_history_shots.setIconSize(QSize(20, 20))
        self.take_history_shots.setMinimumHeight(32)
        self.take_history_shots.setToolTip(
            "Generate commands and send them to CS2 to take history screenshots. "
            "Images will be saved in: game/screenshots/Hammer5Tools/History/Date"
        )

        self.take_loading_screen_shots = QPushButton("Take Loading Screen Shots")
        self.take_loading_screen_shots.setIcon(QIcon(":/icons/data_object_24dp.png"))
        self.take_loading_screen_shots.setIconSize(QSize(20, 20))
        self.take_loading_screen_shots.setMinimumHeight(32)
        self.take_loading_screen_shots.setToolTip(
            "Generate commands and send them to CS2 to take loading screen screenshots. "
            "Previous images in game/screenshots/Hammer5Tools/LoadingScreen will be deleted first."
        )

        shots_row.addWidget(self.take_history_shots)
        shots_row.addWidget(self.take_loading_screen_shots)
        screenshots_layout.addLayout(shots_row)

        # Apply Options
        apply_row = QHBoxLayout()
        apply_row.setContentsMargins(0, 0, 0, 0)
        apply_row.setSpacing(4)

        self.delete_existings = QCheckBox("Delete existing")
        self.delete_existings.setIcon(QIcon(":/icons/delete_sweep_16dp.svg"))
        self.delete_existings.setIconSize(QSize(20, 20))
        self.delete_existings.setChecked(True)
        self.delete_existings.setToolTip("Deletes all existing screenshots on the loading screen.")

        self.camera_name_mode = QCheckBox("Camera Name")
        self.camera_name_mode.setIcon(QIcon(":/icons/colors_24dp.png"))
        self.camera_name_mode.setIconSize(QSize(20, 20))
        self.camera_name_mode.setChecked(False)
        self.camera_name_mode.setToolTip("Adds name of point_camera to image")

        self.apply_screenshots_button = QPushButton("Set loading images")
        self.apply_screenshots_button.setIcon(QIcon(":/icons/check_24dp.svg"))
        self.apply_screenshots_button.setIconSize(QSize(20, 20))
        self.apply_screenshots_button.setMinimumHeight(32)
        self.apply_screenshots_button.setToolTip(
            "Apply images that are located in game/screenshots/Hammer5Tools/LoadingScreen as loading screen images"
        )

        apply_row.addWidget(self.delete_existings)
        apply_row.addWidget(self.camera_name_mode)
        apply_row.addWidget(self.apply_screenshots_button)
        screenshots_layout.addLayout(apply_row)

        self.screenshots_dock.setWidget(screenshots_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.screenshots_dock)

        # --- Right Dock 1: Icon ---
        self.icon_dock = QDockWidget("Icon", self)
        self.icon_dock.setObjectName("LoadingEditor_IconDock")
        self.icon_dock.setFeatures(dock_features)

        icon_widget = QWidget()
        icon_layout = QVBoxLayout(icon_widget)
        icon_layout.setContentsMargins(6, 6, 6, 6)
        icon_layout.setSpacing(6)

        self.svg_preview_widget = SvgPreviewWidget()
        icon_layout.addWidget(self.svg_preview_widget, 1)

        self.svg_tips_label = QLabel("Tips: Convert text to paths. Avoid rasterized layers.")
        self.svg_tips_label.setWordWrap(True)
        self.svg_tips_label.setProperty("h5Component", "loadingSvgTips")
        self.svg_tips_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        icon_layout.addWidget(self.svg_tips_label, 0)

        self.fit_viewbox_checkbox = QCheckBox("Fit content to viewbox")
        self.fit_viewbox_checkbox.setChecked(True)
        self.fit_viewbox_checkbox.setToolTip("Rescale the SVG content to fit a 32x32 viewBox and remove hidden elements.")
        icon_layout.addWidget(self.fit_viewbox_checkbox, 0)

        self.apply_icon_button = QPushButton("Apply Icon")
        self.apply_icon_button.setIcon(QIcon(":/icons/check_24dp.svg"))
        self.apply_icon_button.setIconSize(QSize(20, 20))
        self.apply_icon_button.setMinimumHeight(32)
        icon_layout.addWidget(self.apply_icon_button, 0)

        self.icon_dock.setWidget(icon_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.icon_dock)

        # --- Right Dock 2: Description ---
        self.description_dock = QDockWidget("Description", self)
        self.description_dock.setObjectName("LoadingEditor_DescriptionDock")
        self.description_dock.setFeatures(dock_features)

        description_widget = QWidget()
        description_layout = QVBoxLayout(description_widget)
        description_layout.setContentsMargins(6, 6, 6, 6)
        description_layout.setSpacing(6)

        self.PlainTextEdit_Description_2 = QPlainTextEdit()
        self.PlainTextEdit_Description_2.setPlaceholderText("A community map created by:")
        description_layout.addWidget(self.PlainTextEdit_Description_2, 1)

        self.apply_description_button = QPushButton("Apply description")
        self.apply_description_button.setIcon(QIcon(":/icons/check_24dp.svg"))
        self.apply_description_button.setIconSize(QSize(20, 20))
        self.apply_description_button.setMinimumHeight(32)
        description_layout.addWidget(self.apply_description_button, 0)

        self.description_dock.setWidget(description_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.description_dock)

        self.splitDockWidget(self.icon_dock, self.description_dock, Qt.Vertical)

        self._restore_layout_state()

    def _wire_signals(self):
        self.timeline_view.image_selected.connect(self.on_timeline_image_selected)
        self.screenshots_tabwidget.currentChanged.connect(self.on_tab_changed)

        self.apply_description_button.clicked.connect(self.do_loading_editor_cs2_description)
        self.apply_screenshots_button.clicked.connect(self.start_apply_screenshots)
        self.apply_icon_button.clicked.connect(self.icon_processs)
        self.take_history_shots.clicked.connect(self.take_history_shots_action)
        self.take_loading_screen_shots.clicked.connect(self.take_loading_screen_shots_action)
        self.refresh.clicked.connect(self.refresh_timeline)
        self.generate_gifs.clicked.connect(self.export_all_animations)

        self.animation_format_combo.currentTextChanged.connect(self.update_animation_settings)
        self.animation_quality_combo.currentTextChanged.connect(self.update_animation_settings)
        self.update_animation_settings()

        self.PlainTextEdit_Description_2.textChanged.connect(self.image_viewer.update_preview_content)
        self.camera_name_mode.stateChanged.connect(self.image_viewer.update_preview_content)
        self.camera_name_mode.toggled.connect(self.image_viewer.update_preview_content)

    def _save_layout_state(self):
        try:
            geo_hex = self.saveGeometry().toHex().data().decode("utf-8")
            state_hex = self.saveState().toHex().data().decode("utf-8")
            set_settings_value("LoadingEditor", "geometry", geo_hex)
            set_settings_value("LoadingEditor", "window_state", state_hex)
        except Exception:
            pass

    def _restore_layout_state(self):
        try:
            geo_hex = get_settings_value("LoadingEditor", "geometry")
            if geo_hex:
                self.restoreGeometry(QByteArray.fromHex(geo_hex.encode("utf-8")))
            state_hex = get_settings_value("LoadingEditor", "window_state")
            if state_hex:
                restored = self.restoreState(QByteArray.fromHex(state_hex.encode("utf-8")))
                if not restored:
                    self._apply_default_dock_sizes()
            else:
                self._apply_default_dock_sizes()
        except Exception:
            self._apply_default_dock_sizes()

    def _apply_default_dock_sizes(self):
        total_w = self.width() if self.width() > 400 else 1200
        side_w = max(260, int(total_w * 0.25))
        self.resizeDocks([self.screenshots_dock, self.icon_dock, self.description_dock], [side_w, side_w, side_w], Qt.Horizontal)
        self.resizeDocks([self.icon_dock, self.description_dock], [320, 200], Qt.Vertical)

    def closeEvent(self, event: QCloseEvent):
        self._save_layout_state()
        super().closeEvent(event)

    def refresh_timeline(self):
        """Refresh timeline data"""
        self.timeline_view.load_timeline_data()

    def on_tab_changed(self, index: int):
        """Handle tab change between Explorer and Timeline"""
        if index == 1:
            self.timeline_view.load_timeline_data()

    def on_timeline_image_selected(self, image_path: str):
        """Handle image selection from timeline view"""
        if os.path.exists(image_path):
            self.image_viewer.showImage(image_path)

    def export_all_animations(self):
        self.timeline_view.export_all_animations()

    def update_animation_settings(self):
        self.timeline_view.set_export_settings(
            self.animation_format_combo.currentText(),
            self.animation_quality_combo.currentText(),
        )

    def get_loading_preview_data(self) -> dict:
        """
        Supplies the CS2 loading-screen preview overlay with the current map
        icon, name, description, and camera name preference as configured in this editor.
        """
        icon_path = self.svg_preview_widget.file_path
        if not icon_path or not os.path.exists(icon_path):
            content_dir = addon_content_dir()
            if content_dir:
                possible_path = str(content_dir / "panorama" / "images" / "map_icons" / f"map_icon_{get_addon_name()}.svg")
                if os.path.exists(possible_path):
                    icon_path = possible_path

        show_camera_name = self.camera_name_mode.isChecked()

        return {
            "icon_path": icon_path,
            "map_name": get_addon_name(),
            "gamemode_text": "Competitive",
            "description_html": self.PlainTextEdit_Description_2.toPlainText(),
            "show_camera_name": show_camera_name,
        }

    def load_existing_icon(self):
        content_dir = addon_content_dir()
        if content_dir:
            folder_path = str(content_dir / "panorama" / "images" / "map_icons")
            svg_icon_filename = f"map_icon_{get_addon_name()}.svg"
            svg_path = os.path.join(folder_path, svg_icon_filename)
            if os.path.exists(svg_path):
                self.svg_preview_widget.load_svg(svg_path)

    def load_existing_description(self):
        game_dir = addon_game_dir()
        if not game_dir:
            return
        description_file = str(game_dir / "maps" / f"{get_addon_name()}.txt")
        if os.path.exists(description_file):
            try:
                with open(description_file, "r") as f:
                    lines = f.readlines()
                description = "".join(lines[1:]).strip() if len(lines) > 1 else ""
                self.PlainTextEdit_Description_2.setPlainText(description)
            except Exception:
                pass

    def start_apply_screenshots(self):
        try:
            file_count = len([f for f in os.listdir(self.loadingscreen_path)
                              if os.path.isfile(os.path.join(self.loadingscreen_path, f))])
        except Exception:
            file_count = 0

        if file_count > 10:
            QMessageBox.warning(self, "Warning", "The number of files is more than 10. The game doesn't support more than 10")

        self.unified_dialog.reset()
        worker = ApplyScreenshotsWorker(
            self.loadingscreen_path,
            self.delete_existings.isChecked(),
            self.camera_name_mode.isChecked()
        )
        worker.signals.progress.connect(self.unified_dialog.update_progress)
        worker.signals.error.connect(self.show_error)
        worker.signals.finished.connect(self.processing_finished)
        worker.signals.log.connect(self.unified_dialog.append_log)
        self.unified_dialog.cancel_button.clicked.connect(worker.abort)
        self.unified_dialog.show()
        self.threadpool.start(worker)

    def show_error(self, error_message: str):
        self.unified_dialog.append_log("Error: " + error_message)
        error_dialog = ErrorInfo(text="An error occurred during processing.", details=error_message)
        error_dialog.exec_()

    def processing_finished(self):
        self.unified_dialog.append_log("Processing complete.")
        self.unified_dialog.cancel_button.setText("Finish")
        set_style_property(self.unified_dialog.cancel_button, "h5State", "complete")
        try:
            self.unified_dialog.cancel_button.clicked.disconnect()
        except Exception:
            pass
        self.unified_dialog.cancel_button.clicked.connect(self.unified_dialog.close)

    def take_history_shots_action(self):
        """Generate commands for history screenshots and send directly to CS2 via netcon."""
        vmap_path = os.path.join(get_addon_dir(), "maps", f"{get_addon_name()}.vmap")
        commands, session_date = generate_commands(vmap_path, history=True)
        if not commands:
            return

        from gui.widgets import require_cs2
        if not require_cs2("take screenshots"):
            return
        if not CS2Netcon.send_many(commands):
            return

        if not session_date or not self.content_history_path:
            return

        # Count the shots themselves: a camera contributes a varying number of
        # commands (its angles or FOV may be missing), so deriving the count
        # from the list length drifts and the copy can start too early.
        camera_count = max(1, sum("png_screenshot" in command for command in commands))
        delay_ms = max(3000, int(camera_count * (10 / 64) * 1000) + 2000)

        src_folder = os.path.join(self.history_path, session_date)
        dst_folder = os.path.join(self.content_history_path, session_date)

        QTimer.singleShot(delay_ms, lambda: self._copy_history_session(src_folder, dst_folder))

    def _copy_history_session(self, src_folder: str, dst_folder: str):
        """Copy history screenshots from the game folder into content/panorama/history_screenshots."""
        if not os.path.isdir(src_folder):
            return
        try:
            os.makedirs(dst_folder, exist_ok=True)
            for filename in os.listdir(src_folder):
                src_file = os.path.join(src_folder, filename)
                if os.path.isfile(src_file):
                    shutil.copy2(src_file, os.path.join(dst_folder, filename))
        except Exception:
            pass

    def take_loading_screen_shots_action(self):
        """Generate commands for loading screen screenshots, clear previous shots, and send to CS2 via netcon."""
        if os.path.exists(self.loadingscreen_path):
            for filename in os.listdir(self.loadingscreen_path):
                file_path = os.path.join(self.loadingscreen_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception:
                    pass

        path = os.path.join(get_addon_dir(), "maps", f"{get_addon_name()}.vmap")
        commands, _ = generate_commands(path, history=False)
        if commands:
            from gui.widgets import require_cs2
            if not require_cs2("take screenshots"):
                return
            CS2Netcon.send_many(commands)

    def loading_editor_cs2_description(self, description_text: str):
        game_dir = addon_game_dir()
        if not game_dir:
            return
        file_name = str(game_dir / "maps" / f"{get_addon_name()}.txt")
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, "w") as f:
            f.write("COMMUNITYMAPCREDITS:\n")
            f.write(description_text)

    def icon_processs(self):
        try:
            svg_path = os.path.normpath(self.svg_preview_widget.get_svg_path())
        except ValueError:
            return
        content_dir = addon_content_dir()
        if not content_dir:
            return
        folder_path = str(content_dir / "panorama" / "images" / "map_icons")
        os.makedirs(folder_path, exist_ok=True)
        svg_dst = os.path.join(folder_path, f"map_icon_{get_addon_name()}.svg")
        if os.path.exists(svg_dst):
            os.remove(svg_dst)
        if self.fit_viewbox_checkbox.isChecked():
            try:
                rescale_svg(svg_path, svg_dst)
            except Exception:
                shutil.copy2(svg_path, svg_dst)
        else:
            shutil.copy2(svg_path, svg_dst)

    def do_loading_editor_cs2_description(self):
        self.loading_editor_cs2_description(self.PlainTextEdit_Description_2.toPlainText())

    def keyPressEvent(self, event: QKeyEvent):
        """
        Handle key press events for the main window.
        F key: Reset camera viewport position
        """
        if event.key() == Qt.Key_F:
            focused_widget = QApplication.focusWidget()
            if not isinstance(focused_widget, (QPlainTextEdit,)):
                self.image_viewer.restoreCameraPosition()
        else:
            super().keyPressEvent(event)

