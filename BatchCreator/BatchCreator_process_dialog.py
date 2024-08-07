from BatchCreator.ui_BatchCreator_process_dialog import Ui_BatchCreator_process_Dialog
from PySide6.QtWidgets import QDialog,QLabel, QFileDialog
from distutils.util import strtobool
from BatchCreator.BatchCreator_process import batchcreator_process_all
import os
from preferences import  get_cs2_path, get_addon_name

class BatchCreator_process_Dialog(QDialog):
    def __init__(self, process, current_file_path, parent=None):
        super().__init__(parent)
        self.ui = Ui_BatchCreator_process_Dialog()
        self.ui.setupUi(self)
        self.setModal(True)  # Set the dialog as modal
        self.process = process
        self.current_file_path = current_file_path
        # ['ignore_list', 'custom_files', 'custom_output', 'load_from_the_folder', 'algorithm','output_to_the_folder']
        # Assuming process['algorithm'] is a tuple, you can convert it to a single value before setting the current index
        try:
            self.ui.algorithm_select_comboBox.setCurrentIndex(int(process['algorithm']))
            self.ui.algorithm_select_comboBox.currentIndexChanged.connect(self.on_algorithm_index_changed)
            def bool_from_str(value):
                return bool(strtobool(process[value]))
            self.ui.load_from_the_folder_checkBox.setChecked(bool_from_str('load_from_the_folder'))
            self.ui.output_to_the_folder_checkBox.setChecked(bool_from_str('output_to_the_folder'))

            self.ui.load_from_the_folder_checkBox.stateChanged.connect(self.on_load_from_folder_changed)
            self.ui.output_to_the_folder_checkBox.stateChanged.connect(self.on_output_to_folder_changed)


            self.ui.ignore_extensions_lineEdit.setText(process['ignore_extensions'])
            self.ui.ignore_extensions_lineEdit.textChanged.connect(self.on_ignore_extensions_changed)

            self.ui.ignore_files_lineEdit.setText(process['ignore_list'])
            self.ui.ignore_files_lineEdit.textChanged.connect(self.on_ignore_extensions_changed)

            self.ui.select_files_to_process_button.clicked.connect(self.on_pressed_select_files_to_process_button)
            self.ui.choose_output_button.clicked.connect(self.on_pressed_choose_output_button)

            self.ui.process_button.clicked.connect(self.process_all)
            self.process_preview()
        except:
            pass

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
        file_path = QFileDialog.getExistingDirectory(self, "Select Folder to Process", options=QFileDialog.ShowDirsOnly)
        if file_path:
            self.process['custom_output'] = file_path
            self.process_preview()
    def on_pressed_select_files_to_process_button(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files to Process", "", "All Files (*)")
        if file_paths:
            self.process['custom_files'] = file_paths
            self.process_preview()
    def process_all(self):
        batchcreator_process_all(self.current_file_path, preview=False, process=self.process)
    def process_preview(self):
        files = batchcreator_process_all(self.current_file_path, preview=True, process=self.process)
        print(files)
        self.ui.Input_files_preview_scrollarea.clear()
        self.ui.output_files_preview_scrollarea.clear()
        for item in files[1]:
            label = QLabel(item)
            self.ui.Input_files_preview_scrollarea.addItem(label.text())
        for item in files[0]:
            label = QLabel(item + f".{files[2]}")
            self.ui.output_files_preview_scrollarea.addItem(label.text())
        self.ui.output_folder.setText(f'Output folder: {os.path.relpath(files[3], (os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name())))}')