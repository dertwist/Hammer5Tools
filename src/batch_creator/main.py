import json
import os
from PySide6.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QLineEdit
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDropEvent, QAction, QIcon, QTextCharFormat, QTextCursor
from src.batch_creator.ui_main import Ui_BatchCreator_MainWindow
from src.preferences import get_addon_name, get_cs2_path, debug
from src.batch_creator.highlighter import CustomHighlighter
from src.explorer.main import Explorer
from src.batch_creator.objects import default_file
from src.batch_creator.dialog import BatchCreatorProcessDialog
from src.batch_creator.process import perform_batch_processing
from src.batch_creator.property.frame import PropertyFrame
from src.batch_creator.property.objects import default_replacement, default_replacements
from src.batch_creator.context_menu import ReplacementsContextMenu
from src.preferences import get_config_value, set_config_value
from src.batch_creator.monitor import *
from src.widgets import ErrorInfo

class DragDropLineEdit(QLineEdit):
    fileDropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setPlaceholderText('Path to vmdl, vmat, vsmart')

    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            for url in mime_data.urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    self.fileDropped.emit(file_path)
            event.acceptProposedAction()
        else:
            event.ignore()


class BatchCreatorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_BatchCreator_MainWindow()
        self.ui.setupUi(self)

        self.current_file = None
        self.process_data = default_file['process'].copy()
        self.created_files = []
        self.monitoring_running_state = True
        self.search_results = []
        self.current_search_index = -1

        self.addon_name = get_addon_name()
        self.cs2_path = get_cs2_path()
        self.explorer_directory = os.path.join(self.cs2_path, "content", "csgo_addons", self.addon_name)
        self.replace_reference_editline()


        self.explorer = Explorer(parent=self.ui.left_vertical_frame, tree_directory=self.explorer_directory, addon=self.addon_name, editor_name='BatchCreator')

        self.ui.layout.addWidget(self.explorer.frame)
        self.ui.layout.setContentsMargins(0, 0, 0, 0)
        self.setAcceptDrops(True)

        self.context_menu = ReplacementsContextMenu(self, self.ui.kv3_QplainTextEdit)



        # Connect signals
        self.ui.select_reference_button.clicked.connect(self.select_reference)
        self.ui.reference_editline.fileDropped.connect(self.set_reference)

        self.ui.kv3_QplainTextEdit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.kv3_QplainTextEdit.customContextMenuRequested.connect(self.context_menu.show)
        self.ui.kv3_QplainTextEdit.dropEvent = self.handle_plain_text_drop
        self.init_replacements_editor()
        self.update_editor_visibility()

        self.monitoring_list = MonitoringFileWatcher(self.explorer_directory)
        self.monitoring_list.open_file.connect(self.load_file)
        self.ui.monitoring_content.addWidget(self.monitoring_list)

        self.load_splitter_position()
        self.connect_signals()

    def connect_signals(self):
        """Connect UI signals to their respective slots."""
        self.ui.create_file.clicked.connect(self.create_file)
        self.ui.save_button.clicked.connect(self.save_file)
        self.ui.open_button.clicked.connect(self.open_file)
        self.ui.process_all_button.clicked.connect(self.process_all_files)
        self.ui.process_options_button.clicked.connect(self.show_process_options)
        self.ui.return_button.clicked.connect(self.revert_created_files)
        self.ui.return_button.setEnabled(False)
        self.ui.viewport_searchbar.textChanged.connect(self.perform_search)
        self.ui.viewport_search_previous_button.clicked.connect(self.search_previous)
        self.ui.viewport_search_next_button.clicked.connect(self.search_next)
        self.ui.splitter.splitterMoved.connect(self.save_splitter_position)

    def save_splitter_position(self):
        """Save the splitter position to settings."""
        set_config_value('BatchCreator', 'splitterSizes', self.ui.splitter.sizes())

    def load_splitter_position(self):
        """Load the splitter position from settings."""
        sizes = get_config_value("BatchCreator", 'splitterSizes')
        if sizes:
            sizes = [int(size) for size in sizes]
        else:
            sizes = [448, 220]
        self.ui.splitter.setSizes(sizes)

    def closeEvent(self, event):
        """Override close event to save splitter position."""
        self.save_splitter_position()
        super().closeEvent(event)

    #============================================================<  Referencing  >==========================================================

    def replace_reference_editline(self):
        parent_layout = self.ui.frame_8.layout()


        # Create new DragDropLineEdit
        self.ui.reference_editline = DragDropLineEdit()
        self.ui.reference_editline.setObjectName("reference_editline")

        # Add the new widget to the layout
        parent_layout.insertWidget(1, self.ui.reference_editline)
    def select_reference(self):
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Select Reference File")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setDirectory(self.explorer_directory)
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                selected_file = selected_files[0]
                self.set_reference(selected_file)
    def set_reference(self, ref):
        try:
            ref = os.path.relpath(ref, self.explorer_directory)
            self.ui.reference_editline.setText(str(ref))
        except:
            ErrorInfo("Select a file in the addon folder").exec_()
        self.load_reference()

    def handle_drag_and_drop_reference(self, event: QDropEvent):
        """Handle file drop into the editor."""
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            for url in mime_data.urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    self.set_reference(file_path)
        event.accept()
    def load_reference(self):
        reference = self.ui.reference_editline.text()
        reference_path = os.path.join(get_addon_dir(), reference)
        with open(reference_path, 'r') as file:
            __data = file.read()
        self.ui.kv3_QplainTextEdit.clear()
        self.ui.kv3_QplainTextEdit.setPlainText(str(__data))
        self.highlighter = CustomHighlighter(self.ui.kv3_QplainTextEdit.document())
    #============================================================<  Replacements  >=========================================================
    def init_replacements_editor(self):
        self.ui.new_replacement_button.clicked.connect(lambda :self.new_replacement())
        self.replacements_layout = self.ui.replacements_layout.layout()

    def new_replacement(self, __data: dict = None):
        if __data is None:
            __data = default_replacement
        widget_instance = PropertyFrame(widget_list=self.replacements_layout, _data=__data)
        index = self.replacements_layout.count() - 1
        if index == -1:
            index = 0
        self.replacements_layout.insertWidget(index, widget_instance)

    def populate_replacements(self, replacements: dict = None):
        """Create replacements from dict input."""
        if replacements is None:
            replacements = {}
        else:
            for key, value in replacements.items():
                self.new_replacement(value)

    def collect_replacements(self):
        """Collect replacements into a dictionary."""
        _data = {}
        for index in range(self.replacements_layout.count()):
            widget = self.replacements_layout.itemAt(index).widget()
            if isinstance(widget, PropertyFrame):
                value = widget.value
                value = {index: value}
                _data.update(value)
        return _data

    def get_property_value(self, index):
        """Get dictionary value from widget instance frame."""
        widget_instance = self.replacements_layout.itemAt(index).widget()
        if isinstance(widget_instance, PropertyFrame):
            value = widget_instance.value
            debug(f"Getting PropertyFrame Value: \n {value}")
            return value
        return {}

    def clear_replacements(self):
        """Delete all PropertyFrame widgets in ui.replacements_layout."""
        for i in reversed(range(self.replacements_layout.count())):
            item = self.replacements_layout.itemAt(i)
            widget = item.widget()
            if widget and isinstance(widget, PropertyFrame):
                widget.setParent(None)
                widget.deleteLater()

    #==============================================================<  Viewport  >===========================================================

    def handle_plain_text_drop(self, event: QDropEvent):
        """Handle file drop into the editor."""
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            for url in mime_data.urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    self.load_file_content(file_path)
        event.accept()

    def load_file_content(self, file_path):
        """Load content from a file into the editor."""
        try:
            self.highlighter = CustomHighlighter(self.ui.kv3_QplainTextEdit.document())
            with open(file_path, 'r') as file:
                data = file.read()
            self.ui.kv3_QplainTextEdit.setPlainText(data)
        except Exception as e:
            QMessageBox.critical(self, "File Read Error", f"An error occurred while reading the file: {e}")

    def perform_search(self):
        """Perform search in kv3_QplainTextEdit."""
        search_term = self.ui.viewport_searchbar.text()
        self.search_results.clear()
        self.current_search_index = -1

        if search_term:
            cursor = self.ui.kv3_QplainTextEdit.textCursor()
            document = self.ui.kv3_QplainTextEdit.document()
            cursor.beginEditBlock()

            # Reset formatting only for the search term
            fmt = QTextCharFormat()
            cursor.setPosition(0)
            while not cursor.isNull() and not cursor.atEnd():
                cursor = document.find(search_term, cursor)
                if not cursor.isNull():
                    self.search_results.append(cursor.selectionStart())
                    cursor.mergeCharFormat(fmt)

            # Highlight all occurrences
            highlight_format = QTextCharFormat()
            highlight_format.setBackground(Qt.yellow)  # Example highlight color
            for position in self.search_results:
                cursor.setPosition(position)
                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(search_term))
                cursor.mergeCharFormat(highlight_format)

            cursor.endEditBlock()

        # Update the search label
        self.update_search_label()

    def update_search_label(self):
        """Update the search results label."""
        total_matches = len(self.search_results)
        self.ui.viewport_search_label.setText(f"Found: {total_matches}")

    def search_next(self):
        """Navigate to the next search result."""
        if self.search_results:
            self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
            self.highlight_current_search_result()

    def search_previous(self):
        """Navigate to the previous search result."""
        if self.search_results:
            self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
            self.highlight_current_search_result()

    def highlight_current_search_result(self):
        """Highlight the current search result."""
        if self.search_results:
            cursor = self.ui.kv3_QplainTextEdit.textCursor()
            cursor.setPosition(self.search_results[self.current_search_index])
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.KeepAnchor,
                                len(self.ui.viewport_searchbar.text()))
            self.ui.kv3_QplainTextEdit.setTextCursor(cursor)
            self.ui.kv3_QplainTextEdit.ensureCursorVisible()

    def update_editor_visibility(self):
        """Update the visibility of editor-related widgets based on the current file state."""
        if self.current_file:
            self.ui.editor_widgets.show()
            self.ui.referencing_groupbox.setDisabled(False)
            self.ui.process_groupbox.setDisabled(False)
            self.ui.label_editor_placeholder.hide()
        else:
            self.ui.editor_widgets.hide()
            self.ui.referencing_groupbox.setDisabled(True)
            self.ui.process_groupbox.setDisabled(True)
            self.ui.label_editor_placeholder.show()

    #==============================================================<  Explorer  >===========================================================

    def update_explorer_title(self):
        """Update the title of the explorer based on the current file."""
        if self.current_file:
            folder_name = os.path.basename(self.current_file)
            self.ui.dockWidget.setWindowTitle(f"Explorer ({folder_name})")
        else:
            self.ui.dockWidget.setWindowTitle("Explorer")
        self.update_editor_visibility()

    def get_relative_path(self, file_path):
        """Get the path relative to the addon folder."""
        root_directory = os.path.join(self.cs2_path, "content", "csgo_addons", self.addon_name)
        return os.path.relpath(file_path, root_directory)

    def create_file(self):
        """Create a new file in the selected folder."""
        index = self.explorer.tree.currentIndex()
        if not index.isValid():
            QMessageBox.warning(self, "Invalid Path", "Select a valid folder.")
            return

        model = self.explorer.tree.model()
        file_path = model.filePath(index)

        if not model.isDir(index):
            QMessageBox.warning(self, "Invalid Selection", "Please select a folder.")
            return

        base_directory = os.path.join(self.cs2_path, "content", "csgo_addons", self.addon_name)
        selected_path = os.path.join(base_directory, file_path)
        file_name = os.path.splitext(os.path.basename(file_path))[0]

        if not file_name:
            QMessageBox.warning(self, "Invalid Path", "Select a valid folder.")
            return

        directory_path = os.path.dirname(os.path.normpath(selected_path))
        if not os.path.exists(directory_path):
            QMessageBox.warning(self, "Invalid Path", "The directory does not exist.")
            return

        batch_file_path = os.path.join(directory_path, f"{file_name}.hbat")
        self.write_json_file(batch_file_path, default_file)

    def write_json_file(self, file_path, data):
        """Write data to a JSON file."""
        try:
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)
            print(f"File created: {file_path}")
        except Exception as e:
            print(f"Failed to create file: {e}")

    def save_file(self):
        """Save the current file."""
        if self.current_file:
            content = self.ui.kv3_QplainTextEdit.toPlainText()
            self.process_data['extension'] = self.ui.extension_lineEdit.text()
            self.process_data['reference'] = self.ui.reference_editline.text()
            data = {
                'process': self.process_data,
                'replacements': self.collect_replacements(),
                'file': {'content': content}
            }
            self.write_json_file(self.current_file, data)
        else:
            print("No file is currently opened to save.")

    def open_file(self):
        """Open a file selected in the explorer."""
        indexes = self.explorer.tree.selectionModel().selectedIndexes()
        if indexes:
            index = indexes[0]
            file_path = self.explorer.model.filePath(index)
            self.current_file = file_path
            if not self.explorer.model.isDir(index):
                if os.path.splitext(file_path)[1] != ".hbat":
                    if not self.confirm_open_anyway():
                        return
                self.load_file(file_path)
            else:
                QMessageBox.information(self, "Folder Selected", "You have selected a folder. Please select a file to open.")
        else:
            QMessageBox.information(self, "No File Selected", "No file selected. Please select a file to open.")

    def confirm_open_anyway(self):
        """Confirm opening a file with an unsupported extension."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Invalid File Extension")
        msg_box.setText("Please select a file with the .hbat extension.")
        msg_box.addButton("Open Anyway", QMessageBox.AcceptRole)
        msg_box.addButton("Cancel", QMessageBox.RejectRole)
        response = msg_box.exec()
        return response == QMessageBox.AcceptRole

    def load_file(self, file_path):
        """Load a file's content into the editor."""
        try:
            self.clear_replacements()
            self.highlighter = CustomHighlighter(self.ui.kv3_QplainTextEdit.document())
            self.ui.reference_editline.clear()
            with open(file_path, 'r') as file:
                data = json.load(file)
                content = data.get('file', {}).get('content', '')
                self.process_data = data.get('process', {})
                self.ui.reference_editline.setText(self.process_data.get('reference', ''))
                self.ui.kv3_QplainTextEdit.setPlainText(content)
                self.ui.extension_lineEdit.setText(self.process_data.get('extension', default_file['process']['extension']))
                self.populate_replacements(data.get('replacements', default_replacements))
                self.update_explorer_title()
                print(f"File opened from: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "File Open Error", f"An error occurred while opening the file: {e}")
            raise ValueError
        self.update_editor_visibility()
        self.update_explorer_title()

    def show_process_options(self):
        """Show the process options dialog."""
        if not hasattr(self, 'process_dialog') or not self.process_dialog.isVisible():
            self.process_dialog = BatchCreatorProcessDialog(process=self.process_data, current_file=self.current_file, parent=self, process_all=self.process_all_files, collect_replacements=self.collect_replacements)
            self.process_dialog.show()

    def process_all_files(self):
        """Process all files based on the current settings."""
        self.save_file()
        created_files = perform_batch_processing(file_path=self.current_file, process=self.process_data, preview=False, replacements=self.collect_replacements())
        self.created_files.extend(created_files)
        if created_files:
            self.ui.return_button.setEnabled(True)

    def revert_created_files(self):
        """Delete all files created during processing."""
        for file_path in self.created_files:
            try:
                os.remove(file_path)
                print(f"Removed file: {file_path}")
            except OSError as e:
                print(f"Error removing file {file_path}: {e}")
        self.created_files.clear()
        self.ui.return_button.setEnabled(False)