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
    def __init__(self, name, var_class, var_value, var_visible_in_editor, var_display_name, widget_list):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.variable_name.setAcceptDrops(False)
        self.name = name
        self.var_class = var_class
        self.var_default = (var_value)['default']
        self.var_min = (var_value)['min']
        self.var_max = (var_value)['max']
        self.var_model = (var_value)['model']
        self.var_visible_in_editor = var_visible_in_editor
        self.var_display_name = var_display_name

        self.var_value = {
            'default': {None},
            'min': {None},
            'max': {None},
            'model': {None}
        }

        self.ui.variable_name.setText(name)
        self.ui.varialbe_display_name.setText(var_display_name)
        self.ui.variable_class.setText(var_class)
        self.ui.visible_in_editor.setChecked(self.var_visible_in_editor)
        self.ui.visible_in_editor.clicked.connect(self.visible_in_editor)
        self.widget_list = widget_list
        if var_class == 'Int':
            self.var_int_instance = Var_class_Int(default=self.var_default, min=self.var_min, max=self.var_max,model=None)
            # self.var_int_instance.signal.connect(lambda var_default=self.var_default, var_min=self.var_min, var_max=self.var_max, var_model=self.var_model: self.on_changed(var_default, var_min, var_max, var_model))
            self.var_int_instance.signal.connect(lambda default=1, min_val='f', max_val='f', model='d': self.on_changed(default, min_val, max_val, model))
            self.ui.layout.insertWidget(1, Var_class_Int(default=self.var_default, min=self.var_min, max=self.var_max,model=None))
        elif var_class == 'Float':
            self.var_int_instance = Var_class_Int(default=self.var_default, min=self.var_min, max=self.var_max,model=None)
            self.var_int_instance.signal.connect(lambda var_default=self.var_default, var_min=self.var_min, var_max=self.var_max,var_model=self.var_model: self.on_changed(var_default, var_min, var_max, var_model))
            self.ui.layout.insertWidget(1, Var_class_Int(default=self.var_default, min=self.var_min, max=self.var_max,
                                                         model=None))
        else:
            self.ui.layout.insertWidget(1, Var_class_legacy(var_value=self.var_default))
        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)

        self.init_ui()

    def show_child(self):
        if not self.ui.show_child.isChecked():
            self.ui.frame_layout.setMaximumSize(16666,0)
        else:
            self.ui.frame_layout.setMaximumSize(16666, 16666)

    def on_changed(self, var_default, var_min, var_max, var_model):
        print('1')
        print(self.var_value)
        self.var_value = {
            'default': var_default if var_default else None,
            'min': var_min if var_min else None,
            'max': var_max if var_max else None,
            'model': var_model if var_model else None
        }
        print(self.var_value)

    def visible_in_editor(self):
        self.var_visible_in_editor = self.ui.visible_in_editor.isChecked()
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
            clipboard.setText(f"hammer5tools:smartprop_editor_var;;{self.name};;{self.var_class};;{self.var_value};;{self.var_visible_in_editor};;{self.var_display_name}")
