from BatchCreator.ui_BatchCreator_main import Ui_BatchCreator_MainWindow
from BatchCreator.BatchCreator_mini_windows_explorer import MiniWindowsExplorer
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QApplication
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDrag
from PySide6.QtCore import Qt, QMimeData
from preferences import get_addon_name, get_cs2_path
import os
from BatchCreator.BatchCreator_custom_highlighter import CustomHighlighter
import configparser

cs2_path = get_cs2_path()

version = "v0.1.0"


class BatchCreatorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_BatchCreator_MainWindow()
        self.ui.setupUi(self)

        # Initialize the path of the currently opened file
        self.current_file_path = None

        # Apply the custom highlighter to the QPlainTextEdit widget
        self.highlighter = CustomHighlighter(self.ui.kv3_QplainTextEdit.document())

        tree_directory = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name())

        # Initialize the mini windows explorer
        self.mini_explorer = MiniWindowsExplorer(self.ui.MiniWindows_explorer, tree_directory)

        # Set up the layout for the audio_files_explorer widget
        self.audio_files_explorer_layout = QVBoxLayout(self.ui.MiniWindows_explorer)
        self.audio_files_explorer_layout.addWidget(self.mini_explorer.tree)
        self.audio_files_explorer_layout.setContentsMargins(0, 0, 0, 0)

        # Disable editing for Status_Line_Qedit
        self.ui.Status_Line_Qedit.setReadOnly(True)

        # Connect the tool button click to the copy function
        self.ui.Copy_from_status_line_toolButton.clicked.connect(self.copy_status_line_to_clipboard)


        # Set up drag and drop for labels
        self.setup_drag_and_drop(self.ui.folder_path_template, "Folder path")
        self.setup_drag_and_drop(self.ui.assets_name_template, "Asset name")
        self.ui.file_initialize_button.clicked.connect(self.file_initialize)

        # Connect save and open buttons
        self.ui.save_button.clicked.connect(self.save_file)
        self.ui.open_button.clicked.connect(self.open_file)

    def setup_drag_and_drop(self, widget, default_text):
        widget.setAcceptDrops(True)
        widget.dragEnterEvent = self.label_dragEnterEvent
        widget.dropEvent = lambda event: self.label_dropEvent(event, widget)
        widget.mousePressEvent = lambda event: self.label_mousePressEvent(event, default_text)

    def label_dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def label_dropEvent(self, event: QDropEvent, widget):
        if event.mimeData().hasText():
            widget.setText(event.mimeData().text())
            event.acceptProposedAction()

    def label_mousePressEvent(self, event, default_text):
        if event.button() == Qt.LeftButton:
            mimeData = QMimeData()
            mimeData.setText(f"%%#$%%{default_text.upper().replace(' ', '_')}%%$#%%")
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec(Qt.MoveAction)

    def copy_status_line_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.ui.Status_Line_Qedit.toPlainText())

    def update_status_line(self):
        indexes = self.mini_explorer.tree.selectionModel().selectedIndexes()
        if indexes:
            index = indexes[0]
            file_path = self.mini_explorer.model.filePath(index)
            if self.mini_explorer.model.isDir(index):
                base_name = os.path.basename(os.path.normpath(file_path))
                self.ui.Status_Line_Qedit.setPlainText(base_name)
                self.ui.status_label.setText(
                    f"Opened File: <span style='color: #b0c27c;'>{base_name}</span> BatchCreator version: <span style='color: #7cc29b;'>{version}</span>")
                self.current_file_path = None  # No file is currently opened
            else:
                base_name = os.path.basename(os.path.normpath(file_path))
                self.ui.Status_Line_Qedit.setPlainText(base_name)
                self.ui.status_label.setText(
                    f"Opened File: <span style='color: #b0c27c;'>{base_name}</span> BatchCreator version: <span style='color: #7cc29b;'>{version}</span>")
                self.current_file_path = file_path  # Store the path of the opened file
        else:
            self.ui.Status_Line_Qedit.clear()
            self.ui.status_label.setText(
                f"Opened File: None BatchCreator version: <span style='color: red;'>{version}</span>")
            self.current_file_path = None  # No file is currently opened

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            target_widget = self.childAt(event.position().toPoint())
            if target_widget in [self.ui.assets_name_template, self.ui.folder_path_template]:
                target_widget.setText(file_path)

    def file_initialize(self):
        path = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name(), self.ui.Status_Line_Qedit.toPlainText())
        file_name = os.path.relpath(self.ui.Status_Line_Qedit.toPlainText())
        path_clear = os.path.dirname(os.path.normpath(path))
        if not path_clear:
            print("No path provided.")
            return

        # Define the file extension
        file_extension = ".hammer5tools_batch"

        # Create the full file path
        file_path = os.path.join(path_clear, f"{file_name}{file_extension}")

        # Create a ConfigParser object
        config = configparser.ConfigParser()

        # Add sections and key-value pairs
        config['APP'] = {
            'name': 'BatchCreator',
            'version': version
        }
        config['CONTENT'] = {
            'file': ""
        }
        config['EXCEPTIONS'] = {
            'example': 'name.extension'
        }

        try:
            # Write the configuration to a file
            with open(file_path, 'w') as configfile:
                config.write(configfile)

            print(f"File created at: {file_path}")
        except Exception as e:
            print(f"Failed to create file: {e}")

    def save_file(self):
        if self.current_file_path:
            try:
                with open(self.current_file_path, 'w') as file:
                    file.write(self.ui.kv3_QplainTextEdit.toPlainText())
                print(f"File saved at: {self.current_file_path}")
            except Exception as e:
                print(f"Failed to save file: {e}")
        else:
            print("No file is currently opened to save.")

    def open_file(self):
        indexes = self.mini_explorer.tree.selectionModel().selectedIndexes()
        if indexes:
            index = indexes[0]
            file_path = self.mini_explorer.model.filePath(index)
            if not self.mini_explorer.model.isDir(index):
                try:
                    with open(file_path, 'r') as file:
                        content = file.read()
                        self.ui.kv3_QplainTextEdit.setPlainText(content)
                    self.current_file_path = file_path  # Store the path of the opened file
                    print(f"File opened from: {file_path}")
                except Exception as e:
                    print(f"Failed to open file: {e}")
            else:
                print("Selected item is a directory, not a file.")
        else:
            print("No file selected.")
        self.update_status_line()