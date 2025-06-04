from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtCore import Qt, QMimeData, QTimer
from PySide6.QtGui import QCursor, QDrag,QAction

class SoundEventEditorPropertyMethods:

    # noinspection PyTypeChecker
    @staticmethod
    def show_context_menu(self, event, property_class):
        context_menu = QMenu()
        delete_action = QAction("Delete", context_menu)
        copy_action = QAction("Copy", context_menu)  # Change 'Duplicate' to 'Copy'
        context_menu.addActions([delete_action, copy_action])  # Replace 'duplicate_action' with 'copy_action'

        action = context_menu.exec(QCursor.pos())

        if action == delete_action:
            self.deleteLater()

        elif action == copy_action:
            clipboard = QApplication.clipboard()
            clipboard.setText(f"hammer5tools:soundeventeditor;;{self.name};;{self.value}")