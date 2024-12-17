import json
import os
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QDialog, QFileDialog, QMessageBox,
    QLabel, QPushButton, QWidget, QHBoxLayout, QListWidgetItem,
    QMenu, QPlainTextEdit
)
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDrag, QShortcut, QKeySequence, QAction, QTextCursor
from src.batch_creator.ui_main import Ui_BatchCreator_MainWindow
from src.batch_creator.ui_dialog import Ui_BatchCreator_process_Dialog
from src.preferences import get_addon_name, get_cs2_path
from src.batch_creator.highlighter import CustomHighlighter
from src.explorer.main import Explorer
from src.qt_styles.common import qt_stylesheet_button, qt_stylesheet_checkbox
from src.batch_creator.objects import default_file
from src.batch_creator.dialog import BatchCreatorProcessDialog
from src.batch_creator.process import perform_batch_processing


class BatchCreatorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_BatchCreator_MainWindow()
        self.ui.setupUi(self)

        self.current_file = None
        self.process_data = {}
        self.created_files = []

        self.cs2_path = get_cs2_path()
        self.addon_name = get_addon_name()

        self.highlighter = CustomHighlighter(self.ui.kv3_QplainTextEdit.document())

        explorer_directory = os.path.join(
            self.cs2_path,
            "content",
            "csgo_addons",
            self.addon_name
        )
        self.explorer = Explorer(
            parent=self.ui.left_vertical_frame,
            tree_directory=explorer_directory,
            addon=self.addon_name,
            editor_name='BatchCreator'
        )

        self.ui.layout.addWidget(self.explorer.frame)
        self.ui.layout.setContentsMargins(0, 0, 0, 0)
        self.relative_path = None
        self.setAcceptDrops(True)
        self.update_top_status_line()

        self.initialize_connections()
        self.initialize_context_menu()
        self.update_editor_visibility()

    def initialize_connections(self):
        self.explorer.tree.selectionModel().selectionChanged.connect(self.update_status_line)
        self.ui.create_file.clicked.connect(self.initialize_file)
        self.ui.save_button.clicked.connect(self.save_file)
        self.ui.open_button.clicked.connect(self.open_file)
        self.ui.process_all_button.clicked.connect(self.process_all_files)
        self.ui.process_options_button.clicked.connect(self.show_process_options)
        self.ui.return_button.clicked.connect(self.revert_created_files)
        self.ui.return_button.setEnabled(False)

    def initialize_context_menu(self):
        self.folder_path_action = QAction("Insert Folder Path", self)
        self.folder_path_action.triggered.connect(lambda: self.insert_placeholder("#$FOLDER_PATH$#"))

        self.asset_name_action = QAction("Insert Asset Name", self)
        self.asset_name_action.triggered.connect(lambda: self.insert_placeholder("#$ASSET_NAME$#"))

        self.ui.kv3_QplainTextEdit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.kv3_QplainTextEdit.customContextMenuRequested.connect(self.show_custom_context_menu)
        self.ui.kv3_QplainTextEdit.dropEvent = self.handle_plain_text_drop

    def handle_drag_enter(self, event: QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def handle_label_drop(self, event: QDropEvent, label_widget):
        if event.mimeData().hasText():
            inserted_text = event.mimeData().text()
            cursor = self.ui.kv3_QplainTextEdit.textCursor()
            cursor.insertText(inserted_text)
            event.acceptProposedAction()

    def handle_label_mouse_press(self, event, placeholder_type):
        if event.button() == Qt.LeftButton:
            placeholder = f"#${placeholder_type.upper().replace(' ', '_')}$#"
            mime_data = QMimeData()
            mime_data.setText(placeholder)
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            drag.exec(Qt.MoveAction)

    def show_custom_context_menu(self, position):
        menu = self.ui.kv3_QplainTextEdit.createStandardContextMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1C1C1C;
                color: #E3E3E3; 
                border: 1px solid #363639; 
            }
            QMenu::item:selected {
                background-color: #414956;
            }
        """)
        menu.addSeparator()
        menu.addAction(self.folder_path_action)
        menu.addAction(self.asset_name_action)
        menu.exec(self.ui.kv3_QplainTextEdit.mapToGlobal(position))

    def insert_placeholder(self, placeholder):
        cursor = self.ui.kv3_QplainTextEdit.textCursor()
        cursor.insertText(placeholder)

    def handle_plain_text_drop(self, event: QDropEvent):
        if event.source() == self:
            return

        mime_data = event.mimeData()
        if mime_data.hasText():
            urls = mime_data.urls()
            for url in urls:
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, 'r') as file:
                            data = file.read()
                        text_edit = self.ui.kv3_QplainTextEdit
                        cursor = text_edit.textCursor()
                        cursor.select(QTextCursor.Document)
                        cursor.insertText(data)
                    except Exception as e:
                        QMessageBox.critical(self, "File Read Error", f"An error occurred while reading the file: {e}")

        event.accept()

    def update_editor_visibility(self):
        if self.current_file is not None:
            self.ui.editor_widgets.show()
            self.ui.referencing_groupbox.setDisabled(False)
            self.ui.process_groupbox.setDisabled(False)
            self.ui.label_editor_placeholder.hide()
        else:
            self.ui.editor_widgets.hide()
            self.ui.referencing_groupbox.setDisabled(True)
            self.ui.process_groupbox.setDisabled(True)
            self.ui.label_editor_placeholder.show()

    def update_explorer_title(self):
        if self.current_file:
            folder_name = os.path.basename(self.current_file)
            self.ui.dockWidget.setWindowTitle(f"Explorer ({folder_name})")
        else:
            self.ui.dockWidget.setWindowTitle("Explorer")
        self.update_editor_visibility()

    def update_status_line(self):
        try:
            index = self.explorer.tree.selectionModel().selectedIndexes()[0]
            if self.explorer.model.isDir(index):
                file_path = self.explorer.model.filePath(index)
                root_directory = os.path.join(self.cs2_path, "content", "csgo_addons", self.addon_name)
                relative_path = os.path.relpath(file_path, root_directory)
                self.relative_path = os.path.normpath(relative_path)
            else:
                self.relative_path = None
        except IndexError:
            self.relative_path = None

    def update_top_status_line(self):
        indexes = self.explorer.tree.selectionModel().selectedIndexes()
        if indexes:
            index = indexes[0]
            file_path = self.explorer.model.filePath(index)
            base_name = os.path.basename(os.path.normpath(file_path))
            print(f"Opened File: {base_name}")
            self.current_file = file_path if not self.explorer.model.isDir(index) else None
        else:
            self.relative_path = None
            self.current_file = None
        self.update_explorer_title()

    def initialize_file(self):
        if self.relative_path is None:
            QMessageBox.warning(self, "Invalid Path", "No path selected. Please select a valid folder.")
            return

        base_directory = os.path.join(self.cs2_path, "content", "csgo_addons", self.addon_name)
        selected_path = os.path.join(base_directory, self.relative_path)
        file_name = os.path.basename(os.path.splitext(self.relative_path)[0])
        directory_path = os.path.dirname(os.path.normpath(selected_path))

        if file_name == '.':
            QMessageBox.warning(self, "Invalid Path", "Select a valid folder.")
            return

        batch_file_path = os.path.join(directory_path, f"{file_name}.hbat")
        self.create_batch_file(batch_file_path)

    def create_batch_file(self, file_path):
        try:
            with open(file_path, 'w') as file:
                json.dump(default_file, file, indent=4)
            print(f"Batch file created at: {file_path}")
        except Exception as e:
            print(f"Failed to create batch file: {e}")

    def save_file(self):
        if self.current_file:
            content = self.ui.kv3_QplainTextEdit.toPlainText()
            extension = self.ui.extension_lineEdit.text()
            self.write_batch_file(self.current_file, content, self.process_data, extension)
        else:
            print("No file is currently opened to save.")

    def write_batch_file(self, file_path, content, process, extension):
        data = {
            'FILE': {'content': content, 'extension': extension},
            'PROCESS': process
        }
        try:
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)
            print(f"File saved at: {file_path}")
        except Exception as e:
            print(f"Failed to save file: {e}")

    def open_file(self):
        indexes = self.explorer.tree.selectionModel().selectedIndexes()
        if indexes:
            index = indexes[0]
            file_path = self.explorer.model.filePath(index)
            self.current_file = file_path
            if not self.explorer.model.isDir(index):
                if os.path.splitext(file_path)[1] != ".hbat":
                    msg_box = QMessageBox(self)
                    msg_box.setIcon(QMessageBox.Warning)
                    msg_box.setWindowTitle("Invalid File Extension")
                    msg_box.setText("Please select a file with the .hbat extension.")
                    msg_box.addButton("Open Anyway", QMessageBox.AcceptRole)
                    msg_box.addButton("Cancel", QMessageBox.RejectRole)
                    response = msg_box.exec()

                    if response == 2:
                        self.display_file_content(file_path)
                        self.update_top_status_line()
                    else:
                        return
                try:
                    self.display_file_content(file_path)
                except Exception as e:
                    QMessageBox.critical(self, "File Open Error", f"An error occurred while opening the file: {e}")
            else:
                QMessageBox.information(self, "Folder Selected", "You have selected a folder. Please select a file to open.")
        else:
            QMessageBox.information(self, "No File Selected", "No file selected. Please select a file to open.")
        self.update_top_status_line()

    def display_file_content(self, file_path):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                content = data.get('FILE', {}).get('content', '')
                extension = data.get('FILE', {}).get('extension', '')
                self.process_data = data.get('PROCESS', {})

            self.ui.kv3_QplainTextEdit.setPlainText(content)
            self.ui.extension_lineEdit.setText(extension)
            self.update_explorer_title()
            print(f"File opened from: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "File Open Error", f"An error occurred while opening the file: {e}")

    def show_process_options(self):
        if not hasattr(self, 'process_dialog') or not self.process_dialog.isVisible():
            self.process_dialog = BatchCreatorProcessDialog(
                process=self.process_data,
                current_file=self.current_file,
                parent=self,
                process_all=self.process_all_files
            )
            self.process_dialog.show()

    def process_all_files(self):
        self.save_file()
        created_files = perform_batch_processing(
            file_path=self.current_file,
            process=self.process_data,
            preview=False
        )
        self.created_files.extend(created_files)
        if created_files:
            self.ui.return_button.setEnabled(True)

    def get_update_previews_files(self):
        processed_files = perform_batch_processing(
            file_path=self.current_file,
            process=self.process_data,
            preview=True
        )
        return processed_files

    def revert_created_files(self):
        for file_path in self.created_files:
            try:
                os.remove(file_path)
                print(f"Removed file: {file_path}")
            except OSError as e:
                print(f"Error removing file {file_path}: {e}")
        self.created_files.clear()
        self.ui.return_button.setEnabled(False)