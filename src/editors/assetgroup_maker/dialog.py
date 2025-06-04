import os
import re
from typing import Callable, List, Tuple, Optional
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QMessageBox, QLabel, QPushButton, QWidget,
    QHBoxLayout, QListWidgetItem, QApplication, QListWidget, QMenu
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction, QFont
from src.editors.assetgroup_maker.ui_dialog import Ui_BatchCreator_process_Dialog
from src.settings.main import get_addon_dir
from src.editors.assetgroup_maker.process import perform_batch_processing
from src.common import enable_dark_title_bar
from src.widgets.common import ErrorInfo


class BatchCreatorProcessDialog(QDialog):
    """
    Dialog for batch processing of files with options for customization.

    Attributes:
        process_data (dict): Configuration data for the processing.
        current_file (str): The current file being processed.
        process_all (Callable): Function to process all files.
        collect_replacements (Callable): Function to collect replacement data.
        viewport (QWidget): The viewport widget for displaying content.
    """

    def __init__(self, process: dict, current_file: str, parent: Optional[QWidget] = None,
                 process_all: Optional[Callable] = None, collect_replacements: Optional[Callable] = None,
                 viewport: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.ui = Ui_BatchCreator_process_Dialog()
        self.ui.setupUi(self)
        self.setModal(False)

        enable_dark_title_bar(self)

        self.process_data = process
        self.current_file = current_file
        self.process_all = process_all
        self.parent_window = parent
        self.collect_replacements = collect_replacements
        self.viewport = viewport

        self.initialize_ui()
        self.connect_signals()
        self.update_previews()

    def initialize_ui(self) -> None:
        """Initialize the UI components with the current process data."""
        try:
            self.ui.algorithm_select_comboBox.setCurrentIndex(int(self.process_data.get('algorithm', 0)))
            self.ui.load_from_the_folder_checkBox.setChecked(self.process_data.get('load_from_the_folder', False))
            self.ui.output_to_the_folder_checkBox.setChecked(self.process_data.get('output_to_the_folder', False))
            self.ui.ignore_extensions_lineEdit.setText(self.process_data.get('ignore_extensions', ''))
            self.ui.ignore_files_lineEdit.setText(self.process_data.get('ignore_list', ''))

            # Initialize button states based on checkbox statuses
            self.on_load_from_folder_toggled(self.ui.load_from_the_folder_checkBox.isChecked())
            self.on_output_to_folder_toggled(self.ui.output_to_the_folder_checkBox.isChecked())

            # Set the initial enabled state of the choose_output_button
            is_output_to_folder = self.process_data.get('output_to_the_folder', False)
            self.ui.choose_output_button.setEnabled(not is_output_to_folder)

            # Enable or disable context menu based on "Load from Folder" checkbox
            self.update_context_menu_policy(is_output_to_folder)
        except KeyError as e:
            QMessageBox.critical(self, "Initialization Error", f"Missing configuration: {e}")

    def connect_signals(self) -> None:
        """Connect UI signals to their respective slots."""
        self.ui.algorithm_select_comboBox.currentIndexChanged.connect(self.on_algorithm_changed)
        self.ui.load_from_the_folder_checkBox.stateChanged.connect(self.on_load_from_folder_toggled)
        self.ui.output_to_the_folder_checkBox.stateChanged.connect(self.on_output_to_folder_toggled)
        self.ui.ignore_extensions_lineEdit.textChanged.connect(self.on_ignore_extensions_changed)
        self.ui.ignore_files_lineEdit.textChanged.connect(self.on_ignore_files_changed)
        self.ui.select_files_to_process_button.clicked.connect(self.select_files_to_process)
        self.ui.choose_output_button.clicked.connect(self.choose_output_directory)
        self.ui.process_button.clicked.connect(self.process_all_files)
        self.ui.paste_files_to_process_button.clicked.connect(self.paste_files_from_clipboard)

        # Initially set context menu policy
        self.update_context_menu_policy(self.process_data.get('load_from_the_folder', False))

    def update_context_menu_policy(self, load_from_folder: bool) -> None:
        """Update the context menu policy based on the load_from_folder state."""
        if load_from_folder:
            self.ui.Input_files_preview_scrollarea.setContextMenuPolicy(Qt.NoContextMenu)
            try:
                self.ui.Input_files_preview_scrollarea.customContextMenuRequested.disconnect()
            except TypeError:
                pass  # Signal was not connected
        else:
            self.ui.Input_files_preview_scrollarea.setContextMenuPolicy(Qt.CustomContextMenu)
            self.ui.Input_files_preview_scrollarea.customContextMenuRequested.connect(self.show_context_menu)

    def on_algorithm_changed(self, index: int) -> None:
        """Handle changes in the algorithm selection."""
        self.process_data['algorithm'] = index
        self.update_previews()

    def on_load_from_folder_toggled(self, state: int) -> None:
        """Handle toggling of the load from folder checkbox."""
        is_checked = bool(state)
        self.process_data['load_from_the_folder'] = is_checked
        self.ui.select_files_to_process_button.setEnabled(not is_checked)
        self.ui.paste_files_to_process_button.setEnabled(not is_checked)
        self.update_context_menu_policy(is_checked)
        self.update_previews()

    def on_output_to_folder_toggled(self, state: int) -> None:
        """Handle toggling of the output to folder checkbox."""
        is_checked = bool(state)
        self.process_data['output_to_the_folder'] = is_checked
        self.ui.choose_output_button.setEnabled(not is_checked)
        self.update_previews()

    def on_ignore_extensions_changed(self, text: str) -> None:
        """Handle changes in the ignore extensions line edit."""
        self.process_data['ignore_extensions'] = text
        self.update_previews()

    def on_ignore_files_changed(self, text: str) -> None:
        """Handle changes in the ignore files line edit."""
        self.process_data['ignore_list'] = text
        self.update_previews()

    def select_files_to_process(self) -> None:
        """Open a file dialog to select files for processing."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Files to Process", "", "All Files (*)"
        )
        if file_paths:
            addon_dir = get_addon_dir()
            self._validate_and_add_files(file_paths, addon_dir, from_paste=False)

    def choose_output_directory(self) -> None:
        """Open a directory dialog to select the output directory."""
        default_output = os.path.join(
            self.parent_window.cs2_path, 'content', 'csgo_addons', self.parent_window.addon_name
        )
        selected_directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", default_output, options=QFileDialog.ShowDirsOnly
        )
        if selected_directory:
            self.process_data['custom_output'] = os.path.abspath(selected_directory)
            self.update_previews()

    def process_all_files(self) -> None:
        """Invoke the process_all function if callable."""
        if callable(self.process_all):
            self.process_all()

    def update_previews(self) -> None:
        """Update the previews of input and output files."""
        processed_files = perform_batch_processing(
            file_path=self.current_file,
            process=self.process_data,
            preview=True,
            replacements=self.collect_replacements(),
            content_template=self.viewport.toPlainText()
        )

        input_preview = self.ui.Input_files_preview_scrollarea
        output_preview = self.ui.output_files_preview_scrollarea

        input_preview.clear()
        output_preview.clear()

        if self.process_data.get('load_from_the_folder'):
            for file in processed_files[1]:
                item_widget = self.create_preview_item(file)
                base_name = os.path.splitext(os.path.basename(file))[0]  # Removed extension
                list_item = QListWidgetItem(base_name)
                input_preview.addItem(list_item)
                list_item.setSizeHint(item_widget.sizeHint())
                input_preview.setItemWidget(list_item, item_widget)
        else:
            for file in self.process_data.get('custom_files', []):
                absolute_path = os.path.abspath(file)
                base_name = os.path.splitext(os.path.basename(file))[0]  # Removed extension
                list_item = QListWidgetItem(base_name)
                list_item.setToolTip(absolute_path)
                list_item.setData(Qt.UserRole, absolute_path)
                input_preview.addItem(list_item)

        for output_file in processed_files[0]:
            output_preview.addItem(QListWidgetItem(f"{output_file}.{processed_files[2]}"))

        if self.process_data.get('output_to_the_folder'):
            output_relative_path = os.path.relpath(
                processed_files[3],
                os.path.join(self.parent_window.cs2_path, "content", "csgo_addons", self.parent_window.addon_name)
            )
            output_text = f'Output folder: {output_relative_path}'
        else:
            output_text = f'Output folder: {self.process_data.get("custom_output", "")}'
        self.ui.output_folder.setText(output_text)

    def create_preview_item(self, file_name: str) -> QWidget:
        """Create a preview item widget for a given file name."""
        label = QLabel(file_name)
        remove_button = QPushButton('Ignore')
        qt_stylesheet_button = """
            /* QPushButton default and hover styles */
            QPushButton {
                font: 580 8pt "Segoe UI";
                border: 2px solid black;
                border-radius: 2px;
                border-color: rgba(80, 80, 80, 255);
                height:14px;
                padding-top: 2px;
                padding-bottom:2px;
                padding-left: 4px;
                padding-right: 4px;
                color: #E3E3E3;
                background-color: #1C1C1C;
            }
            QPushButton:hover {
                background-color: #414956;
                color: white;
            }
            QPushButton:pressed {
                background-color: red;
                background-color: #1C1C1C;
                margin: 1 px;
                margin-left: 2px;
                margin-right: 2px;
            }"""

        remove_button.setStyleSheet(qt_stylesheet_button)
        font = QFont()
        font.setPointSize(12)  # Desired font size
        remove_button.setFont(font)
        remove_button.setMaximumWidth(64)

        def ignore_file() -> None:
            current_ignore_list = self.process_data.get('ignore_list', '')
            updated_ignore_list = f"{current_ignore_list},{file_name}".strip(',')
            self.process_data['ignore_list'] = updated_ignore_list
            self.ui.ignore_files_lineEdit.setText(updated_ignore_list)
            self.update_previews()

        remove_button.clicked.connect(ignore_file)

        layout = QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(remove_button)
        layout.setContentsMargins(0, 4, 0, 0)

        container = QWidget()
        container.setLayout(layout)
        return container

    def paste_files_from_clipboard(self) -> None:
        """Paste file paths from the clipboard and add them to the process list."""
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text().strip()

        if not clipboard_text:
            QMessageBox.information(self, "Paste Files", "Clipboard is empty.")
            return

        raw_paths = re.split(r'\r?\n|\r', clipboard_text)
        addon_dir = get_addon_dir()

        self._validate_and_add_files(raw_paths, addon_dir, from_paste=True)

    def _validate_and_add_files(self, paths: List[str], addon_dir: str, from_paste: bool = True) -> Tuple[List[str], List[Tuple[str, str]]]:
        """Validate and add files to the process list."""
        added_files = []
        skipped_files = []
        error_files = []
        existing_files = set(self.process_data.get('custom_files', []))

        for path in paths:
            path = path.strip()
            if not path:
                continue

            # Determine if the path is absolute or relative
            if os.path.isabs(path):
                full_path = os.path.normpath(path)
            else:
                full_path = os.path.abspath(os.path.join(addon_dir, path))

            # Check for file extension
            _, ext = os.path.splitext(full_path)
            if not ext:
                error_files.append(path)
                continue

            if full_path in existing_files:
                skipped_files.append((path, "Already in the list"))
                continue

            added_files.append(full_path)
            existing_files.add(full_path)

        if error_files:
            error_message = "The following files do not have extensions:\n" + "\n".join(error_files)
            ErrorInfo("Wrong format", str(error_message)).exec_()

        if added_files:
            self.process_data.setdefault('custom_files', []).extend(added_files)
            self.update_previews()

        return added_files, skipped_files

    def show_context_menu(self, position: QPoint) -> None:
        """Show the context menu at the given position."""
        sender = self.sender()
        if isinstance(sender, QListWidget):
            menu = QMenu(self)

            delete_action = QAction("Delete Item", self)
            clear_all_action = QAction("Clear All", self)
            paste_action = QAction("Paste", self)

            delete_action.triggered.connect(self.delete_selected_items)
            clear_all_action.triggered.connect(self.clear_all_items)
            paste_action.triggered.connect(self.paste_files_from_clipboard)

            menu.addAction(delete_action)
            menu.addAction(clear_all_action)
            menu.addAction(paste_action)

            menu.exec_(sender.mapToGlobal(position))

    def delete_selected_items(self) -> None:
        """Delete selected items from the input preview list."""
        input_preview = self.ui.Input_files_preview_scrollarea
        selected_items = input_preview.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Delete Item", "No items selected to delete.")
            return
        for item in selected_items:
            full_path = item.data(Qt.UserRole)
            if full_path in self.process_data.get('custom_files', []):
                self.process_data['custom_files'].remove(full_path)
            input_preview.takeItem(input_preview.row(item))

        self.update_previews()

    def clear_all_items(self) -> None:
        """Clear all items from the input preview list."""
        confirmation = QMessageBox.question(
            self,
            "Clear All Items",
            "Are you sure you want to clear all items?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirmation == QMessageBox.Yes:
            self.process_data['custom_files'] = []
            self.ui.Input_files_preview_scrollarea.clear()
            self.update_previews()