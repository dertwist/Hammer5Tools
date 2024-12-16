import json
import os
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QDialog, QFileDialog, QMessageBox,
    QLabel, QPushButton, QWidget, QHBoxLayout, QListWidgetItem,
    QMenu, QPlainTextEdit
)
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDrag, QShortcut, QKeySequence, QAction, QTextCursor
from src.BatchCreator.ui_main import Ui_BatchCreator_MainWindow
from src.BatchCreator.ui_dialog import Ui_BatchCreator_process_Dialog
from src.preferences import get_addon_name, get_cs2_path
from src.BatchCreator.highlighter import CustomHighlighter
from src.explorer.main import Explorer
from src.qt_styles.common import qt_stylesheet_button, qt_stylesheet_checkbox
from src.BatchCreator.objects import default_file
from src.BatchCreator.dialog import BatchCreatorProcessDialog
from src.BatchCreator.process import *


class BatchCreatorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_BatchCreator_MainWindow()
        self.ui.setupUi(self)

        self.current_file_path = None
        self.opened_file = None
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
        self.initialize_shortcuts()
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

        self.setup_drag_and_drop_labels()

    def setup_drag_and_drop_labels(self):
        self.setup_drag_drop_label(self.ui.folder_path_template, "Folder path")
        self.setup_drag_drop_label(self.ui.assets_name_template, "Asset name")

    def setup_drag_drop_label(self, label_widget, placeholder_type):
        label_widget.setAcceptDrops(True)
        label_widget.dragEnterEvent = self.handle_drag_enter
        label_widget.dropEvent = lambda event: self.handle_label_drop(event, label_widget)
        label_widget.mousePressEvent = lambda event: self.handle_label_mouse_press(event, placeholder_type)

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

    def initialize_shortcuts(self):
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_file)

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
        if self.opened_file is not None:
            self.ui.groupBox_3.show()
            self.ui.kv3_QplainTextEdit.show()
            self.ui.label_editor_placeholder.hide()
        else:
            self.ui.groupBox_3.hide()
            self.ui.kv3_QplainTextEdit.hide()
            self.ui.label_editor_placeholder.show()

    def update_explorer_title(self):
        if self.opened_file:
            folder_name = os.path.basename(self.opened_file)
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
            self.current_file_path = file_path if not self.explorer.model.isDir(index) else None
        else:
            self.relative_path = None
            self.current_file_path = None
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

        batch_file_path = os.path.join(directory_path, f"{file_name}.h5t_batch")
        self.create_batch_file(batch_file_path)

    def create_batch_file(self, file_path):
        try:
            with open(file_path, 'w') as file:
                json.dump(default_file, file, indent=4)
            print(f"Batch file created at: {file_path}")
        except Exception as e:
            print(f"Failed to create batch file: {e}")

    def save_file(self):
        if self.current_file_path:
            content = self.ui.kv3_QplainTextEdit.toPlainText()
            extension = self.ui.extension_lineEdit.text()
            self.write_batch_file(self.current_file_path, content, self.process_data, extension)
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
            self.current_file_path = file_path
            if not self.explorer.model.isDir(index):
                if os.path.splitext(file_path)[1] != ".h5t_batch":
                    msg_box = QMessageBox(self)
                    msg_box.setIcon(QMessageBox.Warning)
                    msg_box.setWindowTitle("Invalid File Extension")
                    msg_box.setText("Please select a file with the .h5t_batch extension.")
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
            self.opened_file = file_path
            self.update_explorer_title()
            print(f"File opened from: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "File Open Error", f"An error occurred while opening the file: {e}")

    def show_process_options(self):
        if not hasattr(self, 'process_dialog') or not self.process_dialog.isVisible():
            self.process_dialog = BatchCreatorProcessDialog(
                process=self.process_data,
                current_file_path=self.current_file_path,
                parent=self,
                process_all=self.process_all_files
            )
            self.process_dialog.show()

    def process_all_files(self):
        self.save_file()
        created_files = self.perform_batch_processing(
            current_path_file=self.current_file_path,
            process=self.process_data,
            preview=False
        )
        self.created_files.extend(created_files)
        if created_files:
            self.ui.return_button.setEnabled(True)

    def perform_batch_processing(self, current_path_file, process, preview):
        batch_directory = os.path.splitext(current_path_file)[0]
        base_directory = os.path.join(self.cs2_path, 'content', 'csgo_addons', self.addon_name)
        relative_directory = os.path.relpath(batch_directory, base_directory).replace('\\', '/')
        algorithm = int(process.get('algorithm', 0))
        file_extension = self.get_file_extension(current_path_file)
        ignore_extensions = [ext.strip() for ext in process.get('ignore_extensions', '').split(',')]

        files_to_process = self.search_files(batch_directory, algorithm, ignore_extensions, process) if process.get('load_from_the_folder') else process.get('custom_files', [])
        created_files = []

        if preview:
            return self.preview_processing_files(files_to_process, batch_directory, base_directory, file_extension, process)
        else:
            output_directory = batch_directory if process.get('output_to_the_folder') else os.path.join(
                self.cs2_path, 'content', 'csgo_addons', self.addon_name, process.get('custom_output', '')
            )
            self.execute_file_creation(files_to_process, output_directory, relative_directory, file_extension, created_files)
            return created_files

    def get_file_extension(self, file_path):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                return data.get('FILE', {}).get('extension', 'vmdl')
        except (json.JSONDecodeError, FileNotFoundError):
            return 'vmdl'

    def execute_file_creation(self, files, output_path, relative_path, extension, created_files):
        try:
            with open(self.current_file_path, 'r') as file:
                data = json.load(file)
                content_template = data.get('FILE', {}).get('content', '')
        except Exception as e:
            QMessageBox.critical(self, "Processing Error", f"Error reading batch file: {e}")
            return

        for file_name in files:
            processed_content = content_template.replace("#$FOLDER_PATH$#", relative_path).replace("#$ASSET_NAME$#", file_name)
            output_file_path = os.path.join(output_path, f"{file_name}.{extension}")
            try:
                with open(output_file_path, 'w') as output_file:
                    output_file.write(processed_content)
                print(f'File created: {output_file_path}')
                created_files.append(output_file_path)
            except Exception as e:
                print(f"Failed to create file {output_file_path}: {e}")

    def preview_processing_files(self, files, batch_directory, base_directory, extension, process):
        if process.get('load_from_the_folder'):
            files_list_out = []
            for root, dirs, files_in_dir in os.walk(batch_directory):
                for file in files_in_dir:
                    if file not in process.get('ignore_list', []) and not any(file.endswith(ext) for ext in process.get('ignore_extensions', '').split(',')):
                        files_list_out.append(file)
            return files, files_list_out, extension, batch_directory
        else:
            return files, None, extension, batch_directory

    def search_files(self, directory, algorithm, ignore_extensions, process):
        ignore_list = [item.strip() for item in process.get('ignore_list', '').split(',')]
        files_found = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file not in ignore_list and not any(file.endswith(ext) for ext in ignore_extensions):
                    base_name, _ = os.path.splitext(file)
                    files_found.append(base_name)

        if algorithm == 0:
            return self.extract_base_names(files_found)
        elif algorithm == 1:
            return self.extract_base_names_underscore(files_found)
        else:
            return []

    def extract_base_names(self, names):
        return set(name.split('_')[0] for name in names)

    def extract_base_names_underscore(self, names):
        return set(name.rsplit('_', 1)[0] if '_' in name else name for name in names)

    def revert_created_files(self):
        for file_path in self.created_files:
            try:
                os.remove(file_path)
                print(f"Removed file: {file_path}")
            except OSError as e:
                print(f"Error removing file {file_path}: {e}")
        self.created_files.clear()
        self.ui.return_button.setEnabled(False)


