from BatchCreator.ui_BatchCreator_main import Ui_BatchCreator_MainWindow
from BatchCreator.BatchCreator_mini_windows_explorer import MiniWindowsExplorer
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QApplication, QLabel
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDrag
from PySide6.QtCore import Qt, QUrl, QMimeData
from preferences import get_addon_name, get_cs2_path
import os

cs2_path = get_cs2_path()

class BatchCreatorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_BatchCreator_MainWindow()
        self.ui.setupUi(self)

        tree_directory = rf"{cs2_path}\content\csgo_addons\{get_addon_name()}"

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

        # Connect the selection change event to the custom slot
        self.mini_explorer.tree.selectionModel().selectionChanged.connect(self.update_status_line)

        self.ui.folder_path_template.setAcceptDrops(True)
        self.ui.folder_path_template.dragEnterEvent = self.label_dragEnterEvent
        self.ui.folder_path_template.dropEvent = lambda event: self.label_dropEvent(event, self.ui.folder_path_template)
        self.ui.folder_path_template.mousePressEvent = lambda event: self.label_mousePressEvent(event, self.ui.folder_path_template)

        self.ui.assets_name_template.setAcceptDrops(True)
        self.ui.assets_name_template.dragEnterEvent = self.label_dragEnterEvent
        self.ui.assets_name_template.dropEvent = lambda event: self.label_dropEvent(event, self.ui.assets_name_template)
        self.ui.assets_name_template.mousePressEvent = lambda event: self.label_mousePressEvent(event, self.ui.assets_name_template)

    def label_dragEnterEvent(self, event: QDragEnterEvent):
        # Accept the event if it contains text data
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def label_dropEvent(self, event: QDropEvent, widget):
        # Handle text drops for label
        if event.mimeData().hasText():
            widget.setText(event.mimeData().text())
            event.acceptProposedAction()

    def label_mousePressEvent(self, event, widget):
        if event.button() == Qt.LeftButton:
            mimeData = QMimeData()
            if widget.text() == "Folder path":
                mimeData.setText("%%#$%%FOLDER_PATH%%$#%%")
            elif widget.text() == "Asset name":
                mimeData.setText("%%#$%%ASSET_NAME%%$#%%")
            else:
                pass
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec(Qt.MoveAction)

    def copy_status_line_to_clipboard(self):
        # Get the text from Status_Line_Qedit
        status_line_text = self.ui.Status_Line_Qedit.toPlainText()
        # Copy the text to the clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(status_line_text)

    def update_status_line(self, selected, deselected):
        # Get the selected indexes
        indexes = self.mini_explorer.tree.selectionModel().selectedIndexes()
        if indexes:
            # Get the first selected index
            index = indexes[0]
            # Get the file path from the model
            file_path = self.mini_explorer.model.filePath(index)
            # Check if the selected item is a directory
            if self.mini_explorer.model.isDir(index):
                # Normalize paths and remove the base path
                base_path = os.path.normpath(rf"{cs2_path}\content\csgo_addons\{get_addon_name()}")
                file_path = os.path.normpath(file_path)
                relative_path = os.path.relpath(file_path, base_path)
                print(relative_path)
                self.ui.Status_Line_Qedit.setPlainText(relative_path)
            else:
                # Clear the status line if the selected item is not a directory
                self.ui.Status_Line_Qedit.clear()
        else:
            # Clear the status line if no item is selected
            self.ui.Status_Line_Qedit.clear()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            # Check which label is the target of the drop event
            if self.childAt(event.position().toPoint()) == self.ui.assets_name_template:
                self.ui.assets_name_template.setText(file_path)
            elif self.childAt(event.position().toPoint()) == self.ui.folder_path_template:
                self.ui.folder_path_template.setText(file_path)