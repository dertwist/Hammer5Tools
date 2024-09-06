from smartprop_editor.ui_variable_frame import Ui_Form


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from soudevent_editor.properties.property_actions import PropertyActions

from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QCursor, QDrag,QAction

from smartprop_editor.variables.int import Var_class_Int
from smartprop_editor.variables.legacy import Var_class_legacy

import ast

class VariableFrame(QWidget):
    def __init__(self, name, var_class, var_value, var_visible_in_editor, widget_list):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.variable_name.setAcceptDrops(False)
        self.name = name
        self.var_class = var_class
        self.var_value = var_value
        self.var_visible_in_editor = var_visible_in_editor


        self.ui.variable_name.setText(name)
        self.ui.variable_class.setText(var_class)
        self.ui.visible_in_editor.setChecked(self.var_visible_in_editor)
        self.ui.visible_in_editor.clicked.connect(self.visible_in_editor)
        self.widget_list = widget_list
        if var_class == 'Int':
            self.ui.layout.insertWidget(0, Var_class_Int(var_value='1'))
        elif var_class == 'Float':
            self.ui.layout.insertWidget(0, Var_class_Int(var_value='1'))
        else:
            self.ui.layout.insertWidget(0, Var_class_legacy(var_value=self.var_value))
        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)

        self.init_ui()

    def show_child(self):
        print(self.ui.show_child.isChecked())
        if not self.ui.show_child.isChecked():
            self.ui.frame_layout.setMaximumSize(16666,0)
        else:
            self.ui.frame_layout.setMaximumSize(16666, 16666)

    def visible_in_editor(self):
        self.var_visible_in_editor = self.ui.visible_in_editor.isChecked()
        print(self.var_visible_in_editor)
    def init_ui(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    mousePressEvent = PropertyActions.mousePressEvent
    mouseMoveEvent = PropertyActions.mouseMoveEvent
    dragEnterEvent = PropertyActions.dragEnterEvent
    dropEvent = PropertyActions.dropEvent
    def show_context_menu(self):
        context_menu = QMenu()
        delete_action = QAction("Delete", context_menu)
        copy_action = QAction("Copy", context_menu)  # Change 'Duplicate' to 'Copy'
        context_menu.addActions([delete_action, copy_action])  # Replace 'duplicate_action' with 'copy_action'

        action = context_menu.exec(QCursor.pos())

        if action == delete_action:
            self.deleteLater()

        elif action == copy_action:
            clipboard = QApplication.clipboard()
            clipboard.setText(f"hammer5tools:smartprop_editor_var;;{self.name};;{self.var_class};;{self.var_value};;{self.var_visible_in_editor}")
