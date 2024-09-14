from smartprop_editor.ui_properties_group_frame import Ui_Form


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal
from soudevent_editor.properties.property_actions import PropertyActions

from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QCursor, QDrag,QAction


import ast

class PropertiesGroupFrame(QWidget):
    signal = Signal()
    def __init__(self, widget_list=None, name=None):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.property_class.setAcceptDrops(False)
        self.name = name


        self.layout = self.ui.layout
        self.ui.add_button.clicked.connect(self.add_action)

        self.ui.property_class.setText(self.name)
        self.widget_list = widget_list

        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)

        self.init_ui()
    def add_action(self):
        self.signal.emit()

    def show_child(self):
        if not self.ui.show_child.isChecked():
            self.ui.frame_layout.setMaximumSize(16666,0)
        else:
            self.ui.frame_layout.setMaximumSize(16666, 16666)

    def on_changed(self, var_default=None, var_min=None, var_max=None, var_model=None):
        pass

    def update_self(self):
        pass
    def init_ui(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    mousePressEvent = PropertyActions.mousePressEvent
    mouseMoveEvent = PropertyActions.mouseMoveEvent
    dragEnterEvent = PropertyActions.dragEnterEvent
    dropEvent = PropertyActions.dropEvent
    # def show_context_menu(self):
    #     context_menu = QMenu()
    #     delete_action = QAction("Delete", context_menu)
    #     copy_action = QAction("Copy", context_menu)  # Change 'Duplicate' to 'Copy'
    #     context_menu.addActions([delete_action, copy_action])  # Replace 'duplicate_action' with 'copy_action'
    #
    #     action = context_menu.exec(QCursor.pos())
    #
    #     if action == delete_action:
    #         self.deleteLater()
    #
    #     elif action == copy_action:
    #         clipboard = QApplication.clipboard()
    #         clipboard.setText(f"hammer5tools:smartprop_editor_var;;{self.name};;{self.var_class};;{self.var_value};;{self.var_visible_in_editor};;{self.var_display_name}")
