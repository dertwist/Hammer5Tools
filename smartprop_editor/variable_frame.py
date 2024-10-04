from smartprop_editor.ui_variable_frame import Ui_Form


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from soudevent_editor.properties.property_actions import PropertyActions

from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QCursor, QDrag,QAction


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
            'default': self.var_default,
            'min':  self.var_min,
            'max':  self.var_max,
            'model':  self.var_model
        }

        self.ui.variable_name.setText(name)
        self.ui.varialbe_display_name.setText(var_display_name)
        self.ui.variable_class.setText(var_class)
        self.ui.visible_in_editor.setChecked(self.var_visible_in_editor)
        self.ui.visible_in_editor.clicked.connect(self.update_self)
        self.ui.varialbe_display_name.textChanged.connect(self.update_self)
        self.ui.variable_name.textChanged.connect(self.update_self)
        self.widget_list = widget_list




        if var_class == 'Int':
            from smartprop_editor.variables.int import Var_class_Int
            self.var_int_instance = Var_class_Int(default=self.var_default, min=self.var_min, max=self.var_max,model=None)
        elif var_class == 'Float':
            from smartprop_editor.variables.float import Var_class_float
            self.var_int_instance = Var_class_float(default=self.var_default, min=self.var_min, max=self.var_max,model=None)
        elif var_class == 'MaterialGroup':
            from smartprop_editor.variables.material_group import Var_class_material_group
            self.var_int_instance = Var_class_material_group(default=self.var_default, min=self.var_min, max=self.var_max,model=self.var_model)
        elif var_class == 'Bool':
            from smartprop_editor.variables.bool import Var_class_bool
            self.var_int_instance = Var_class_bool(default=self.var_default, min=self.var_min, max=self.var_max,model=self.var_model)
        elif var_class == 'Color':
            from smartprop_editor.variables.color import Var_class_color
            self.var_int_instance = Var_class_color(default=self.var_default, min=self.var_min, max=self.var_max,model=self.var_model)
        elif var_class == 'CoordinateSpace':
            from smartprop_editor.variables.combobox import Var_class_combobox
            self.var_int_instance = Var_class_combobox(default=self.var_default, elements=['ELEMENT', 'OBJECT', 'WORLD'])
        elif var_class == 'GridPlacementMode':
            from smartprop_editor.variables.combobox import Var_class_combobox
            self.var_int_instance = Var_class_combobox(default=self.var_default, elements=['SEGMENT', 'FILL'])
        elif var_class == 'GridOriginMode':
            from smartprop_editor.variables.combobox import Var_class_combobox
            self.var_int_instance = Var_class_combobox(default=self.var_default, elements=['CENTER', 'CORNER'])
        elif var_class == 'PickMode':
            from smartprop_editor.variables.combobox import Var_class_combobox
            self.var_int_instance = Var_class_combobox(default=self.var_default, elements=['LARGEST_FIRST', 'RANDOM', 'ALL_IN_ORDER'])
        elif var_class == 'ScaleMode':
            from smartprop_editor.variables.combobox import Var_class_combobox
            self.var_int_instance = Var_class_combobox(default=self.var_default, elements=['NONE', 'SCALE_END_TO_FIT', 'SCALE_EQUALLY', 'SCALE_MAXIMAIZE'])
        elif var_class == 'TraceNoHit':
            from smartprop_editor.variables.combobox import Var_class_combobox
            self.var_int_instance = Var_class_combobox(default=self.var_default, elements=['NOTHING', 'DISCARD', 'MOVE_TO_START', 'MOVE_TO_END'])
        elif var_class == 'ApplyColorMode':
            from smartprop_editor.variables.combobox import Var_class_combobox
            self.var_int_instance = Var_class_combobox(default=self.var_default, elements=['MULTIPLY_OBJECT', 'MULTIPLY_CURRENT', 'REPLACE'])
        elif var_class == 'ChoiceSelectionMode':
            from smartprop_editor.variables.combobox import Var_class_combobox
            self.var_int_instance = Var_class_combobox(default=self.var_default, elements=['RANDOM', 'FIRST'])
        elif var_class == 'RadiusPlacementMode':
            from smartprop_editor.variables.combobox import Var_class_combobox
            self.var_int_instance = Var_class_combobox(default=self.var_default, elements=['SPHERE', 'CIRCLE'])
        elif var_class == 'DistributionMode':
            from smartprop_editor.variables.combobox import Var_class_combobox
            self.var_int_instance = Var_class_combobox(default=self.var_default, elements=['RANDOM', 'REGULAR'])
        elif var_class == 'PathPositions':
            from smartprop_editor.variables.combobox import Var_class_combobox
            self.var_int_instance = Var_class_combobox(default=self.var_default, elements=['ALL', 'NTH', 'START_AND_END', 'CONTROL_POINTS'])
        elif var_class == 'Vector2D':
            from smartprop_editor.variables.vector2d import Var_class_vector2d
            self.var_int_instance = Var_class_vector2d(default=self.var_default)
        elif var_class == 'Vector3D':
            from smartprop_editor.variables.vector3d import Var_class_vector3d
            self.var_int_instance = Var_class_vector3d(default=self.var_default)
        elif var_class == 'Vector4D':
            from smartprop_editor.variables.vector4d import Var_class_vector4d
            self.var_int_instance = Var_class_vector4d(default=self.var_default)
        else:
            from smartprop_editor.variables.legacy import Var_class_legacy
            self.var_int_instance = Var_class_legacy(default=self.var_default, min=self.var_min, max=self.var_max,model=self.var_model)

        self.var_int_instance.edited.connect(lambda var_default=self.var_default, var_min=self.var_min, var_max=self.var_max, var_model=self.var_model: self.on_changed(var_default, var_min, var_max, var_model))
        self.ui.layout.insertWidget(1, self.var_int_instance)

        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)

        self.init_ui()

    def show_child(self):
        if not self.ui.show_child.isChecked():
            self.ui.frame_layout.setMaximumSize(16666,0)
        else:
            self.ui.frame_layout.setMaximumSize(16666, 16666)

    def on_changed(self, var_default=None, var_min=None, var_max=None, var_model=None):
        if self.var_class == 'Bool':
            self.var_value = {
                'default': var_default if var_default is not None else False,
                'min': None,
                'max': None,
                'model': None
            }
        else:
            self.var_value = {
                'default': var_default if var_default else None,
                'min': var_min if var_min else None,
                'max': var_max if var_max else None,
                'model': var_model if var_model else None
            }

    def update_self(self):
        self.var_visible_in_editor = self.ui.visible_in_editor.isChecked()
        self.var_display_name = self.ui.varialbe_display_name.text()
        self.name = self.ui.variable_name.text()
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
