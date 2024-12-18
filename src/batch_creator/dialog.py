import os
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QMessageBox, QLabel, QPushButton, QWidget, QHBoxLayout, QListWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from src.batch_creator.ui_dialog import Ui_BatchCreator_process_Dialog
from src.preferences import get_addon_name, get_cs2_path
from src.qt_styles.common import qt_stylesheet_button
from src.batch_creator.process import perform_batch_processing


class BatchCreatorProcessDialog(QDialog):
    def __init__(self, process, current_file, parent=None, process_all=None, collect_replacements = None):
        super().__init__(parent)
        self.ui = Ui_BatchCreator_process_Dialog()
        self.ui.setupUi(self)
        self.setModal(False)

        self.process_data = process
        self.current_file = current_file
        self.process_all = process_all
        self.parent_window = parent
        self.collect_replacements = collect_replacements

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

    def on_algorithm_changed(self, index):
        self.process_data['algorithm'] = index
        self.update_previews()

    def on_load_from_folder_toggled(self, state):
        self.process_data['load_from_the_folder'] = bool(state)
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
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files to Process", "", "All Files (*)")
        if file_paths:
            base_names = [os.path.basename(file_path) for file_path in file_paths]
            self.process_data['custom_files'] = base_names
            self.update_previews()

    def choose_output_directory(self):
        default_output = os.path.join(self.parent_window.cs2_path, 'content', 'csgo_addons', self.parent_window.addon_name)
        selected_directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", default_output, options=QFileDialog.ShowDirsOnly)
        if selected_directory:
            self.process_data['custom_output'] = os.path.relpath(selected_directory, default_output)
            self.update_previews()

    def process_all_files(self):
        self.process_all()

    def update_previews(self):
        processed_files = perform_batch_processing(
            file_path=self.current_file,
            process=self.process_data,
            preview=True,
            replacements=self.collect_replacements()
        )

        input_preview = self.ui.Input_files_preview_scrollarea
        output_preview = self.ui.output_files_preview_scrollarea

        input_preview.clear()
        output_preview.clear()

        if self.process_data.get('load_from_the_folder'):
            for file in processed_files[1]:
                item_widget = self.create_preview_item(file)
                list_item = QListWidgetItem()
                list_item.setSizeHint(item_widget.sizeHint())
                input_preview.addItem(list_item)
                input_preview.setItemWidget(list_item, item_widget)
        else:
            for file in self.process_data.get('custom_files', []):
                input_preview.addItem(QListWidgetItem(file))

        for output_file in processed_files[0]:
            output_preview.addItem(QListWidgetItem(f"{output_file}.{processed_files[2]}"))

        output_text = (
            f'Output folder: {os.path.relpath(processed_files[3], os.path.join(self.parent_window.cs2_path, "content", "csgo_addons", self.parent_window.addon_name))}'
            if self.process_data.get('output_to_the_folder')
            else f'Output folder: {self.process_data.get("custom_output", "")}'
        )
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