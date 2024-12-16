import json
import os
from PySide6.QtWidgets import QMainWindow, QApplication, QDialog, QFileDialog, QMessageBox, QLabel, QPushButton, QWidget, QHBoxLayout, QListWidgetItem, QMenu, QPlainTextEdit
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDrag, QShortcut, QKeySequence, QAction, QTextCursor
from src.BatchCreator.ui_main import Ui_BatchCreator_MainWindow
from src.BatchCreator.ui_dialog import Ui_BatchCreator_process_Dialog
from src.preferences import get_addon_name, get_cs2_path
from src.BatchCreator.highlighter import CustomHighlighter
from src.explorer.main import Explorer
from src.qt_styles.common import qt_stylesheet_button, qt_stylesheet_checkbox
from src.BatchCreator.objects import default_file

cs2_path = get_cs2_path()

class BatchCreatorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_BatchCreator_MainWindow()
        self.ui.setupUi(self)
        self.current_file_path = None
        self.opened_file = None
        self.process = {}
        self.created_files = []

        self.highlighter = CustomHighlighter(self.ui.kv3_QplainTextEdit.document())
        tree_directory = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name())
        self.mini_explorer = Explorer(self.ui.left_vertical_frame, tree_directory, get_addon_name(), editor_name='BatchCreator')

        layout = self.ui.layout
        layout.addWidget(self.mini_explorer.frame)
        layout.setContentsMargins(0, 0, 0, 0)
        self.relative_path = None
        self.setAcceptDrops(True)
        self.update_top_status_line()

        self.mini_explorer.tree.selectionModel().selectionChanged.connect(self.update_status_line)
        self.ui.create_file.clicked.connect(self.initialize_file)
        self.ui.save_button.clicked.connect(self.save_file)
        self.ui.open_button.clicked.connect(self.open_file)
        self.setup_drag_and_drop(self.ui.folder_path_template, "Folder path")
        self.setup_drag_and_drop(self.ui.assets_name_template, "Asset name")
        self.ui.process_all_button.clicked.connect(self.process_all)
        self.ui.process_options_button.clicked.connect(self.show_process_options)
        self.ui.return_button.clicked.connect(self.return_files)
        self.ui.return_button.setEnabled(False)

        self.folder_path_action = QAction("Insert Folder Path", self)
        self.folder_path_action.triggered.connect(lambda: self.insert_placeholder("#$FOLDER_PATH$#"))

        self.asset_name_action = QAction("Insert Asset Name", self)
        self.asset_name_action.triggered.connect(lambda: self.insert_placeholder("#$ASSET_NAME$#"))
        self.ui.kv3_QplainTextEdit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.kv3_QplainTextEdit.customContextMenuRequested.connect(self.show_context_menu)
        self.ui.kv3_QplainTextEdit.dropEvent = self.dropEvent_kv3_plain_text

        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_file)

        self.update_editor_status()

    def dropEvent_kv3_plain_text(self, event):
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

    def show_context_menu(self, position):
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

    def update_editor_status(self):
        if self.opened_file is not None:
            self.ui.groupBox_3.show()
            self.ui.kv3_QplainTextEdit.show()
            self.ui.label_editor_placeholder.hide()
        else:
            self.ui.groupBox_3.hide()
            self.ui.kv3_QplainTextEdit.hide()
            self.ui.label_editor_placeholder.show()

    def update_explorer_status(self):
        if self.opened_file is None:
            self.ui.dockWidget.setWindowTitle(f"Explorer")
        else:
            self.ui.dockWidget.setWindowTitle(f"Explorer ({os.path.basename(self.opened_file)})")
        self.update_editor_status()

    def setup_drag_and_drop(self, widget, default_text):
        widget.setAcceptDrops(True)
        widget.dragEnterEvent = self.label_drag_enter_event
        widget.dropEvent = lambda event: self.label_drop_event(event, widget)
        widget.mousePressEvent = lambda event: self.label_mouse_press_event(event, default_text)

    def label_drag_enter_event(self, event: QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def label_drop_event(self, event: QDropEvent, widget):
        if event.mimeData().hasText():
            new_text = event.mimeData().text()
            text_edit = self.ui.kv3_QplainTextEdit
            cursor = text_edit.textCursor()
            cursor.insertText(new_text)
            event.acceptProposedAction()

    def label_mouse_press_event(self, event, default_text):
        if event.button() == Qt.LeftButton:
            mimeData = QMimeData()
            mimeData.setText(f"#${default_text.upper().replace(' ', '_')}$#")
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec(Qt.MoveAction)

    def update_status_line(self):
        try:
            index = self.mini_explorer.tree.selectionModel().selectedIndexes()[0]
            if self.mini_explorer.model.isDir(index):
                file_path = self.mini_explorer.model.filePath(index)
                root_directory = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name())
                relative_path = os.path.relpath(file_path, root_directory)
                self.relative_path = os.path.normpath(relative_path)
            else:
                self.relative_path = None
        except IndexError:
            self.relative_path = None

    def update_top_status_line(self):
        indexes = self.mini_explorer.tree.selectionModel().selectedIndexes()
        if indexes:
            index = indexes[0]
            file_path = self.mini_explorer.model.filePath(index)
            base_name = os.path.basename(os.path.normpath(file_path))
            print(f"Opened File: {base_name}")
            self.current_file_path = file_path if not self.mini_explorer.model.isDir(index) else None
        else:
            self.relative_path = None
            self.current_file_path = None

    def initialize_file(self):
        if self.relative_path is None:
            QMessageBox.warning(self, "Invalid Path", "No path selected. Please select a valid folder.")
            return

        path = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name(), self.relative_path)
        file_name = os.path.basename(os.path.normpath(os.path.splitext(self.relative_path)[0]))
        path_clear = os.path.dirname(os.path.normpath(path))

        if file_name == '.':
            QMessageBox.warning(self, "Invalid Path", "Select folder.")
            return

        file_path = os.path.join(path_clear, f"{file_name}.h5t_batch")
        batch_creator_file_parser_initialize(file_path)

    def save_file(self):
        if self.current_file_path:
            content = self.ui.kv3_QplainTextEdit.toPlainText()
            extension = self.ui.extension_lineEdit.text()
            batch_creator_file_parser_output(content, self.process, extension, self.current_file_path)
        else:
            print("No file is currently opened to save.")

    def open_file(self):
        indexes = self.mini_explorer.tree.selectionModel().selectedIndexes()
        if indexes:
            index = indexes[0]
            file_path = self.mini_explorer.model.filePath(index)
            self.current_file_path = file_path
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
                QMessageBox.information(self, "Folder Selected", "You have selected a folder. Please select a file to open.")
        else:
            QMessageBox.information(self, "No File Selected", "No file selected. Please select a file to open.")
        self.update_top_status_line()

    def show_process_options(self):
        if not hasattr(self, 'process_dialog') or not self.process_dialog.isVisible():
            self.process_dialog = BatchCreatorProcessDialog(process=self.process, current_file_path=self.current_file_path, process_all=self.process_all)
            self.process_dialog.show()

    def process_all(self):
        self.save_file()
        created_files = batchcreator_process_all(current_path_file=self.current_file_path, preview=False, process=self.process)
        self.created_files.extend(created_files)
        if created_files:
            self.ui.return_button.setEnabled(True)

    def return_files(self):
        for file_path in self.created_files:
            try:
                os.remove(file_path)
                print(f"Removed file: {file_path}")
            except OSError as e:
                print(f"Error removing file {file_path}: {e}")
        self.created_files.clear()
        self.ui.return_button.setEnabled(False)

    def _open_file_content(self, file_path):
        try:
            content, extension, self.process = batch_creator_file_parser_parse(file_path)
            self.ui.kv3_QplainTextEdit.setPlainText(content)
            self.ui.extension_lineEdit.setText(extension)
            self.current_file_path = file_path
            self.opened_file = file_path
            print(f"File opened from: {file_path}")
            self.update_explorer_status()
        except Exception as e:
            QMessageBox.critical(self, "File Open Error", f"An error occurred while opening the file: {e}")

class BatchCreatorProcessDialog(QDialog):
    def __init__(self, process, current_file_path, parent=None, process_all=None):
        super().__init__(parent)
        self.ui = Ui_BatchCreator_process_Dialog()
        self.ui.setupUi(self)
        self.setModal(False)
        self.process_all = process_all
        self.process = process
        self.current_file_path = current_file_path

        try:
            self.ui.algorithm_select_comboBox.setCurrentIndex(int(process['algorithm']))
            self.ui.algorithm_select_comboBox.currentIndexChanged.connect(self.on_algorithm_index_changed)
            self.ui.load_from_the_folder_checkBox.setChecked(process['load_from_the_folder'])
            self.ui.output_to_the_folder_checkBox.setChecked(process['output_to_the_folder'])

            self.ui.load_from_the_folder_checkBox.stateChanged.connect(self.on_load_from_folder_changed)
            self.ui.output_to_the_folder_checkBox.stateChanged.connect(self.on_output_to_folder_changed)

            self.ui.ignore_extensions_lineEdit.setText(process['ignore_extensions'])
            self.ui.ignore_extensions_lineEdit.textChanged.connect(self.on_ignore_extensions_changed)

            self.ui.ignore_files_lineEdit.setText(process['ignore_list'])
            self.ui.ignore_files_lineEdit.textChanged.connect(self.on_ignore_files_changed)

            self.ui.select_files_to_process_button.clicked.connect(self.on_pressed_select_files_to_process_button)
            self.ui.choose_output_button.clicked.connect(self.on_pressed_choose_output_button)

            self.ui.process_button.clicked.connect(self.process_all)
            self.process_preview()
        except KeyError as e:
            QMessageBox.critical(self, "Initialization Error", f"An error occurred during initialization: {e}")

    def on_load_from_folder_changed(self, state):
        self.process['load_from_the_folder'] = bool(state)
        self.process_preview()

    def on_output_to_folder_changed(self, state):
        self.process['output_to_the_folder'] = bool(state)
        self.process_preview()

    def on_ignore_extensions_changed(self, text):
        self.process['ignore_extensions'] = text
        self.process_preview()

    def on_ignore_files_changed(self, text):
        self.process['ignore_list'] = text
        self.process_preview()

    def on_algorithm_index_changed(self, index):
        self.process['algorithm'] = index
        self.process_preview()

    def on_pressed_choose_output_button(self):
        file_path = QFileDialog.getExistingDirectory(self, "Select Folder to Process", os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name()), options=QFileDialog.ShowDirsOnly)
        if file_path:
            self.process['custom_output'] = os.path.relpath(file_path, os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name()))
            self.process_preview()

    def on_pressed_select_files_to_process_button(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files to Process", "", "All Files (*)")
        if file_paths:
            base_names = [os.path.basename(file_path) for file_path in file_paths]
            self.process['custom_files'] = base_names
            self.process_preview()

    def process_preview(self):
        files = batchcreator_process_all(self.current_file_path, preview=True, process=self.process)
        self.ui.Input_files_preview_scrollarea.clear()
        self.ui.output_files_preview_scrollarea.clear()

        if self.process['load_from_the_folder']:
            for index, item in enumerate(files[1]):
                label = QLabel(item)
                remove_button = QPushButton('Ignore')
                remove_button.setStyleSheet(qt_stylesheet_button)

                def ignore_item(item):
                    scroll_position = self.ui.Input_files_preview_scrollarea.verticalScrollBar().value()
                    self.process['ignore_list'] += f",{item}"
                    self.process_preview()
                    item_widget.deleteLater()
                    self.ui.Input_files_preview_scrollarea.verticalScrollBar().setValue(scroll_position)

                remove_button.clicked.connect(lambda _, item=item: ignore_item(item))

                item_widget = QWidget()
                h_layout = QHBoxLayout()
                h_layout.addWidget(label)
                remove_button.setMaximumWidth(64)
                h_layout.addWidget(remove_button)
                h_layout.setContentsMargins(0, 4, 0, 0)
                item_widget.setLayout(h_layout)

                list_item = QListWidgetItem()
                list_item.setSizeHint(item_widget.sizeHint())

                self.ui.Input_files_preview_scrollarea.addItem(list_item)
                self.ui.Input_files_preview_scrollarea.setItemWidget(list_item, item_widget)
        else:
            files_list = self.process['custom_files']
            for item in files_list:
                label = QLabel(item)
                list_item = QListWidgetItem()
                self.ui.Input_files_preview_scrollarea.addItem(list_item)
                self.ui.Input_files_preview_scrollarea.setItemWidget(list_item, label)

        self.ui.ignore_files_lineEdit.setText(self.process['ignore_list'])
        self.ui.output_files_preview_scrollarea.clear()
        for item in files[0]:
            label = QLabel(item + f".{files[2]}")
            self.ui.output_files_preview_scrollarea.addItem(label.text())

        if self.process['output_to_the_folder']:
            self.ui.output_folder.setText(f'Output folder: {os.path.relpath(files[3], os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name()))}')
        else:
            self.ui.output_folder.setText(f'Output folder: {self.process["custom_output"]}')


def batch_creator_file_parser_parse(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            content = data.get('FILE', {}).get('content')
            extension = data.get('FILE', {}).get('extension')
            process = data.get('PROCESS', {})
            return content, extension, process
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"An error occurred: {e}")
        return None, None, None

def batch_creator_file_parser_output(content, process, extension, file_path):
    data = {
        'FILE': {'content': content, 'extension': extension},
        'PROCESS': process
    }
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
        print(f"File created at: {file_path}")
    except Exception as e:
        print(f"Failed to create file: {e}")

def batch_creator_file_parser_initialize(file_path):
    data = default_file
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
        print(f"File created at: {file_path}")
    except Exception as e:
        print(f"Failed to create file: {e}")

def batchcreator_process_all(current_path_file, process, preview):
    folder_path = os.path.splitext(current_path_file)[0]
    prefix_path = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name())
    folder_path_relative = os.path.relpath(folder_path, prefix_path).replace('\\', '/')
    algorithm = int(process['algorithm'])
    extension = batch_creator_file_parser_parse(current_path_file)[1]
    ignore_extensions = [item for item in process['ignore_extensions'].split(',')]

    files_r = search_files(folder_path, algorithm, ignore_extensions, process) if process['load_from_the_folder'] else process['custom_files']

    created_files = []

    if preview:
        files_list_out = []
        if process['load_from_the_folder']:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file not in process['ignore_list'] and not any(file.endswith(ext) for ext in ignore_extensions):
                        files_list_out.append(file)
            return files_r, files_list_out, extension, folder_path
        else:
            return files_r, None, extension, folder_path
    else:
        def do_process(path):
            content = batch_creator_file_parser_parse(current_path_file)[0]
            for item in files_r:
                content_out = content.replace("#$FOLDER_PATH$#", folder_path_relative).replace("#$ASSET_NAME$#", item)
                filename = os.path.join(path, item) + f".{extension}"
                with open(filename, 'w') as file:
                    file.write(content_out)
                print(f'File {filename} created successfully.')
                created_files.append(filename)

        if process['output_to_the_folder']:
            do_process(folder_path)
        else:
            folder_path = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), process['custom_output'])
            do_process(folder_path)

    return created_files

def search_files(directory, algorithm, ignore_extensions, process):
    ignore_list = [item.strip() for item in process['ignore_list'].split(',')]
    files_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file not in ignore_list and not any(file.endswith(ext) for ext in ignore_extensions):
                file_name = os.path.splitext(file)
                files_list.append(file_name)

    if algorithm == 0:
        return extract_base_names_extension(files_list)
    elif algorithm == 1:
        return extract_base_names_from_end_underscore(files_list)
    else:
        return None, None

def extract_base_names_from_end_underscore(names, path=False):
    base_names = set()
    if path:
        for name in names:
            base_name = os.path.basename(name[0]).rsplit('_', 1)[0]
            base_names.add(base_name)
    else:
        for name in names:
            base_name = name[0].rsplit('_', 1)[0]
            base_names.add(base_name)
    return base_names

def extract_base_names_extension(names, path=False):
    base_names = set()
    if path:
        for name in names:
            base_name = os.path.splitext(os.path.basename(name))[0]
            base_names.add(base_name)
    else:
        for name in names:
            base_name = os.path.splitext(name[0])[0]
            base_names.add(base_name)
    return base_names