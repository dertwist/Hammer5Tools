from smartprop_editor.ui_variable_frame import Ui_Form


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from soudevent_editor.properties.property_actions import PropertyActions
from smartprop_editor.variables.int import Var_class_Int
import ast

class VariableFrame(QWidget):
    def __init__(self, name, var_value, var_class, var_visible_in_editor, widget_list):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.name = name
        self.ui.variable_name.setText(name)
        self.ui.variable_class.setText(var_class)
        self.var_visible_in_editor = var_visible_in_editor
        self.ui.visible_in_editor.setChecked(self.var_visible_in_editor)
        self.ui.visible_in_editor.clicked.connect(self.visible_in_editor)
        self.widget_list = widget_list
        if var_class == 'Float':
            self.ui.layout.insertWidget(0, Var_class_Int(var_value='1', var_class='int'))
        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)

        self.init_ui()

    def show_child(self):
        print(self.ui.show_child.isChecked())
        if not self.ui.show_child.isChecked():
            # self.ui.layout.setEnabled(False)
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
        PropertyActions.show_context_menu(self, event=self.event, property_class=self)
