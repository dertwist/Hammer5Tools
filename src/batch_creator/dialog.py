import os
import json
import re
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QMessageBox, QLabel, QPushButton, QWidget,
    QHBoxLayout, QListWidgetItem, QApplication, QListWidget, QMenu
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction
from src.batch_creator.ui_dialog import Ui_BatchCreator_process_Dialog
from src.preferences import get_addon_name, get_cs2_path, get_addon_dir
from src.qt_styles.common import qt_stylesheet_button
from src.batch_creator.process import perform_batch_processing
from src.common import enable_dark_title_bar


class BatchCreatorProcessDialog(QDialog):
    def __init__(self, process, current_file, parent=None, process_all=None, collect_replacements=None, viewport=None):
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

    def initialize_ui(self):
        try:
            self.ui.algorithm_select_comboBox.setCurrentIndex(int(self.process_data.get('algorithm', 0)))
            self.ui.load_from_the_folder_checkBox.setChecked(self.process_data.get('load_from_the_folder', False))
            self.ui.output_to_the_folder_checkBox.setChecked(self.process_data.get('output_to_the_folder', False))
            self.ui.ignore_extensions_lineEdit.setText(self.process_data.get('ignore_extensions', ''))
            self.ui.ignore_files_lineEdit.setText(self.process_data.get('ignore_list', ''))
        except KeyError as e:
            QMessageBox.critical(self, "Initialization Error", f"Missing configuration: {e}")

    def connect_signals(self):
        self.ui.algorithm_select_comboBox.currentIndexChanged.connect(self.on_algorithm_changed)
        self.ui.load_from_the_folder_checkBox.stateChanged.connect(self.on_load_from_folder_toggled)
        self.ui.output_to_the_folder_checkBox.stateChanged.connect(self.on_output_to_folder_toggled)
        self.ui.ignore_extensions_lineEdit.textChanged.connect(self.on_ignore_extensions_changed)
        self.ui.ignore_files_lineEdit.textChanged.connect(self.on_ignore_files_changed)
        self.ui.select_files_to_process_button.clicked.connect(self.select_files_to_process)
        self.ui.choose_output_button.clicked.connect(self.choose_output_directory)
        self.ui.process_button.clicked.connect(self.process_all_files)
        self.ui.paste_files_to_process_button.clicked.connect(self.paste_files_from_clipboard)

        self.ui.Input_files_preview_scrollarea.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.Input_files_preview_scrollarea.customContextMenuRequested.connect(self.show_context_menu)

    def on_algorithm_changed(self, index):
        self.process_data['algorithm'] = index
        self.update_previews()

    def on_load_from_folder_toggled(self, state):
        is_checked = bool(state)
        self.process_data['load_from_the_folder'] = is_checked
        self.ui.select_files_to_process_button.setEnabled(not is_checked)
        self.ui.paste_files_to_process_button.setEnabled(not is_checked)
        self.update_previews()

    def on_output_to_folder_toggled(self, state):
        self.process_data['output_to_the_folder'] = bool(state)
        self.update_previews()

    def on_ignore_extensions_changed(self, text):
        self.process_data['ignore_extensions'] = text
        self.update_previews()

    def on_ignore_files_changed(self, text):
        self.process_data['ignore_list'] = text
        self.update_previews()

    def select_files_to_process(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Files to Process", "", "All Files (*)"
        )
        if file_paths:
            absolute_paths = [os.path.abspath(path) for path in file_paths]
            self.process_data['custom_files'] = absolute_paths
            self.update_previews()

    def choose_output_directory(self):
        default_output = os.path.join(
            self.parent_window.cs2_path, 'content', 'csgo_addons', self.parent_window.addon_name
        )
        selected_directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", default_output, options=QFileDialog.ShowDirsOnly
        )
        if selected_directory:
            self.process_data['custom_output'] = os.path.abspath(selected_directory)
            self.update_previews()

    def process_all_files(self):
        if callable(self.process_all):
            self.process_all()

    def update_previews(self):
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
                base_name = os.path.basename(file)
                list_item = QListWidgetItem(base_name)
                input_preview.addItem(list_item)
                list_item.setSizeHint(item_widget.sizeHint())
                input_preview.setItemWidget(list_item, item_widget)
        else:
            for file in self.process_data.get('custom_files', []):
                absolute_path = os.path.abspath(file)
                base_name = os.path.basename(file)
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

    def create_preview_item(self, file_name):
        label = QLabel(file_name)
        remove_button = QPushButton('Ignore')
        remove_button.setStyleSheet(qt_stylesheet_button)
        remove_button.setMaximumWidth(64)

        def ignore_file():
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

    def paste_files_from_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text().strip()

        if not clipboard_text:
            QMessageBox.information(self, "Paste Files", "Clipboard is empty.")
            return

        # Split clipboard text into lines, supporting different newline characters
        raw_paths = re.split(r'\r?\n|\r', clipboard_text)
        addon_dir = get_addon_dir()

        added_files = []
        skipped_files = []

        existing_files = set(self.process_data.get('custom_files', []))

        for path in raw_paths:
            path = path.strip()
            if not path:
                continue

            # Determine if the path is absolute or relative
            if os.path.isabs(path):
                full_path = os.path.normpath(path)
            else:
                full_path = os.path.abspath(os.path.join(addon_dir, path))

            if full_path in existing_files:
                skipped_files.append((path, "Already in the list"))
                continue

            added_files.append(full_path)
            existing_files.add(full_path)

        if added_files:
            self.process_data.setdefault('custom_files', []).extend(added_files)
            self.update_previews()

        # Prepare feedback message
        message = ""
        if added_files:
            message += f"Added {len(added_files)} file(s) successfully.\n"
        if skipped_files:
            message += f"Skipped {len(skipped_files)} file(s):\n"
            for file, reason in skipped_files:
                message += f"- {file}: {reason}\n"


    def show_context_menu(self, position: QPoint):
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

    def delete_selected_items(self):
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

        # Write updated data back to disk
        self.update_previews()

    def clear_all_items(self):
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