import json
import os
from PySide6.QtWidgets import QMainWindow, QMessageBox
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDropEvent, QAction, QIcon
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

class BatchCreatorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_BatchCreator_MainWindow()
        self.ui.setupUi(self)

        self.current_file = None
        self.process_data = default_file['process'].copy()
        self.created_files = []
        self.monitoring_running_state = True

        self.cs2_path = get_cs2_path()
        self.addon_name = get_addon_name()

        self.highlighter = CustomHighlighter(self.ui.kv3_QplainTextEdit.document())

        explorer_directory = os.path.join(self.cs2_path, "content", "csgo_addons", self.addon_name)
        self.explorer = Explorer(parent=self.ui.left_vertical_frame, tree_directory=explorer_directory, addon=self.addon_name, editor_name='BatchCreator')

        self.ui.layout.addWidget(self.explorer.frame)
        self.ui.layout.setContentsMargins(0, 0, 0, 0)
        self.setAcceptDrops(True)

        self.context_menu = ReplacementsContextMenu(self, self.ui.kv3_QplainTextEdit)

        self.ui.kv3_QplainTextEdit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.kv3_QplainTextEdit.customContextMenuRequested.connect(self.context_menu.show)
        self.ui.kv3_QplainTextEdit.dropEvent = self.handle_plain_text_drop
        self.init_replacements_editor()
        self.update_editor_visibility()
        self.toggle_monitoring()

        self.connect_signals()

    def connect_signals(self):
        """Connect UI signals to their respective slots."""
        self.ui.create_file.clicked.connect(self.create_file)
        self.ui.save_button.clicked.connect(self.save_file)
        self.ui.open_button.clicked.connect(self.open_file)
        self.ui.process_all_button.clicked.connect(self.process_all_files)
        self.ui.process_options_button.clicked.connect(self.show_process_options)
        self.ui.return_button.clicked.connect(self.revert_created_files)
        self.ui.monitoring_start_toggle_button.clicked.connect(self.toggle_monitoring)
        self.ui.return_button.setEnabled(False)

    def init_replacements_editor(self):
        self.ui.new_replacement_button.clicked.connect(lambda :self.new_replacement())
        self.replacements_layout = self.ui.verticalLayout_11

    def new_replacement(self, __data: dict = None):
        if __data is None:
            __data = default_replacement
        widget_instance = PropertyFrame(widget_list=self.replacements_layout, _data=__data)
        index = self.replacements_layout.count() - 1
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
        while self.replacements_layout.count():
            widget = self.replacements_layout.takeAt(0).widget()
            if widget and isinstance(widget, PropertyFrame):
                widget.deleteLater()

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
            with open(file_path, 'r') as file:
                data = file.read()
            self.ui.kv3_QplainTextEdit.setPlainText(data)
        except Exception as e:
            QMessageBox.critical(self, "File Read Error", f"An error occurred while reading the file: {e}")

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
            data = {
                'file': {'content': content},
                'process': self.process_data,
                'replacements': self.collect_replacements()
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
        self.update_explorer_title()
        self.update_editor_visibility()

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
            with open(file_path, 'r') as file:
                data = json.load(file)
                content = data.get('file', {}).get('content', '')
                self.process_data = data.get('process', {})
                self.ui.kv3_QplainTextEdit.setPlainText(content)
                self.ui.extension_lineEdit.setText(self.process_data.get('extension', default_file['process']['extension']))
                self.populate_replacements(data.get('replacements', default_replacements))
                self.update_explorer_title()
                print(f"File opened from: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "File Open Error", f"An error occurred while opening the file: {e}")

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

    def toggle_monitoring(self):
        """Toggle the monitoring state."""
        self.monitoring_running_state = not self.monitoring_running_state

        if self.monitoring_running_state:
            icon_path = ":/valve_common/icons/tools/common/control_stop.png"
            button_text = "Stop Monitoring"
        else:
            icon_path = ":/valve_common/icons/tools/common/control_play.png"
            button_text = "Start Monitoring"

        self.ui.monitoring_start_toggle_button.setIcon(QIcon(icon_path))
        self.ui.monitoring_start_toggle_button.setText(button_text)