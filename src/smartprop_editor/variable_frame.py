from src.smartprop_editor.ui_variable_frame import Ui_Form

from PySide6.QtWidgets import QWidget, QMenu, QApplication
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QCursor, QDrag, QAction
from src.property.methods import PropertyMethods
from src.smartprop_editor.element_id import *
from src.preferences import get_config_bool
from src.popup_menu.popup_menu_main import PopupMenu
from src.smartprop_editor.objects import variables_list
class VariableFrame(QWidget):
    duplicate = Signal(list, int)

    def __init__(self, name, var_class, var_value, var_visible_in_editor, var_display_name, widget_list):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.variable_name.setAcceptDrops(False)
        self.name = name
        self.var_class = var_class
        self.var_default = var_value.get('default')
        self.var_min = var_value.get('min')
        self.var_max = var_value.get('max')
        self.var_model = var_value.get('model')
        self.var_visible_in_editor = var_visible_in_editor
        self.var_display_name = var_display_name

        self.var_value = {
            'default': self.var_default,
            'min': self.var_min,
            'max': self.var_max,
            'model': self.var_model,
            'm_nElementID': get_ElementID(var_value)
        }

        # ID Handling
        update_value_ElementID(self.var_value)
        self.element_id = get_ElementID(self.var_value)
        if get_config_bool('SmartPropEditor', 'display_id_with_variable_class', default=False):
            self.ui.id_display.setText(str(self.element_id))
        else:
            self.ui.id_display.deleteLater()
            self.ui.id_display_label.deleteLater()

        # UI Setup
        self.ui.variable_name.setText(name)
        self.ui.varialbe_display_name.setText(var_display_name)
        self.ui.variable_class.setText(var_class)
        self.ui.visible_in_editor.setChecked(self.var_visible_in_editor)
        self.ui.visible_in_editor.clicked.connect(self.update_self)
        self.ui.varialbe_display_name.textChanged.connect(self.update_self)
        self.ui.variable_name.textChanged.connect(self.update_self)
        self.widget_list = widget_list

        self.ui.change_class.clicked.connect(self.call_class_select_menu)

        # Initialize variable instance based on var_class
        self._initialize_var_instance(var_class)

        # Connect the edited signal directly to on_changed
        self.var_int_instance.edited.connect(self.on_changed)
        self.ui.layout.insertWidget(1, self.var_int_instance)

        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)

        self.init_ui()

    def _initialize_var_instance(self, var_class):
        if var_class == 'Int':
            from src.smartprop_editor.variables.int import Var_class_Int
            self.var_int_instance = Var_class_Int(
                default=self.var_default, min=self.var_min, max=self.var_max, model=None
            )
        elif var_class == 'Float':
            from src.smartprop_editor.variables.float import Var_class_float
            self.var_int_instance = Var_class_float(
                default=self.var_default, min=self.var_min, max=self.var_max, model=None
            )
        elif var_class == 'MaterialGroup':
            from src.smartprop_editor.variables.material_group import Var_class_material_group
            self.var_int_instance = Var_class_material_group(
                default=self.var_default, min=self.var_min, max=self.var_max, model=self.var_model
            )
        elif var_class == 'Bool':
            from src.smartprop_editor.variables.bool import Var_class_bool
            self.var_int_instance = Var_class_bool(
                default=self.var_default, min=self.var_min, max=self.var_max, model=self.var_model
            )
        elif var_class == 'Color':
            from src.smartprop_editor.variables.color import Var_class_color
            self.var_int_instance = Var_class_color(
                default=self.var_default, min=self.var_min, max=self.var_max, model=self.var_model
            )
        elif var_class in ['CoordinateSpace', 'GridPlacementMode', 'GridOriginMode', 'PickMode', 'ScaleMode', 'TraceNoHit', 'ApplyColorMode', 'ChoiceSelectionMode', 'RadiusPlacementMode', 'DistributionMode', 'PathPositions']:
            from src.smartprop_editor.variables.combobox import Var_class_combobox
            elements = self._get_combobox_elements(var_class)
            self.var_int_instance = Var_class_combobox(
                default=self.var_default, elements=elements
            )
        elif var_class == 'Vector2D':
            from src.smartprop_editor.variables.vector2d import Var_class_vector2d
            self.var_int_instance = Var_class_vector2d(default=self.var_default)
        elif var_class == 'Vector3D':
            from src.smartprop_editor.variables.vector3d import Var_class_vector3d
            self.var_int_instance = Var_class_vector3d(default=self.var_default)
        elif var_class == 'Vector4D':
            from src.smartprop_editor.variables.vector4d import Var_class_vector4d
            self.var_int_instance = Var_class_vector4d(default=self.var_default)
        else:
            from src.smartprop_editor.variables.legacy import Var_class_legacy
            self.var_int_instance = Var_class_legacy(
                default=self.var_default, min=self.var_min, max=self.var_max, model=self.var_model
            )

    def _get_combobox_elements(self, var_class):
        elements_dict = {
            'CoordinateSpace': ['ELEMENT', 'OBJECT', 'WORLD'],
            'GridPlacementMode': ['SEGMENT', 'FILL'],
            'GridOriginMode': ['CENTER', 'CORNER'],
            'PickMode': ['LARGEST_FIRST', 'RANDOM', 'ALL_IN_ORDER'],
            'ScaleMode': ['NONE', 'SCALE_END_TO_FIT', 'SCALE_EQUALLY', 'SCALE_MAXIMAIZE'],
            'TraceNoHit': ['NOTHING', 'DISCARD', 'MOVE_TO_START', 'MOVE_TO_END'],
            'ApplyColorMode': ['MULTIPLY_OBJECT', 'MULTIPLY_CURRENT', 'REPLACE'],
            'ChoiceSelectionMode': ['RANDOM', 'FIRST', 'SPECIFIC'],
            'RadiusPlacementMode': ['SPHERE', 'CIRCLE'],
            'DistributionMode': ['RANDOM', 'REGULAR'],
            'PathPositions': ['ALL', 'NTH', 'START_AND_END', 'CONTROL_POINTS'],
        }
        return elements_dict.get(var_class, [])

    def set_class(self, var_class):
        widget = self.ui.layout.itemAt(1).widget()
        widget.deleteLater()
        self.var_class = var_class
        self.var_value = {
            'default': None,
            'min': None,
            'max': None,
            'model': None,
            'm_nElementID': self.var_value['m_nElementID']
        }
        self.var_default = self.var_value['default']
        self.var_min = self.var_value['min']
        self.var_max = self.var_value['max']
        self.var_model = self.var_value['model']
        self.ui.variable_class.setText(var_class)

        self._initialize_var_instance(var_class)

        # Connect the edited signal directly to on_changed
        self.var_int_instance.edited.connect(self.on_changed)
        self.ui.layout.insertWidget(1, self.var_int_instance)
        self.on_changed()

    def get_classes(self):
        return [{item: item} for item in variables_list]

    def call_class_select_menu(self):
        elements = self.get_classes()
        self.popup_menu = PopupMenu(elements, add_once=False)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.set_class(value))
        self.popup_menu.show()

    def show_child(self):
        if not self.ui.show_child.isChecked():
            self.ui.frame_layout.setMaximumSize(16666, 0)
        else:
            self.ui.frame_layout.setMaximumSize(16666, 16666)

    def on_changed(self, var_default=None, var_min=None, var_max=None, var_model=None):
        # Update instance variables with the new values
        self.var_default = var_default
        self.var_min = var_min
        self.var_max = var_max
        self.var_model = var_model

        # Update var_value dictionary
        if self.var_class == 'Bool':
            self.var_value = {
                'default': var_default if var_default is not None else False,
                'min': None,
                'max': None,
                'model': None,
                'm_nElementID': self.element_id
            }
        else:
            self.var_value = {
                'default': var_default if var_default is not None else None,
                'min': var_min if var_min is not None else None,
                'max': var_max if var_max is not None else None,
                'model': var_model if var_model is not None else None,
                'm_nElementID': self.element_id
            }

    def update_self(self):
        self.var_visible_in_editor = self.ui.visible_in_editor.isChecked()
        self.var_display_name = self.ui.varialbe_display_name.text()
        self.name = self.ui.variable_name.text()

    def init_ui(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    mousePressEvent = PropertyMethods.mousePressEvent
    mouseMoveEvent = PropertyMethods.mouseMoveEvent
    dragEnterEvent = PropertyMethods.dragEnterEvent
    dropEvent = PropertyMethods.dropEvent

    def show_context_menu(self):
        context_menu = QMenu()
        delete_action = QAction("Delete", context_menu)
        copy_action = QAction("Copy", context_menu)
        duplicate_action = QAction("Duplicate", context_menu)
        context_menu.addActions([delete_action, copy_action, duplicate_action])

        action = context_menu.exec(QCursor.pos())

        if action == delete_action:
            self.deleteLater()
        elif action == copy_action:
            clipboard = QApplication.clipboard()
            clipboard.setText(f"hammer5tools:smartprop_editor_var;;{self.name};;{self.var_class};;{self.var_value};;{self.var_visible_in_editor};;{self.var_display_name}")
        elif action == duplicate_action:
            __data = [self.name, self.var_class, self.var_value, self.var_visible_in_editor, self.var_display_name]
            __index = self.widget_list.indexOf(self)
            self.duplicate.emit(__data, __index)