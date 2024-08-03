from BatchCreator.ui_BatchCreator_main import Ui_BatchCreator_MainWindow
from BatchCreator.BatchCreator_mini_windows_explorer import MiniWindowsExplorer
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QApplication, QMessageBox
from PySide6.QtCore import Qt, QMimeData
from preferences import get_addon_name, get_cs2_path
import os
from BatchCreator.BatchCreator_custom_highlighter import CustomHighlighter
from BatchCreator.BatchCreator_file_parser import batch_creator_file_parser_parse, batch_creator_file_parser_initialize, batch_creator_file_parser_output
from BatchCreator.BatchCreator_process import batchcreator_process_all
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDrag, QShortcut, QKeySequence
from PySide6.QtWidgets import QMessageBox

cs2_path = get_cs2_path()
from packaging import version

class BatchCreatorMainWindow(QMainWindow):
    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.ui = Ui_BatchCreator_MainWindow()
        self.ui.setupUi(self)
        self.version = version
        self.current_file_path = None

        self.highlighter = CustomHighlighter(self.ui.kv3_QplainTextEdit.document())
        tree_directory = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name())
        self.mini_explorer = MiniWindowsExplorer(self.ui.MiniWindows_explorer, tree_directory, get_addon_name())

        self.setup_ui()
        self.setup_connections()
        self.update_top_status_line()


    def setup_ui(self):
        layout = QVBoxLayout(self.ui.MiniWindows_explorer)
        layout.addWidget(self.mini_explorer.tree)
        layout.setContentsMargins(0, 0, 0, 0)
        self.ui.Status_Line_Qedit.setReadOnly(True)
        self.setAcceptDrops(True)


    def setup_connections(self):
        self.mini_explorer.tree.selectionModel().selectionChanged.connect(self.update_status_line)
        self.ui.Copy_from_status_line_toolButton.clicked.connect(self.copy_status_line_to_clipboard)
        self.ui.file_initialize_button.clicked.connect(self.file_initialize)
        self.ui.save_button.clicked.connect(self.save_file)
        self.ui.open_button.clicked.connect(self.open_file)
        self.setup_drag_and_drop(self.ui.folder_path_template, "Folder path")
        self.setup_drag_and_drop(self.ui.assets_name_template, "Asset name")
        self.ui.process_all_button.clicked.connect(self.process_all)

        # Create a shortcut for saving the file with Ctrl+S
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_file)

    def process_all(self):
        batchcreator_process_all(self.current_file_path)

    def setup_drag_and_drop(self, widget, default_text):
        widget.setAcceptDrops(True)
        widget.dragEnterEvent = self.label_dragEnterEvent
        widget.dropEvent = lambda event: self.label_dropEvent(event, widget)
        widget.mousePressEvent = lambda event: self.label_mousePressEvent(event, default_text)

    def label_dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def label_dropEvent(self, event: QDropEvent, widget):
        if event.mimeData().hasText():
            widget.setText(event.mimeData().text())
            event.acceptProposedAction()

    def label_mousePressEvent(self, event, default_text):
        if event.button() == Qt.LeftButton:
            mimeData = QMimeData()
            mimeData.setText(f"#${default_text.upper().replace(' ', '_')}$#")
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec(Qt.MoveAction)

    def copy_status_line_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.ui.Status_Line_Qedit.toPlainText())

    def update_status_line(self):
        try:
            index = self.mini_explorer.tree.selectionModel().selectedIndexes()[0]
            if self.mini_explorer.model.isDir(index):
                file_path = self.mini_explorer.model.filePath(index)
                root_directory = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name())
                relative_path = os.path.relpath(file_path, root_directory)
                relative_path = os.path.normpath(relative_path)
                self.ui.Status_Line_Qedit.setPlainText(relative_path)
            else:
                self.ui.Status_Line_Qedit.clear()
        except:
            pass

    def update_top_status_line(self):
        indexes = self.mini_explorer.tree.selectionModel().selectedIndexes()
        if indexes:
            index = indexes[0]
            file_path = self.mini_explorer.model.filePath(index)
            base_name = os.path.basename(os.path.normpath(file_path))
            self.ui.status_label.setText(
                f"Opened File: <span style='color: #b0c27c;'>{base_name}</span> BatchCreator version: <span style='color: #7cc29b;'>{self.version}</span>")
            self.current_file_path = file_path if not self.mini_explorer.model.isDir(index) else None
        else:
            self.ui.Status_Line_Qedit.clear()
            self.ui.status_label.setText(
                f"Opened File: None BatchCreator version: <span style='color: #7cc29b;'>{self.version}</span>")
            self.current_file_path = None

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            target_widget = self.childAt(event.position().toPoint())
            if target_widget in [self.ui.assets_name_template, self.ui.folder_path_template]:
                target_widget.setText(file_path)

    def file_initialize(self):
        path = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name(),self.ui.Status_Line_Qedit.toPlainText())
        file_name = os.path.basename(os.path.normpath(os.path.splitext(self.ui.Status_Line_Qedit.toPlainText())[0]))
        print(file_name + ' file name')
        path_clear = os.path.dirname(os.path.normpath(path))
        print(path_clear + ' path_clear')
        if file_name == '.':
            print("No path provided.")
            QMessageBox.warning(self, "Invalid Path",
                                "Select folder.")
            return

        file_path = os.path.join(path_clear, f"{file_name}.h5t_batch")
        print(file_path)
        batch_creator_file_parser_initialize(self.version, file_path)

    def save_file(self):
        if self.current_file_path:
            exceptions = batch_creator_file_parser_parse(self.current_file_path)[2]
            content = self.ui.kv3_QplainTextEdit.toPlainText()
            extension = self.ui.extension_lineEdit.text()
            batch_creator_file_parser_output(self.version, content, exceptions, extension,  self.current_file_path)
        else:
            print("No file is currently opened to save.")

    def open_file(self):
        indexes = self.mini_explorer.tree.selectionModel().selectedIndexes()
        if indexes:
            index = indexes[0]
            file_path = self.mini_explorer.model.filePath(index)
            if not self.mini_explorer.model.isDir(index):
                if os.path.splitext(file_path)[1] != ".h5t_batch":
                    msg_box = QMessageBox(self)
                    msg_box.setIcon(QMessageBox.Warning)
                    msg_box.setWindowTitle("Invalid File Extension")
                    msg_box.setText("Please select a file with the .h5t_batch extension.")
                    msg_box.addButton("Open Anyway", QMessageBox.AcceptRole)
                    msg_box.addButton("Cancel", QMessageBox.RejectRole)
                    response = msg_box.exec()

                    if response == 2:
                        self._open_file_content(file_path)
                        self.update_top_status_line()
                    else:
                        return
                try:
                    self._open_file_content(file_path)
                except Exception as e:
                    QMessageBox.critical(self, "File Open Error", f"An error occurred while opening the file: {e}")
            else:
                QMessageBox.information(self, "Folder Selected",
                                        "You have selected a folder. Please select a file to open.")
        else:
            QMessageBox.information(self, "No File Selected", "No file selected. Please select a file to open.")
        self.update_top_status_line()

    def _open_file_content(self, file_path):
        try:
            version_file, content, _, extension = batch_creator_file_parser_parse(file_path)

            # Compare versions
            if version.parse(self.version) > version.parse(version_file):
                QMessageBox.information(self, "Attention",
                                        f"The current version ({self.version}) is newer than the file version ({version_file}).")

            self.ui.kv3_QplainTextEdit.setPlainText(content)
            self.ui.extension_lineEdit.setText(extension)
            self.current_file_path = file_path
            print(f"File opened from: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "File Open Error", f"An error occurred while opening the file: {e}")