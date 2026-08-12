from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QLineEdit, QSlider, QHBoxLayout, QCheckBox
from PySide6.QtCore import Qt
from src.editors.smartprop_editor.widgets.main import ComboboxVariablesWidget
from src.widgets import ComboboxTreeChild
from src.settings.main import debug
var_choice_identification_bool = ['boolean', 'bool', 'csmartpropvariable_bool']
var_choice_identification_float = ['float', 'csmartpropvariable_float']
var_choice_identification_int = ['integer', 'int', 'csmartpropvariable_int']
var_choice_identification_string = [
    'string', 'csmartpropvariable_string',
    'model', 'csmartpropvariable_model',
    'material', 'csmartpropvariable_material',
    'materialgroup', 'csmartpropvariable_materialgroup',
    'scalemode', 'pickmode', 'tracenohit', 'applycolormode', 'choiceselectionmode',
    'colorselectionmode', 'orientationmode', 'coordinatespace', 'direction',
    'distributionmode', 'radiusplacementmode', 'gridplacementmode', 'gridoriginmode',
    'pathpositions', 'surfaceproperty'
]
var_choice_identification_vector3d = [
    'vector3d', 'csmartpropvariable_vector3d', 'vector', 'vector3', 'angles',
    'csmartpropvariable_angles', 'color', 'csmartpropvariable_color', 'vector2d', 'vector4d'
]

class AddChoice():
    def __init__(self, tree=QTreeWidget, name=None, default=None, variables_scrollArea=None):
        super().__init__()
        self.tree = tree
        self.variables_scrollArea = variables_scrollArea
        self.name = name if name is not None else 'Choice'
        self.default = default if default is not None else 'default'
        self.item = QTreeWidgetItem()
        self.item.setText(0, self.name)
        self.item.setText(2, 'choice')
        self.item.setFlags(self.item.flags() | Qt.ItemIsEditable)
        root = self.tree.invisibleRootItem()
        root.addChild(self.item)
        combobox = ComboboxTreeChild(layout=root, root=self.item)
        combobox.setCurrentText(self.default)
        combobox.addItem(self.default)
        self.tree.setItemWidget(self.item, 1, combobox)


class AddOption():
    def __init__(self, parent=None, name=None):
        super().__init__()
        self.item = QTreeWidgetItem()
        self.item.setText(0, name if name is not None else 'Option')
        self.item.setText(2, 'option')
        self.item.setFlags(self.item.flags() | Qt.ItemIsEditable)
        if parent and hasattr(parent, 'addChild'):
            parent.addChild(self.item)

class AddVariable():
    def __init__(self, element_id_generator=None, parent=QTreeWidgetItem, name=None, value=None, variables_scrollArea=None, type=None):
        super().__init__()
        """Adding variable tree item"""
        item = QTreeWidgetItem()
        item.setText(0, name or "")
        item.setText(2, 'variable')
        item.setText(1, str(value if value is not None else ""))
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        if parent and hasattr(parent, 'addChild'):
            parent.addChild(item)

        combobox = ComboboxVariablesWidget(
            variables_layout=variables_scrollArea,
            filter_types=['Float', 'MaterialGroup', 'Material', 'Bool', 'Int', 'ScaleMode', 'PickMode', 'Model', 'String', 'Vector3D'],
            element_id_generator=element_id_generator
        )
        combobox.combobox.set_variable(name or "")

        from functools import partial
        combobox._type_change_handler = partial(self.variable_edit_line, parent=item)
        combobox.combobox.changed.connect(combobox._type_change_handler)

        # Auto-infer variable type and value from variables_scrollArea if missing
        if (not type or type == "") and name and variables_scrollArea:
            for i in range(variables_scrollArea.count()):
                w = variables_scrollArea.itemAt(i).widget()
                if w and hasattr(w, 'name') and w.name == name:
                    type = getattr(w, 'var_class', '')
                    if (value is None or value == "") and hasattr(w, 'var_value') and isinstance(w.var_value, dict):
                        value = w.var_value.get('default', value)
                    break

        value_dict = {'name': name, 'class': type or '', 'm_default': value}
        self.variable_edit_line(value_dict, parent=item)
        if parent and hasattr(parent, 'treeWidget') and parent.treeWidget():
            parent.treeWidget().setItemWidget(item, 0, combobox)

    def variable_edit_line(self, value_dict, parent):
        """Select widget based on the variable type"""
        if not parent or not parent.treeWidget():
            return

        old_widget = parent.treeWidget().itemWidget(parent, 1)
        if old_widget:
            old_widget.deleteLater()
            
        var_class = value_dict.get('class') or ''
        var_type = str(var_class).lower().strip()
        val = value_dict.get('m_default')
        
        if var_type in var_choice_identification_bool:
            debug('Var choice type bool')
            widget = VariableBool(value=val, type=var_class or 'Bool')
        elif var_type in var_choice_identification_float or var_type in var_choice_identification_int:
            debug('Var choice type float/int')
            widget = VariableFloat(value=val, type=var_class or 'Float')
        elif var_type in var_choice_identification_string:
            debug('Var choice type string')
            widget = VariableString(value=val, type=var_class or 'String')
        elif var_type in var_choice_identification_vector3d:
            debug('Var choice type vector3d')
            widget = VariableVector3d(value=val, type=var_class or 'Vector3D')
        else:
            debug(f'Var choice type is generic ({var_type})')
            widget = VariableWidget(value=val, type=var_class or 'String')

        parent.treeWidget().setItemWidget(parent, 1, widget)

class VariableWidget(QWidget):
    def __init__(self, value=None, type=None):
        super().__init__()
        self.data = {'m_DataType': type or 'String', 'm_Value': value if value is not None else ""}
        self.setupUI()

    def setupUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.editline = QLineEdit()
        self.editline.setText(str(self.data['m_Value']))
        self.editline.setFocusPolicy(Qt.StrongFocus)
        self.editline.textChanged.connect(self.set_value)
        self.layout.addWidget(self.editline)
        self.setLayout(self.layout)

    def set_value(self):
        self.data.update({'m_Value': self.editline.text()})

class VariableString(QWidget):
    def __init__(self, value=None, type=None):
        super().__init__()
        if value is None:
            value = ""
        self.data = {'m_DataType': type or 'String', 'm_Value': value}
        self.setupUI()

    def setupUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.editline = QLineEdit()
        self.editline.setText(str(self.data['m_Value']))
        self.editline.setFocusPolicy(Qt.StrongFocus)
        self.editline.textChanged.connect(self.set_value)
        self.layout.addWidget(self.editline)
        self.setLayout(self.layout)

    def set_value(self):
        self.data['m_Value'] = self.editline.text()

class VariableVector3d(QWidget):
    def __init__(self, value=None, type=None):
        super().__init__()
        if value is None or not isinstance(value, (list, tuple)) or len(value) < 3:
            if isinstance(value, str):
                try:
                    import ast
                    parsed = ast.literal_eval(value)
                    if isinstance(parsed, (list, tuple)) and len(parsed) >= 3:
                        value = parsed
                    else:
                        value = [1.0, 1.0, 1.0]
                except Exception:
                    value = [1.0, 1.0, 1.0]
            else:
                value = [1.0, 1.0, 1.0]
        self.data = {'m_DataType': type or 'Vector3D', 'm_Value': list(value)}
        self.setupUI()

    def setupUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.x_edit = QLineEdit()
        self.y_edit = QLineEdit()
        self.z_edit = QLineEdit()
        
        for idx, edit in enumerate((self.x_edit, self.y_edit, self.z_edit)):
            try:
                edit.setText(str(self.data['m_Value'][idx]))
            except Exception:
                edit.setText("1.0")
            edit.setFocusPolicy(Qt.StrongFocus)
            edit.textChanged.connect(self.set_value)
            self.layout.addWidget(edit)
            
        self.setLayout(self.layout)

    def set_value(self):
        def _get_val(edit):
            try: return float(edit.text())
            except Exception: return 0.0
        self.data['m_Value'] = [
            _get_val(self.x_edit),
            _get_val(self.y_edit),
            _get_val(self.z_edit)
        ]

class VariableFloat(QWidget):
    def __init__(self, value=None, type=None):
        super().__init__()
        self.data = {'m_DataType': type or 'Float', 'm_Value': value if value is not None else 0.0}
        self.setupUI()

    def setupUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.editline = QLineEdit()
        self.editline.setMaximumWidth(64)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(-1000)
        self.slider.setMaximum(1000)
        self.slider.setFocusPolicy(Qt.StrongFocus)
        self.slider.wheelEvent = lambda event: None  # Disable mouse wheel
        self.editline.setFocusPolicy(Qt.StrongFocus)

        self.layout.addWidget(self.editline)
        self.layout.addWidget(self.slider)

        value = self.data['m_Value']
        self.editline.setText(str(value))
        if value is None:
            self.editline.setText(str(0))
        try:
            self.slider.setValue(int(float(value) * 100))
        except Exception:
            pass

        self.editline.textChanged.connect(self.on_editline_changed)
        self.slider.valueChanged.connect(self.on_slider_changed)

        self.setLayout(self.layout)

    def on_editline_changed(self):
        try:
            value = float(self.editline.text())
        except (ValueError, TypeError):
            value = 0.0
        if value > self.slider.maximum() / 100 or value < self.slider.minimum() / 100:
            self.slider.setMaximum(int(abs(value) * 10 * 100 + 1000))
            self.slider.setMinimum(int(-abs(value) * 10 * 100 - 1000))
        try:
            self.slider.blockSignals(True)
            self.slider.setValue(int(value * 100))
        except (ValueError, TypeError, OverflowError):
            pass
        finally:
            self.slider.blockSignals(False)
        self.data['m_Value'] = value

    def on_slider_changed(self):
        value = self.slider.value() / 100
        self.editline.setText(str(value))
        self.data['m_Value'] = value

    def set_value(self, value):
        self.editline.setText(str(value))
        try:
            self.slider.setValue(int(float(value) * 100))
        except Exception:
            pass
        self.data['m_Value'] = value

class VariableBool(QWidget):
    def __init__(self, value=None, type=None):
        super().__init__()
        self.data = {'m_DataType': type or 'Bool', 'm_Value': value}
        self.setupUI()

    def setupUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.checkbox = QCheckBox()

        self.layout.addWidget(self.checkbox)

        value = self.data['m_Value']
        if isinstance(value, str):
            value = value.lower() in ('true', '1', 'yes')
        self.checkbox.setChecked(bool(value))
        self.checkbox.setText(str(self.checkbox.isChecked()))
        self.checkbox.checkStateChanged.connect(self.on_checkbox_changed)

        self.setLayout(self.layout)
        self.on_checkbox_changed()

    def on_checkbox_changed(self):
        self.checkbox.setText(str(self.checkbox.isChecked()))
        self.set_value()

    def set_value(self):
        self.data.update({'m_Value': self.checkbox.isChecked()})
