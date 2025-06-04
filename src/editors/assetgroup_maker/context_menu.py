from PySide6.QtWidgets import QMenu, QLineEdit, QPlainTextEdit, QTextEdit, QWidget
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction, QCursor

class ReplacementsContextMenu:
    """
    A context menu for inserting placeholders into text widgets.

    Attributes:
        parent (QWidget): The parent widget for the context menu.
        widget (QWidget): The widget where the context menu will be used.
    """

    def __init__(self, parent: QWidget, widget: QWidget) -> None:
        self.parent = parent
        self.widget = widget
        self._setup_actions()

    def _setup_actions(self) -> None:
        """Initialize actions for the context menu."""
        self.folder_path_action = QAction("Insert Folder Path", self.parent)
        self.folder_path_action.triggered.connect(lambda: self.insert_placeholder("#$FOLDER_PATH$#"))

        self.asset_name_action = QAction("Insert Asset Name", self.parent)
        self.asset_name_action.triggered.connect(lambda: self.insert_placeholder("#$ASSET_NAME$#"))

    def show(self, position: QPoint) -> None:
        """Display custom context menu at the given position."""
        menu = self.widget.createStandardContextMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1C1C1C;
                color: #E3E3E3; 
                border: 1px solid #363639; 
            }
            QMenu::item:selected {
                background-color: #414956;
            }
        """)
        menu.addSeparator()
        menu.addAction(self.folder_path_action)
        menu.addAction(self.asset_name_action)
        menu.exec(QCursor.pos())

    def insert_placeholder(self, placeholder: str) -> None:
        """Insert or replace a placeholder text in the editor."""
        try:
            if isinstance(self.widget, (QPlainTextEdit, QTextEdit)):
                cursor = self.widget.textCursor()
                if cursor.hasSelection():
                    cursor.removeSelectedText()
                cursor.insertText(placeholder)
            elif isinstance(self.widget, QLineEdit):
                current_text = self.widget.text()
                cursor_position = self.widget.cursorPosition()
                selected_text_length = len(self.widget.selectedText())

                # Replace selected text with the placeholder
                if selected_text_length > 0:
                    start = cursor_position
                    end = cursor_position + selected_text_length
                    new_text = current_text[:start] + placeholder + current_text[end:]
                else:
                    # Insert at the cursor position if no text is selected
                    new_text = current_text[:cursor_position] + placeholder + current_text[cursor_position:]

                self.widget.setText(new_text)
                # Move the cursor to the end of the inserted text
                self.widget.setCursorPosition(cursor_position + len(placeholder))
            else:
                print("Unsupported widget type for placeholder insertion.")
        except Exception as e:
            print(f"Error inserting placeholder: {e}")