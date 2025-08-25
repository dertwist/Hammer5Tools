from src.common import JsonToKv3
from src.editors.smartprop_editor.ui_variable_frame import Ui_Form
from PySide6.QtWidgets import QWidget, QMenu, QApplication
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QCursor, QAction
from src.property.methods import PropertyMethods
from src.widgets.element_id import *
from src.settings.main import get_settings_bool
from src.widgets.popup_menu.main import PopupMenu
from src.editors.smartprop_editor.objects import variables_list, expression_completer
from src.widgets.completer.main import CompletingPlainTextEdit

class VariableFrame(QWidget):
    duplicate = Signal(list, int)

    def __init__(self, name, var_class, var_value, var_visible_in_editor, var_display_name, widget_list, element_id_generator):
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
        self.hide_expression = var_value.get('m_HideExpression')
        self.var_visible_in_editor = var_visible_in_editor
        self.var_display_name = var_display_name
        self.element_id_generator = element_id_generator

        # Keep the full hide expression as-is (no extraction needed)
        # m_HideExpression can contain expressions like "new_var_1 == false" or "new_var_1 < 23"
        self.var_value = {
            'default': self.var_default,
            'min': self.var_min,
            'max': self.var_max,
            'model': self.var_model,
            'm_nElementID': get_ElementID(var_value),
            'm_HideExpression': self.hide_expression
        }

        # ID Handling
        self.element_id = get_ElementID(self.var_value)
        if get_settings_bool('SmartPropEditor', 'display_id_with_variable_class', default=False):
            self.ui.id_display.setText(str(self.element_id))
        else:
            self.ui.id_display.deleteLater()
            self.ui.id_display_label.deleteLater()

        # UI Setup
        # Instead of connecting textChanged signal to update_self, we install an event filter
        self.ui.variable_name.setText(name)
        self.ui.varialbe_display_name.setText(var_display_name)
        self.ui.variable_class.setText(var_class)
        self.ui.visible_in_editor.setChecked(self.var_visible_in_editor)
        self.ui.visible_in_editor.clicked.connect(self.update_self)
        self.ui.varialbe_display_name.textChanged.connect(self.update_self)
        # Install event filter on variable_name to enforce uniqueness on focus out
        self.ui.variable_name.installEventFilter(self)

        self.widget_list = widget_list

        self.ui.change_class.clicked.connect(self.call_class_select_menu)

        # Initialize variable instance based on var_class
        self._initialize_var_instance(var_class)

        # Connect the edited signal directly to on_changed
        self.var_int_instance.edited.connect(self.on_changed)
        self.ui.layout.insertWidget(2, self.var_int_instance)

        # Setup the CompletingPlainTextEdit for Hide Expression logic
        self.hide_expression_input = CompletingPlainTextEdit()
        self.hide_expression_input.completion_tail = ''
        self.hide_expression_input.setPlaceholderText("Enter expression (e.g., variable_name == false, variable_name < 23)")
        if self.hide_expression:
            self.hide_expression_input.setPlainText(str(self.hide_expression))
        self.hide_expression_input.textChanged.connect(self.on_hide_expression_changed)
        
        # Setup completer for variable names
        self._setup_hide_expression_completer()
        
        self.ui.hide_expression_frame.layout().addWidget(self.hide_expression_input)

        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)

        self.init_ui()

    def _initialize_var_instance(self, var_class):
        if var_class == 'Int':
            from src.editors.smartprop_editor.variables.int import Var_class_Int
            self.var_int_instance = Var_class_Int(
                default=self.var_default, min=self.var_min, max=self.var_max, model=None
            )
        elif var_class == 'Float':
            from src.editors.smartprop_editor.variables.float import Var_class_float
            self.var_int_instance = Var_class_float(
                default=self.var_default, min=self.var_min, max=self.var_max, model=None
            )
        elif var_class == 'MaterialGroup':
            from src.editors.smartprop_editor.variables.material_group import Var_class_material_group
            self.var_int_instance = Var_class_material_group(
                default=self.var_default, min=self.var_min, max=self.var_max, model=self.var_model
            )
        elif var_class == 'Bool':
            from src.editors.smartprop_editor.variables.bool import Var_class_bool
            self.var_int_instance = Var_class_bool(
                default=self.var_default, min=self.var_min, max=self.var_max, model=self.var_model
            )
        elif var_class == 'Color':
            from src.editors.smartprop_editor.variables.color import Var_class_color
            self.var_int_instance = Var_class_color(
                default=self.var_default, min=self.var_min, max=self.var_max, model=self.var_model
            )
        elif var_class in ['CoordinateSpace', 'GridPlacementMode', 'GridOriginMode', 'PickMode', 'ScaleMode', 'TraceNoHit', 'ApplyColorMode', 'ChoiceSelectionMode', 'RadiusPlacementMode', 'DistributionMode', 'PathPositions']:
            from src.editors.smartprop_editor.variables.combobox import Var_class_combobox
            elements = self._get_combobox_elements(var_class)
            self.var_int_instance = Var_class_combobox(
                default=self.var_default, elements=elements
            )
        elif var_class == 'Vector2D':
            from src.editors.smartprop_editor.variables.vector2d import Var_class_vector2d
            self.var_int_instance = Var_class_vector2d(default=self.var_default)
        elif var_class == 'Vector3D':
            from src.editors.smartprop_editor.variables.vector3d import Var_class_vector3d
            self.var_int_instance = Var_class_vector3d(default=self.var_default)
        elif var_class == 'Vector4D':
            from src.editors.smartprop_editor.variables.vector4d import Var_class_vector4d
            self.var_int_instance = Var_class_vector4d(default=self.var_default)
        else:
            from src.editors.smartprop_editor.variables.legacy import Var_class_legacy
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

    def _get_available_variable_names(self):
        """Get list of available variable names from the widget list for completer."""
        variable_names = []
        count = self.widget_list.count()
        for i in range(count):
            widget = self.widget_list.itemAt(i).widget()
            if hasattr(widget, "name") and widget.name:
                variable_names.append(widget.name)
        return variable_names

    def _setup_hide_expression_completer(self):
        """Setup completer for hide expression input with variable names and common operators."""
        # Get available variable names
        variable_names = self._get_available_variable_names()
        
        # Create completion suggestions including variables and common patterns
        completions = []
        
        # Add variable names
        completions.extend(variable_names)
        
        # Add common expression patterns with variable names
        for var_name in variable_names:
            completions.extend([
                f"{var_name} == false",
                f"{var_name} == true",
                f"{var_name} != false",
                f"{var_name} != true",
                f"{var_name} == 0",
                f"{var_name} != 0",
                f"{var_name} > 0",
                f"{var_name} < 0",
                f"{var_name} >= 0",
                f"{var_name} <= 0",
                f"!{var_name}"
            ])
        
        # Add expression completer items and common boolean values/operators
        completions.extend(expression_completer)
        completions.extend([
            "true", "false", "==", "!=", ">=", "<=", ">", "<", "!"
        ])
        
        # Remove duplicates and sort
        completions = sorted(list(set(completions)))
        
        # Set the completions for the CompletingPlainTextEdit
        self.hide_expression_input.completions.setStringList(completions)

    def update_hide_expression_completer(self):
        """Update the completer when variable names change."""
        self._setup_hide_expression_completer()

    def set_class(self, var_class):
        widget = self.ui.layout.itemAt(1).widget()
        widget.deleteLater()
        self.var_class = var_class
        self.var_value = {
            'default': None,
            'min': None,
            'max': None,
            'model': None,
            'm_nElementID': self.var_value['m_nElementID'],
            'm_HideExpression': None # m_HideExpression = "AdvancedOptions == false"
        }
        self.var_default = self.var_value['default']
        self.var_min = self.var_value['min']
        self.var_max = self.var_value['max']
        self.var_model = self.var_value['model']
        self.hide_expression = self.var_value['m_HideExpression']
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
        
    def on_hide_expression_changed(self):
        """Handle changes to the hide expression input field."""
        self.hide_expression = self.hide_expression_input.toPlainText().strip()
        # Convert empty string to None for consistency
        if not self.hide_expression:
            self.hide_expression = None
        # Update completer with current variable names
        self._setup_hide_expression_completer()
        self.on_changed()
        
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
                'm_nElementID': self.element_id,
                'm_HideExpression':  self.hide_expression if self.hide_expression is not None else None
            }
        else:
            self.var_value = {
                'default': var_default if var_default is not None else None,
                'min': var_min if var_min is not None else None,
                'max': var_max if var_max is not None else None,
                'model': var_model if var_model is not None else None,
                'm_nElementID': self.element_id,
                'm_HideExpression': self.hide_expression if self.hide_expression is not None else None
            }

    def update_self(self):
        self.var_visible_in_editor = self.ui.visible_in_editor.isChecked()
        self.var_display_name = self.ui.varialbe_display_name.text()

    def _make_unique(self, name):
        existing_names = []
        count = self.widget_list.count()
        for i in range(count):
            widget = self.widget_list.itemAt(i).widget()
            if widget is not self and hasattr(widget, "name"):
                existing_names.append(widget.name)

        if name not in existing_names:
            return name
        else:
            suffix = 1
            unique_name = f"{name}_{suffix}"
            while unique_name in existing_names:
                suffix += 1
                unique_name = f"{name}_{suffix}"
            return unique_name

    def init_ui(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def eventFilter(self, obj, event):
        """Enforce unique name when the variable name editing line loses focus.
        Also warns if variable name starts with a number or special symbol.
        """
        if obj == self.ui.variable_name and event.type() == QEvent.FocusOut:
            new_name = self.ui.variable_name.text()
            if new_name and (new_name[0].isdigit() or (not new_name[0].isalpha() and new_name[0] != '_')):
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Invalid Variable Name",
                    "It is not recommended to use numbers or special symbols at the start of variable name"
                )

            # Continue with existing unique name logic
            unique_name = self._make_unique(new_name)
            if unique_name != new_name:
                self.ui.variable_name.setText(unique_name)
            self.name = unique_name

        return super().eventFilter(obj, event)

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
            m_variable = {'_class': f'CSmartPropVariable_{self.var_class}', 'm_VariableName':self.name, 'm_bExposeAsParameter': self.var_visible_in_editor}
            if self.var_display_name is not None:
                m_variable.update({'m_ParameterName': self.var_display_name})
            if self.var_default is not None:
                m_variable.update({'m_DefaultValue': self.var_default})
            if self.var_min is not None:
                m_variable.update({'m_flParamaterMinValue': self.var_min})
            if self.var_max is not None:
                m_variable.update({'m_flParamaterMaxValue': self.var_max})
            if self.var_model is not None:
                m_variable.update({'m_sModelName': self.var_model})
            if self.hide_expression is not None:
                m_variable.update({'m_HideExpression': self.hide_expression})
            m_data = {'m_Variables': []}
            m_data['m_Variables'].append(m_variable)
            clipboard.setText(JsonToKv3(m_data))
        elif action == duplicate_action:
            __data = [self.name, self.var_class, self.var_value, self.var_visible_in_editor, self.var_display_name]
            __index = self.widget_list.indexOf(self)
            self.duplicate.emit(__data, __index)