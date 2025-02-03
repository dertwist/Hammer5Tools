import os
import shutil
import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QDialog,
    QPlainTextEdit,
    QVBoxLayout,
    QProgressBar,
    QPushButton,
    QLabel,
    QWidget
)
from PySide6.QtCore import Qt, QObject, Signal, QRunnable, QThreadPool
from PySide6.QtGui import QPixmap
from PySide6.QtSvgWidgets import QSvgWidget

from src.settings.main import get_cs2_path, get_addon_name, debug
from src.loading_editor.ui_main import Ui_Loading_editorMainWindow
from src.explorer.image_viewer import ExplorerImageViewer
from src.common import compile
from src.widgets import ErrorInfo


class SvgPreviewWidget(QWidget):
    """
    A widget that supports drag and drop for SVG files.
    Initially, a placeholder is shown. When an SVG file is dropped,
    the placeholder is hidden and the SVG preview is displayed.
    """
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.file_path = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.svg_preview = QSvgWidget(self)
        self.svg_preview.setFixedSize(200, 200)
        self.svg_preview.setStyleSheet("border: none;")
        self.svg_preview.hide()
        layout.addWidget(self.svg_preview, alignment=Qt.AlignCenter)

        self.info_label = QLabel("Drag and drop an SVG file", self)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("margin: 0px; border: 0px; color: gray; font-size: 13px;")
        layout.addWidget(self.info_label, alignment=Qt.AlignCenter)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if all(url.toLocalFile().lower().endswith('.svg') for url in urls):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith('.svg'):
                    self.file_path = file_path
                    self.svg_preview.load(file_path)
                    self.info_label.hide()
                    self.svg_preview.show()
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


class ApplyScreenshotsSignals(QObject):
    progress = Signal(int)
    error = Signal(str)
    finished = Signal()
    log = Signal(str)


class ApplyScreenshotsWorker(QRunnable):
    def __init__(self, game_screenshot_path: str, delete_existing: bool):
        super().__init__()
        self.game_screenshot_path = game_screenshot_path
        self.delete_existing = delete_existing
        self.signals = ApplyScreenshotsSignals()
        self._is_aborted = False
        self.addon_path = os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name())

    def run(self):
        try:
            if self._is_aborted:
                return

            res_folder = os.path.join(self.addon_path, "res")
            if os.path.exists(res_folder):
                shutil.rmtree(res_folder)
                debug(f"Deleted res folder at {res_folder}")
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
        except Exception as e:
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
            debug(f"Error listing files: {e}")
            self.signals.log.emit(f"Error listing files: {e}")
            files = []
        for idx, file_name in enumerate(files):
            original_path = os.path.join(self.game_screenshot_path, file_name)
            new_base_name = f"{get_addon_name()}_png" if idx == 0 else f"{get_addon_name()}_{idx}_png"
            file_list.append((original_path, new_base_name))
        self.signals.log.emit(f"Collected file list: {file_list}")
        return file_list

    def delete_old_vtex(self):
        self.signals.log.emit("Deleting old vtex files")
        try:
            shutil.rmtree(os.path.join(self.addon_path, "panorama", "images", "map_icons", "screenshots", "1080p"))
            self.signals.log.emit("Deleted old vtex files from primary location")
        except Exception as e:
            debug(f"Error deleting old vtex files: {e}")
            self.signals.log.emit(f"Error deleting old vtex files: {e}")
        if self.delete_existing:
            self.signals.log.emit("Deleting compiled vtex_c files because delete_existing is True")
            try:
                shutil.rmtree(os.path.join(get_cs2_path(), "game", "csgo_addons", get_addon_name(),
                                           "panorama", "images", "map_icons", "screenshots", "1080p"))
                self.signals.log.emit("Deleted compiled vtex_c files from game location")
            except Exception as e:
                debug(f"Error deleting compiled vtex_c files: {e}")
                self.signals.log.emit(f"Error deleting compiled vtex_c files: {e}")

    def process_files(self, file_list: list):
        total_files = len(file_list)
        for index, (original_file, new_base_name) in enumerate(file_list):
            if self._is_aborted:
                self.signals.log.emit("Processing aborted.")
                return
            self.signals.log.emit(f"Processing file: {original_file} as {new_base_name}")
            self.creating_vtex(original_file, new_base_name)
            progress = 60 + int(40 * (index + 1) / total_files)
            self.signals.progress.emit(progress)

    def creating_vtex(self, original_file_path: str, new_base_name: str):
        resolutions = {
            "1080p": 1080,
            "720p": 720,
            "360p": 360,
        }
        pixmap = QPixmap(original_file_path)
        if pixmap.isNull():
            msg = f"Error loading image {original_file_path} with QPixmap."
            debug(msg)
            self.signals.log.emit(msg)
            return

        vtex_template = """<!-- dmx encoding keyvalues2_noids 1 format vtex 1 -->
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
        for res_folder, max_height in resolutions.items():
            target_folder = os.path.join(self.addon_path, "panorama", "images", "map_icons", "screenshots", res_folder)
            os.makedirs(target_folder, exist_ok=True)

            scaled_pixmap = pixmap.scaledToHeight(max_height, Qt.SmoothTransformation)
            output_image_path = os.path.join(target_folder, f"{new_base_name}.png")
            if not scaled_pixmap.save(output_image_path, "PNG"):
                err_msg = f"Error saving downscaled image {output_image_path}"
                debug(err_msg)
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
                debug(err_msg)
                self.signals.log.emit(err_msg)
                continue
            compile(vtex_path)
            self.signals.log.emit(f"Compiled vtex file {vtex_path}")

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
        self.cancel_button.setStyleSheet("")


class Loading_editorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Loading_editorMainWindow()
        self.ui.setupUi(self)

        self.threadpool = QThreadPool()
        self.game_screenshot_path = os.path.join(get_cs2_path(), "game", "csgo_addons", get_addon_name(), "screenshots")
        if not os.path.exists(self.game_screenshot_path):
            os.makedirs(self.game_screenshot_path)

        explorer_view = ExplorerImageViewer(tree_directory=self.game_screenshot_path)
        explorer_view.setStyleSheet("padding:0")
        self.ui.explorer.layout().addWidget(explorer_view)
        self.ui.screenshot_preview.layout().addWidget(explorer_view.image_viewer)
        self.ui.splitter_2.setSizes([200, 100])

        self.svg_preview_widget = SvgPreviewWidget()
        self.ui.svg_icon_frame.layout().addWidget(self.svg_preview_widget)

        self.ui.apply_description_button.clicked.connect(self.do_loading_editor_cs2_description)
        self.ui.apply_screenshots_button.clicked.connect(self.start_apply_screenshots)
        self.ui.apply_icon_button.clicked.connect(self.icon_processs)
        self.ui.clear_all_button.clicked.connect(self.clear_images)
        self.ui.open_folder_button.clicked.connect(self.open_images_folder)

        self.unified_dialog = UnifiedProcessingDialog(self)

    def start_apply_screenshots(self):
        try:
            file_count = len([f for f in os.listdir(self.game_screenshot_path)
                              if os.path.isfile(os.path.join(self.game_screenshot_path, f))])
        except Exception as e:
            debug(f"Error counting files: {e}")
            file_count = 0
        if file_count > 10:
            reply = QMessageBox.warning(
                self,
                "Warning",
                "Antall filer er mer enn 10. Vennligst bekreft at dette er ønskelig.",
                QMessageBox.Ok | QMessageBox.Cancel
            )
            if reply == QMessageBox.Cancel:
                return

        self.unified_dialog.reset()

        worker = ApplyScreenshotsWorker(self.game_screenshot_path, self.ui.delete_existings.isChecked())
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
        self.unified_dialog.cancel_button.setStyleSheet("background-color: green; color: white;")
        try:
            self.unified_dialog.cancel_button.clicked.disconnect()
        except Exception:
            pass
        self.unified_dialog.cancel_button.clicked.connect(self.unified_dialog.close)

    def clear_images(self):
        shutil.rmtree(self.game_screenshot_path, ignore_errors=True)
        os.makedirs(self.game_screenshot_path)

    def open_images_folder(self):
        os.startfile(self.game_screenshot_path)

    def loading_editor_cs2_description(self, description_text: str):
        file_name = os.path.join(get_cs2_path(), "game", "csgo_addons", get_addon_name(), "maps", f"{get_addon_name()}.txt")
        with open(file_name, "w") as f:
            f.write("COMMUNITYMAPCREDITS:\n")
            f.write(description_text)

    def icon_processs(self):
        svg_path = self.svg_preview_widget.get_svg_path()
        svg_path = os.path.normpath(svg_path)
        folder_path = os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name(), "panorama", "images", "map_icons")
        os.makedirs(folder_path, exist_ok=True)
        svg_dst = os.path.join(folder_path, f"map_icon_{get_addon_name()}.svg")
        if os.path.exists(svg_dst):
            os.remove(svg_dst)
        shutil.copy2(svg_path, svg_dst)

    def do_loading_editor_cs2_description(self):
        self.loading_editor_cs2_description(self.ui.PlainTextEdit_Description_2.toPlainText())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Loading_editorMainWindow()
    window.show()
    sys.exit(app.exec())