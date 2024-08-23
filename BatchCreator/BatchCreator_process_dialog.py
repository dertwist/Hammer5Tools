from BatchCreator.ui_BatchCreator_process_dialog import Ui_BatchCreator_process_Dialog
from PySide6.QtWidgets import QDialog,QLabel, QFileDialog, QPushButton, QHBoxLayout, QWidget, QListWidgetItem
from distutils.util import strtobool
from BatchCreator.BatchCreator_process import batchcreator_process_all
import os
from preferences import  get_cs2_path, get_addon_name
import ast

class BatchCreator_process_Dialog(QDialog):
    def __init__(self, process, current_file_path, parent=None):
        super().__init__(parent)
        self.ui = Ui_BatchCreator_process_Dialog()
        self.ui.setupUi(self)
        self.setModal(True)
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
            self.ui.ignore_files_lineEdit.textChanged.connect(self.on_ignore_files_changed)

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

    # noinspection PyTypeChecker
    def on_pressed_choose_output_button(self):
        file_path = QFileDialog.getExistingDirectory(self, "Select Folder to Process", os.path.join(get_cs2_path(),'content', 'csgo_addons', get_addon_name()), options=QFileDialog.ShowDirsOnly)
        if file_path:
            self.process['custom_output'] = os.path.relpath(file_path,(os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name())))
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
        self.ui.Input_files_preview_scrollarea.clear()
        self.ui.output_files_preview_scrollarea.clear()

        def str_to_bool(value):
                try:
                    return bool(strtobool(self.process[value]))
                except:
                    return self.process[value]
        if str_to_bool('load_from_the_folder'):
            for index, item in enumerate(files[1]):
                label = QLabel(item)
                # Update the QPushButton stylesheet to make it smaller
                remove_button = QPushButton('Ignore')
                # noinspection PyTypeChecker
                remove_button.setStyleSheet("""
                    QPushButton {
                        font: 700 8pt "Segoe UI";
                        border: 2px solid black;
                        border-radius: 4px;
                        border-color: rgba(80, 80, 80, 255);
                        height: 16px;
                        padding-top: 2px;
                        padding-bottom: 2px;
                        padding-left: 4px;
                        padding-right: 4px;
                        color: #c4c4c4;
                        background-color: #1C1C1C;
                    }
                    QPushButton:hover {
                        background-color: #414956;
                        color: white;
                    }
                    QPushButton:pressed {
                        background-color: #2d323b;
                        margin: 1px;
                        margin-left: 2px;
                        margin-right: 2px;
                    }
                """)

                def ignore_item(item):
                    # Get the current scroll position
                    scroll_position = self.ui.Input_files_preview_scrollarea.verticalScrollBar().value()

                    # Remove the item from the UI
                    self.process['ignore_list'] += f",{item}"
                    self.process_preview()
                    item_widget.deleteLater()

                    # Reset the scroll position after deletion
                    self.ui.Input_files_preview_scrollarea.verticalScrollBar().setValue(scroll_position)

                # Use lambda to capture the current value of item
                remove_button.clicked.connect(lambda _, item=item: ignore_item(item))

                item_widget = QWidget()
                h_layout = QHBoxLayout()
                h_layout.addWidget(label)
                remove_button.setMaximumWidth(64)
                h_layout.addWidget(remove_button)
                h_layout.setContentsMargins(0, 4, 0, 0)
                item_widget.setLayout(h_layout)


                list_item = QListWidgetItem()
                list_item.setSizeHint(item_widget.sizeHint())  # Set the size hint for the item

                self.ui.Input_files_preview_scrollarea.addItem(list_item)
                self.ui.Input_files_preview_scrollarea.setItemWidget(list_item, item_widget)
        else:
            files_list = ast.literal_eval(self.process['custom_files'])
            for item in files_list:
                label = QLabel(item)
                list_item = QListWidgetItem() # Set the size hint for the item

                self.ui.Input_files_preview_scrollarea.addItem(list_item)
                self.ui.Input_files_preview_scrollarea.setItemWidget(list_item, label)
        self.ui.ignore_files_lineEdit.setText(self.process['ignore_list'])
        self.ui.output_files_preview_scrollarea.clear()
        for item in files[0]:

            label = QLabel(item + f".{files[2]}")
            self.ui.output_files_preview_scrollarea.addItem(label.text())

        if str_to_bool('output_to_the_folder'):
            self.ui.output_folder.setText(f'Output folder: {os.path.relpath(files[3], (os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name())))}')

        else:
            self.ui.output_folder.setText(f'Output folder: {self.process['custom_output']}')