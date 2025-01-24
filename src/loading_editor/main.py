import os
import shutil
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QProgressDialog
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, Qt
from src.settings.main import get_cs2_path, get_addon_name, debug
from src.loading_editor.ui_main import Ui_Loading_editorMainWindow
from src.loading_editor.svg_drag_and_drop import Svg_Drag_and_Drop
from src.explorer.image_viewer import ExplorerImageViewer
from src.common import compile
from src.widgets import ErrorInfo  # Assuming ErrorInfo is defined in src.widgets


class ApplyScreenshotsSignals(QObject):
    progress = Signal(int)
    error = Signal(str)
    finished = Signal()


class ApplyScreenshotsWorker(QRunnable):
    def __init__(self, game_screenshot_path, content_screenshot_path, delete_existing):
        super().__init__()
        self.game_screenshot_path = game_screenshot_path
        self.content_screenshot_path = content_screenshot_path
        self.delete_existing = delete_existing
        self.signals = ApplyScreenshotsSignals()
        self._is_aborted = False
        self.addon_path = os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name())

    def run(self):
        try:
            # Step 1: Copy files
            if self._is_aborted:
                return
            self.copy_files()
            self.signals.progress.emit(20)

            # Step 2: Rename files
            if self._is_aborted:
                return
            self.rename_files()
            self.signals.progress.emit(40)

            # Step 3: Collect image files
            if self._is_aborted:
                return
            file_list = self.collect_files()
            self.signals.progress.emit(60)

            # Step 4: Delete old vtex files
            if self._is_aborted:
                return
            self.delete_old_vtex()
            self.signals.progress.emit(80)

            # Step 5: Process files
            if self._is_aborted:
                return
            self.process_files(file_list)
            self.signals.progress.emit(100)

            self.signals.finished.emit()
        except Exception as e:
            import traceback
            error_message = traceback.format_exc()
            self.signals.error.emit(error_message)

    def copy_files(self):
        debug(f'Copying files from {self.game_screenshot_path} to {self.content_screenshot_path}')
        if os.path.exists(self.content_screenshot_path):
            shutil.rmtree(self.content_screenshot_path, ignore_errors=True)
        shutil.copytree(self.game_screenshot_path, self.content_screenshot_path)

    def rename_files(self):
        base_path = self.content_screenshot_path
        for file_images_loop_count, file_name in enumerate(os.listdir(base_path)):
            try:
                if file_images_loop_count == 0:
                    file_name_parts = os.path.splitext(file_name)
                    file_extension = file_name_parts[1]
                    new_file_name = f"{get_addon_name()}_png{file_extension}"
                    debug(f'Old name {file_name}, New name {new_file_name}')
                    os.rename(os.path.join(base_path, file_name), os.path.join(base_path, new_file_name))
                else:
                    file_name_parts = os.path.splitext(file_name)
                    file_extension = file_name_parts[1]
                    new_file_name = f"{get_addon_name()}_{file_images_loop_count}_png{file_extension}"
                    debug(f'Old name {file_name}, New name {new_file_name}')
                    os.rename(os.path.join(base_path, file_name), os.path.join(base_path, new_file_name))
            except Exception as e:
                print(f"An error occurred while renaming the file: {file_name}. Error: {e}")

    def collect_files(self):
        debug('Collecting image files from content folder')
        file_list = []
        for root, dirs, files in os.walk(self.content_screenshot_path):
            for file_name in files:
                full_file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(full_file_path, self.addon_path)
                file_list.append(relative_path)
        debug(f'File list: {file_list}')
        return file_list

    def delete_old_vtex(self):
        debug('Deleting old vtex files')
        try:
            shutil.rmtree(os.path.join(self.addon_path, "panorama", "images", "map_icons", "screenshots", "1080p"))
        except Exception as e:
            debug(f'Error deleting old vtex files: {e}')

        if self.delete_existing:
            debug('Deleting compiled vtex_c files because delete_existing is True')
            try:
                shutil.rmtree(os.path.join(get_cs2_path(), "game", "csgo_addons", get_addon_name(),
                                           "panorama", "images", "map_icons", "screenshots", "1080p"))
            except Exception as e:
                debug(f'Error deleting compiled vtex_c files: {e}')

    def process_files(self, file_list):
        total_files = len(file_list)
        for index, item in enumerate(file_list):
            if self._is_aborted:
                return
            debug(f'Processing: {item}')
            self.creating_vtex(item)
            # Update progress (from 80 to 100)
            progress = 80 + int(20 * (index + 1) / total_files)
            self.signals.progress.emit(progress)

    def creating_vtex(self, path):
        vtex_file = """<!-- dmx encoding keyvalues2_noids 1 format vtex 1 -->
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
        vtex_file = vtex_file.replace('%%PATH%%', path.replace('\\', '/'))
        name = os.path.basename(path)
        name = os.path.splitext(name)[0]
        vtex_path = os.path.join(self.addon_path, "panorama", "images", "map_icons", "screenshots", "1080p", f'{name}.vtex')
        os.makedirs(os.path.dirname(vtex_path), exist_ok=True)

        with open(vtex_path, 'w') as file:
            file.write(vtex_file)

        compile(vtex_path)

    def abort(self):
        self._is_aborted = True


class Loading_editorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Loading_editorMainWindow()
        self.ui.setupUi(self)

        self.threadpool = QThreadPool()

        self.game_screenshot_path = os.path.join(get_cs2_path(), "game", "csgo_addons", get_addon_name(), 'screenshots')
        self.content_screenshot_path = os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name(), 'screenshots')
        if not os.path.exists(self.game_screenshot_path):
            os.makedirs(self.game_screenshot_path)

        # Explorer init
        explorer_view = ExplorerImageViewer(tree_directory=self.game_screenshot_path)
        explorer_view.setStyleSheet("padding:0")
        self.ui.explorer.layout().addWidget(explorer_view)
        self.ui.screenshot_preview.layout().addWidget(explorer_view.image_viewer)
        self.ui.splitter_2.setSizes([200, 100])

        self.Svg_Drap_and_Drop_Area = Svg_Drag_and_Drop()
        self.ui.svg_icon_frame.layout().addWidget(self.Svg_Drap_and_Drop_Area)

        # apply_description_button
        self.ui.apply_description_button.clicked.connect(self.do_loading_editor_cs2_description)
        # apply images
        self.ui.apply_screenshots_button.clicked.connect(self.start_apply_screenshots)
        self.ui.apply_icon_button.clicked.connect(self.icon_processs)

        self.ui.clear_all_button.clicked.connect(self.clear_images)
        self.ui.open_folder_button.clicked.connect(self.open_images_folder)

    def start_apply_screenshots(self):
        delete_existing = self.ui.delete_existings.isChecked()

        worker = ApplyScreenshotsWorker(self.game_screenshot_path, self.content_screenshot_path, delete_existing)
        worker.signals.progress.connect(self.update_progress)
        worker.signals.error.connect(self.show_error)
        worker.signals.finished.connect(self.processing_finished)

        # Create a progress dialog
        self.progress_dialog = QProgressDialog("Processing screenshots...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Processing")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.canceled.connect(worker.abort)
        self.progress_dialog.show()

        # Start the worker
        self.threadpool.start(worker)

    def update_progress(self, value):
        self.progress_dialog.setValue(value)

    def show_error(self, error_message):
        self.progress_dialog.close()
        error_dialog = ErrorInfo(text="An error occurred during processing.", details=error_message)
        error_dialog.exec_()

    def processing_finished(self):
        self.progress_dialog.close()
        QMessageBox.information(self, "Processing Complete", "Screenshots have been processed successfully.")

    def clear_images(self):
        shutil.rmtree(self.game_screenshot_path, ignore_errors=True)
        os.makedirs(self.game_screenshot_path)

    def open_images_folder(self):
        os.startfile(self.game_screenshot_path)

    def loading_editor_cs2_description(self, loading_editor_cs2_description_text):
        file_name = os.path.join(get_cs2_path(), "game", "csgo_addons", get_addon_name(), 'maps', f'{get_addon_name()}.txt')
        with open(file_name, 'w') as f:
            f.write("COMMUNITYMAPCREDITS:\n")
            f.write(loading_editor_cs2_description_text)

    def icon_processs(self):
        svg_path = self.Svg_Drap_and_Drop_Area.loading_editor_get_svg()
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