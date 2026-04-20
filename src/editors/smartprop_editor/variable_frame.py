from src.common import JsonToKv3
from src.editors.smartprop_editor.ui_variable_frame import Ui_Form
from PySide6.QtWidgets import QWidget, QMenu, QApplication
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QCursor, QAction
from src.property.methods import PropertyMethods
from src.widgets.element_id import *
from src.settings.main import get_settings_bool
from src.widgets.popup_menu.main import PopupMenu
from src.editors.smartprop_editor.objects import variables_list
from src.widgets.completer.main import CompletingPlainTextEdit
from src.editors.smartprop_editor.completion_utils import CompletionUtils
from src.editors.smartprop_editor.widgets.expression_editor.main import ExpressionEditor


class VariableFrame(PropertyMethods, QWidget):
    duplicate = Signal(list, int)
    delete_requested = Signal()
    pre_change = Signal()    # fires BEFORE var_value/name/etc. are updated
    content_changed = Signal()
    edited = Signal()

    def __init__(self, name, var_class, var_value, var_visible_in_editor, var_display_name, widget_list,
                 element_id_generator):
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
        self.ui.variable_name.setText(name if name is not None else "")
        self.ui.varialbe_display_name.setText(var_display_name if var_display_name is not None else "")
        self.ui.variable_class.setText(var_class if var_class is not None else "")
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
        self.hide_expression_input.setPlaceholderText(
            "Enter expression (e.g., variable_name == false)")
        if self.hide_expression:
            self.hide_expression_input.setPlainText(str(self.hide_expression))
        self.hide_expression_input.textChanged.connect(self.on_hide_expression_changed)

        # Setup completer for variable names with filtering for hide expressions
        self._setup_hide_expression_completer()



        #Setup Expression editor
        self.expression_editor = ExpressionEditor(self.hide_expression_input, self.widget_list)
        self.ui.hide_expression_frame.layout().addWidget(self.expression_editor)

        #Expression text field
        self.ui.hide_expression_frame.layout().addWidget(self.hide_expression_input)

        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)

        self.init_ui()
        self.update_colors()

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
        elif var_class == 'Material':
            from src.editors.smartprop_editor.variables.material import Var_class_material
            self.var_int_instance = Var_class_material(
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
        elif var_class in ['CoordinateSpace', 'GridPlacementMode', 'GridOriginMode', 'PickMode', 'ScaleMode',
                           'TraceNoHit', 'ApplyColorMode', 'ChoiceSelectionMode', 'RadiusPlacementMode',
                           'DistributionMode', 'PathPositions', 'Direction']:
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
        return CompletionUtils.get_combobox_elements(var_class)

    def update_colors(self):
        color_map = {
            'String': '#E67E22',
            'Model': '#E67E22',
            'Material': '#E67E22',
            'MaterialGroup': '#E67E22',
            'Bool': '#C0392B',
            'Float': '#2980B9',
            'Int': '#2471A3',
            'Vector2D': '#8E44AD',
            'Vector3D': '#8E44AD',
            'Vector4D': '#8E44AD',
            'Angles': '#8E44AD',
            'Color': '#1B5E20',
        }

        enum_types = [
            'Direction', 'CoordinateSpace', 'GridPlacementMode', 'GridOriginMode',
            'PickMode', 'ScaleMode', 'TraceNoHit', 'ApplyColorMode',
            'ChoiceSelectionMode', 'RadiusPlacementMode', 'DistributionMode', 'PathPositions'
        ]

        target_color = color_map.get(self.var_class, '#242424')
        if self.var_class in enum_types:
            target_color = '#1D8348'

        style = self.ui.label.styleSheet()
        import re
        if 'background-color:' in style:
            style = re.sub(r'background-color:\s*[^;]+;', f'background-color: {target_color};', style)
        else:
            style += f'\nbackground-color: {target_color};'
        self.ui.label.setStyleSheet(style)

    def _setup_hide_expression_completer(self):
        """Setup completer for hide expression input with filtered type-aware completions."""
        # For hide expressions, only show Bool, Int, and Float variables
        filter_types = ['Bool', 'Int', 'Float']

        # Use the utility to setup the completer with filtering
        CompletionUtils.setup_completer_for_widget(
            self.hide_expression_input,
            self.widget_list,
            filter_types=filter_types,
            context='hide_expression'
        )

    def update_hide_expression_completer(self):
        """Update the completer when variable names change."""
        self._setup_hide_expression_completer()

    def set_class(self, var_class):
        # Emit pre_change BEFORE modifying any state so the undo snapshot
        # captures the correct "before" values.
        self.pre_change.emit()

        # Remove the old var_int_instance widget from the layout.
        # It lives at index 2 in self.ui.layout (after frame_3 and
        # hide_expression_frame), so we locate it by reference instead of
        # hard-coding an index to be robust.
        old_widget = self.var_int_instance
        for i in range(self.ui.layout.count()):
            if self.ui.layout.itemAt(i).widget() is old_widget:
                self.ui.layout.takeAt(i)
                break
        old_widget.deleteLater()

        self.var_class = var_class
        self.var_value = {
            'default': None,
            'min': None,
            'max': None,
            'model': None,
            'm_nElementID': self.var_value['m_nElementID'],
            'm_HideExpression': None
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
        self.ui.layout.insertWidget(2, self.var_int_instance)
        # Emit content_changed directly (pre_change was already emitted above)
        self.update_colors()
        self.content_changed.emit()

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
        # Update completer with current variable names and types
        self._setup_hide_expression_completer()
        # on_changed emits content_changed, so no extra emit needed here
        self.on_changed()

    def show_child(self):
        if not self.ui.show_child.isChecked():
            self.ui.frame_layout.setMaximumSize(16666, 0)
        else:
            self.ui.frame_layout.setMaximumSize(16666, 16666)

    def set_indent(self, level):
        """Set left margin based on indentation level (5px per level)."""
        if hasattr(self, 'ui') and hasattr(self.ui, 'verticalLayout'):
            self.ui.verticalLayout.setContentsMargins(level * 5, 0, 0, 0)

    def on_changed(self, var_default=None, var_min=None, var_max=None, var_model=None):
        # Signal listeners (variables_viewport) to snapshot state BEFORE we modify it.
        self.pre_change.emit()
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
                'm_HideExpression': self.hide_expression if self.hide_expression is not None else None
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
        self.content_changed.emit()

    def update_self(self):
        self.pre_change.emit()
        self.var_visible_in_editor = self.ui.visible_in_editor.isChecked()
        self.var_display_name = self.ui.varialbe_display_name.text()
        self.content_changed.emit()

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
            # Capture snapshot before self.name is updated.
            self.pre_change.emit()
            self.name = unique_name
            self.content_changed.emit()

        return super().eventFilter(obj, event)

    mousePressEvent = PropertyMethods.mousePressEvent
    mouseMoveEvent = PropertyMethods.mouseMoveEvent
    dragEnterEvent = PropertyMethods.dragEnterEvent
    dragMoveEvent = PropertyMethods.dragMoveEvent
    dragLeaveEvent = PropertyMethods.dragLeaveEvent

    def dropEvent(self, event):
        self.pre_change.emit()
        PropertyMethods.dropEvent(self, event)
        self.content_changed.emit()

    def show_context_menu(self):
        context_menu = QMenu()
        delete_action = QAction("Delete", context_menu)
        copy_action = QAction("Copy", context_menu)
        duplicate_action = QAction("Duplicate", context_menu)
        context_menu.addActions([delete_action, copy_action, duplicate_action])

        action = context_menu.exec(QCursor.pos())

        if action == delete_action:
            self.delete_requested.emit()
        elif action == copy_action:
            clipboard = QApplication.clipboard()
            m_variable = {'_class': f'CSmartPropVariable_{self.var_class}', 'm_VariableName': self.name,
                          'm_bExposeAsParameter': self.var_visible_in_editor}
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
                
            import re
            is_category = False
            is_start = False
            if self.name:
                if re.match(r"hammer5tools_category_([a-z0-9]+)_(start|end)", self.name) or re.match(r"hammer5tools_category_(.*)_category_(.*)_(start|end)", self.name):
                    is_category = True
                    is_start = self.name.endswith('_start')
                    
            if is_category:
                if is_start:
                    m_variable.update({'m_Hammer5ToolsCategoryName': getattr(self, 'category_name', 'Category name')})
                else:
                    m_variable.update({'m_Hammer5ToolsCategoryName': 'New category'})
                    
            m_data = {'m_Variables': []}
            m_data['m_Variables'].append(m_variable)
            clipboard.setText(JsonToKv3(m_data))
        elif action == duplicate_action:
            __data = [self.name, self.var_class, self.var_value, self.var_visible_in_editor, self.var_display_name]
            __index = self.widget_list.indexOf(self)
            self.duplicate.emit(__data, __index)

    def set_indent(self, level):
        self.ui.verticalLayout.setContentsMargins(level * 5, 0, 0, 0)


class CategoryFrame(VariableFrame):
    visibility_toggled = Signal()
    def __init__(self, name, var_visible_in_editor, var_display_name, widget_list, element_id_generator):
        # Detect if it's start or end before super().__init__ because it calls update_colors
        self.is_start = name.endswith('_start')
        self.is_end = name.endswith('_end')

        # Category is always a Bool class internally for Valve to be happy, but we treat it specially
        super().__init__(name=name, var_class='Bool', var_value={'default': None},
                         var_visible_in_editor=var_visible_in_editor,
                         var_display_name=var_display_name, widget_list=widget_list,
                         element_id_generator=element_id_generator)

        # Base name and hash extraction
        import re
        # Try new format first: hammer5tools_category_{hash}_{start/end}
        match = re.match(r"hammer5tools_category_([a-z0-9]+)_(start|end)", name)
        if match:
            self.category_hash = match.group(1)
        else:
            # Fallback to old format just in case
            match_old = re.match(r"hammer5tools_category_(.*)_category_(.*)_(start|end)", name)
            if match_old:
                self.category_hash = match_old.group(2)
            else:
                self.category_hash = name

        self._setup_category_ui()

    def _setup_category_ui(self):
        # Hide irrelevant widgets
        self.ui.variable_class.hide()
        self.ui.change_class.hide()
        if hasattr(self.ui, 'id_display'): self.ui.id_display.hide()
        if hasattr(self.ui, 'id_display_label'): self.ui.id_display_label.hide()

        # Categories don't have frame_layout values
        self.ui.frame_layout.hide()
        if hasattr(self, 'var_int_instance'):
            self.var_int_instance.hide()

        # Update labels/placeholders
        if self.is_start:
            self.category_name = self._extract_display_name(self.var_display_name)
            self.ui.variable_name.setPlaceholderText("Category Name")
            self.ui.variable_name.setText(self.category_name)
            self.ui.frame_3.hide()
            
            # Start categories can expand/collapse children
            self.ui.show_child.show()
            self.ui.show_child.setChecked(True)
        else:
            # End widget is very minimal
            self.ui.variable_name.hide()
            self.ui.visible_in_editor.hide()
            self.ui.frame_3.hide()
            self.ui.show_child.hide()
            self.ui.hide_expression_frame.hide()
            self.ui.label.setStyleSheet(self.ui.label.styleSheet() + "image: none;")
            self.setFixedHeight(12) # Small line for end
            self.ui.label.setText("      ") # Just some space

        self.update_colors()

    def show_child(self):
        # Override show_child to trigger visibility updates instead of expanding self.ui.frame_layout
        if self.is_start:
            self.visibility_toggled.emit()

    def _extract_display_name(self, full_display_name):
        # Extract "Name" from " ----====Name====----"
        if full_display_name:
            import re
            match = re.search(r"----====(.*)===----", full_display_name)
            if match:
                return match.group(1).strip()
            return full_display_name
        return "Category Name"

    def _format_display_name(self, base_display_name):
        if self.is_start:
            return f" ----===={base_display_name}===------"
        else:
            return "                                             "

    def update_self(self):
        self.pre_change.emit()
        self.var_visible_in_editor = self.ui.visible_in_editor.isChecked()

        if self.is_start:
            self.category_name = self.ui.variable_name.text()
            self.var_display_name = self._format_display_name(self.category_name)
            # DO NOT change self.name (m_VariableName)

            # Sync with end widget if found
            self._sync_with_end_widget()

        self.content_changed.emit()

    def _sync_with_end_widget(self):
        """Find the corresponding end widget and update its name/visibility."""
        layout = self.widget_list
        if not layout: return

        found_start = False
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if w == self:
                found_start = True
                continue
            if found_start and isinstance(w, CategoryFrame) and w.is_end and w.category_hash == self.category_hash:
                w.pre_change.emit()
                w.name = f"hammer5tools_category_{self.category_hash}_end"
                w.var_visible_in_editor = self.var_visible_in_editor
                w.content_changed.emit()
                break

    def update_colors(self):
        # Categories have a distinct color
        target_color = '#2C3E50' if self.is_start else '#1C1C1C'
        style = self.ui.label.styleSheet()
        import re
        if 'background-color:' in style:
            style = re.sub(r'background-color:\s*[^;]+;', f'background-color: {target_color};', style)
        else:
            style += f'\nbackground-color: {target_color};'
        self.ui.label.setStyleSheet(style)

    def eventFilter(self, obj, event):
        if obj == self.ui.variable_name and event.type() == QEvent.FocusOut:
            if self.is_start:
                new_cat_name = self.ui.variable_name.text()
                self.category_name = new_cat_name
                self.update_self()
            return True
        return super(CategoryFrame, self).eventFilter(obj, event)