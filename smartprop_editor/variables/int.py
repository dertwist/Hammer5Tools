from smartprop_editor.variables.ui_int import Ui_Widget

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from soudevent_editor.properties.property_actions import PropertyActions
from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QCursor, QDrag, QAction
import ast


class Var_class_Int(QWidget):
    def __init__(self, var_value, var_class):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.var_value = var_value
        self.var_class = var_class
        self.init_ui()


    def init_ui(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    # mousePressEvent = PropertyActions.mousePressEvent
    # mouseMoveEvent = PropertyActions.mouseMoveEvent
    # dragEnterEvent = PropertyActions.dragEnterEvent
    # dropEvent = PropertyActions.dropEvent

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
            clipboard.setText(f"hammer5tools:smartprop_editor;;{self.var_class};;{self.var_value}")
