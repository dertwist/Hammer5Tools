from time import process_time_ns

from smartprop_editor.ui_property_frame import Ui_Form


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from soudevent_editor.properties.property_actions import PropertyActions

from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QCursor, QDrag,QAction


import ast

class PropertyFrame(QWidget):
    def __init__(self, value=None, widget_list=None, name=None):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.property_class.setAcceptDrops(False)
        self.name = name
        value = ast.literal_eval(value)
        # print(type(value), value)

        self.name = value['_class']
        self.name = self.name.replace('CSmartPropSelectionCriteria_', '')
        self.name = self.name.replace('CSmartPropFilter_', '')
        self.name = self.name.replace('CSmartPropOperation_', '')
        del value['_class']
        self.value = value
        # print(self.value)
        self.layout = self.ui.layout

        self.enable = True
        prop_class = self.name


        self.ui.property_class.setText(self.name)

        self.ui.enable.setChecked(self.enable)
        self.ui.enable.clicked.connect(self.update_self)

        # self.ui.variable_name.textChanged.connect(self.update_self)
        self.widget_list = widget_list




        if prop_class == 'Int':
            # self.ui.property_icon.setIcon('')
            from smartprop_editor.variables.int import Var_class_Int
            self.var_int_instance = Var_class_Int(default=1, min=1, max=1,model=None)
            pass
        elif prop_class == 'Float':
            # from smartprop_editor.variables.float import Var_class_float
            # self.var_int_instance = Var_class_float(default=self.var_default, min=self.var_min, max=self.var_max,model=None)
            pass
        else:
            from smartprop_editor.properties_classes.legacy import PropertyLegacy
            for item, key in self.value.items():
                print(item, key)
            # self.var_int_instance = Var_class_legacy(default=self.var_default, min=self.var_min, max=self.var_max,model=self.var_model)
            pass

        # self.var_int_instance.edited.connect(lambda var_default=self.var_default, var_min=self.var_min, var_max=self.var_max, var_model=self.var_model: self.on_changed(var_default, var_min, var_max, var_model))
        # self.ui.layout.insertWidget(1, self.var_int_instance)

        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)

        self.init_ui()

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
            clipboard.setText(f"hammer5tools:smartprop_editor_var;;{self.name};;{self.value}")
