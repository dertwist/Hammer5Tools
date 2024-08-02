from BatchCreator.ui_BatchCreator_main import Ui_BatchCreator_MainWindow
from BatchCreator.BatchCreator_mini_windows_explorer import MiniWindowsExplorer
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QApplication
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDrag, QSyntaxHighlighter, QTextCharFormat, QColor
from PySide6.QtCore import Qt, QUrl, QMimeData, QRegularExpression
from preferences import get_addon_name, get_cs2_path
import os


cs2_path = get_cs2_path()




from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
from PySide6.QtCore import QRegularExpression

class CustomHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # Define the format for the custom text
        custom_format = QTextCharFormat()
        custom_format.setForeground(QColor("#C78662"))

        # Define the format for the new keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#FF5733"))  # Example color, change as needed

        # Define the format for text within quotes
        quoted_text_format = QTextCharFormat()
        quoted_text_format.setForeground(QColor("#6bc7c4"))

        # Define the format for FOLDER_PATH pattern
        folder_path_format = QTextCharFormat()
        folder_path_format.setForeground(QColor("#C78662"))  # Example color, change as needed

        # Define the format for ASSET_NAME pattern
        asset_name_format = QTextCharFormat()
        asset_name_format.setForeground(QColor("#C78662"))  # Example color, change as needed

        # Define the new keyword patterns
        keyword_patterns = [
            r"\bTextureAmbientOcclusion\b",
            r"\bTextureColor1\b",
            r"\bTextureRoughness1\b",
            r"\bTextureMetalness1\b",
            r"\bTextureNormal\b"
        ]

        # Add the keyword patterns and their format to the highlighting rules
        for pattern in keyword_patterns:
            regex = QRegularExpression(pattern)
            self.highlighting_rules.append((regex, keyword_format))

        # Add the pattern for text within quotes
        quoted_text_pattern = QRegularExpression(r'"\s*[^"]+\s*"')
        self.highlighting_rules.append((quoted_text_pattern, quoted_text_format))

        # Define the patterns to be highlighted
        patterns = [
            (r"%%#\$%%FOLDER_PATH%%\$#%%", folder_path_format),
            (r"%%#\$%%ASSET_NAME%%\$#%%", asset_name_format)
        ]

        # Add the existing patterns and their format to the highlighting rules
        for pattern, format in patterns:
            regex = QRegularExpression(pattern)
            self.highlighting_rules.append((regex, format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

class BatchCreatorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_BatchCreator_MainWindow()
        self.ui.setupUi(self)

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

        # Connect the selection change event to the custom slot
        self.mini_explorer.tree.selectionModel().selectionChanged.connect(self.update_status_line)

        # Set up drag and drop for labels
        self.setup_drag_and_drop(self.ui.folder_path_template, "Folder path")
        self.setup_drag_and_drop(self.ui.assets_name_template, "Asset name")

    # ... rest of the class methods ...

    def setup_drag_and_drop(self, widget, default_text):
        widget.setAcceptDrops(True)
        widget.dragEnterEvent = self.label_dragEnterEvent
        widget.dropEvent = lambda event: self.label_dropEvent(event, widget)
        widget.mousePressEvent = lambda event: self.label_mousePressEvent(event, widget, default_text)

    def label_dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def label_dropEvent(self, event: QDropEvent, widget):
        if event.mimeData().hasText():
            widget.setText(event.mimeData().text())
            event.acceptProposedAction()

    def label_mousePressEvent(self, event, widget, default_text):
        if event.button() == Qt.LeftButton:
            mimeData = QMimeData()
            mimeData.setText(f"%%#$%%{default_text.upper().replace(' ', '_')}%%$#%%")
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec(Qt.MoveAction)

    def copy_status_line_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.ui.Status_Line_Qedit.toPlainText())

    def update_status_line(self, selected, deselected):
        indexes = self.mini_explorer.tree.selectionModel().selectedIndexes()
        if indexes:
            index = indexes[0]
            file_path = self.mini_explorer.model.filePath(index)
            if self.mini_explorer.model.isDir(index):
                base_path = os.path.normpath(os.path.join(cs2_path, "content", "csgo_addons", get_addon_name()))
                relative_path = os.path.relpath(os.path.normpath(file_path), base_path)
                self.ui.Status_Line_Qedit.setPlainText(relative_path)
            else:
                self.ui.Status_Line_Qedit.clear()
        else:
            self.ui.Status_Line_Qedit.clear()

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