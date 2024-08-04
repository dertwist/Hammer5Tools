from BatchCreator.ui_BatchCreator_process_dialog import Ui_BatchCreator_process_Dialog
from PySide6.QtWidgets import QDialog,QLabel
from distutils.util import strtobool
from BatchCreator.BatchCreator_process import batchcreator_process_all

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
    def on_algorithm_index_changed(self, index):
        self.process['algorithm'] = index
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