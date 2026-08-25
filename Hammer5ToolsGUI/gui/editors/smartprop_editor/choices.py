import ast
from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QWidget, QLineEdit, QSlider,
    QHBoxLayout, QCheckBox
)
from PySide6.QtCore import Qt
from gui.editors.smartprop_editor.widgets.main import ComboboxVariablesWidget
from gui.editors.smartprop_editor._common import is_category_widget
from gui.widgets import ComboboxTreeChild
from gui.settings.main import debug

var_choice_identification_bool = ['boolean', 'bool', 'csmartpropvariable_bool']
var_choice_identification_int = ['integer', 'int', 'csmartpropvariable_int']
var_choice_identification_float = ['float', 'csmartpropvariable_float']
var_choice_identification_color = ['color', 'csmartpropvariable_color']
var_choice_identification_vector2d = ['vector2d', 'csmartpropvariable_vector2d']
var_choice_identification_vector3d = [
    'vector3d', 'csmartpropvariable_vector3d', 'vector', 'vector3', 'angles',
    'csmartpropvariable_angles'
]
var_choice_identification_vector4d = ['vector4d', 'csmartpropvariable_vector4d']
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


class AddChoice:
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
        if self.default:
            combobox.addItem(self.default)
            combobox.setCurrentText(self.default)
        self.tree.setItemWidget(self.item, 1, combobox)


class AddOption:
    def __init__(self, parent=None, name=None):
        super().__init__()
        self.item = QTreeWidgetItem()
        self.item.setText(0, name if name is not None else 'Option')
        self.item.setText(2, 'option')
        self.item.setFlags(self.item.flags() | Qt.ItemIsEditable)
        if parent and hasattr(parent, 'addChild'):
            parent.addChild(self.item)


class AddVariable:
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

        # Allow all SmartProp variable types in the choice dropdown (filter_types=None)
        combobox = ComboboxVariablesWidget(
            variables_layout=variables_scrollArea,
            filter_types=None,
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
                    if is_category_widget(w):
                        continue
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

        var_name = value_dict.get('name')
        if var_name:
            parent.setText(0, var_name)

        old_widget = parent.treeWidget().itemWidget(parent, 1)
        if old_widget:
            old_widget.deleteLater()

        var_class = value_dict.get('class') or ''
        var_type = str(var_class).lower().strip()
        val = value_dict.get('m_default')

        if var_type in var_choice_identification_bool:
            debug('Var choice type bool')
            widget = VariableBool(value=val, type=var_class or 'Bool', parent_item=parent)
        elif var_type in var_choice_identification_int:
            debug('Var choice type int')
            widget = VariableInt(value=val, type=var_class or 'Int', parent_item=parent)
        elif var_type in var_choice_identification_float:
            debug('Var choice type float')
            widget = VariableFloat(value=val, type=var_class or 'Float', parent_item=parent)
        elif var_type in var_choice_identification_color:
            debug('Var choice type color')
            widget = VariableColor(value=val, type=var_class or 'Color', parent_item=parent)
        elif var_type in var_choice_identification_vector2d:
            debug('Var choice type vector2d')
            widget = VariableVector2d(value=val, type=var_class or 'Vector2D', parent_item=parent)
        elif var_type in var_choice_identification_vector4d:
            debug('Var choice type vector4d')
            widget = VariableVector4d(value=val, type=var_class or 'Vector4D', parent_item=parent)
        elif var_type in var_choice_identification_vector3d:
            debug('Var choice type vector3d')
            widget = VariableVector3d(value=val, type=var_class or 'Vector3D', parent_item=parent)
        elif var_type in var_choice_identification_string:
            debug('Var choice type string')
            widget = VariableString(value=val, type=var_class or 'String', parent_item=parent)
        else:
            debug(f'Var choice type is generic ({var_type})')
            widget = VariableWidget(value=val, type=var_class or 'String', parent_item=parent)

        parent.treeWidget().setItemWidget(parent, 1, widget)


def _sync_item_text(parent_item, value):
    if parent_item:
        parent_item.setText(1, str(value if value is not None else ""))


def _parse_seq(val, default, count):
    if val is None:
        return default
    if isinstance(val, (list, tuple)):
        lst = list(val)
        while len(lst) < count:
            lst.append(default[len(lst)] if len(lst) < len(default) else 0)
        return lst[:count]
    if isinstance(val, str):
        try:
            parsed = ast.literal_eval(val)
            if isinstance(parsed, (list, tuple)):
                lst = list(parsed)
                while len(lst) < count:
                    lst.append(default[len(lst)] if len(lst) < len(default) else 0)
                return lst[:count]
        except Exception:
            pass
    return default


class VariableWidget(QWidget):
    def __init__(self, value=None, type=None, parent_item=None):
        super().__init__()
        self.parent_item = parent_item
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
        val = self.editline.text()
        self.data.update({'m_Value': val})
        _sync_item_text(self.parent_item, val)


class VariableString(QWidget):
    def __init__(self, value=None, type=None, parent_item=None):
        super().__init__()
        self.parent_item = parent_item
        if value is None:
            value = ""
        self.data = {'m_DataType': type or 'String', 'm_Value': str(value)}
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
        val = self.editline.text()
        self.data['m_Value'] = val
        _sync_item_text(self.parent_item, val)


class VariableInt(QWidget):
    def __init__(self, value=None, type=None, parent_item=None):
        super().__init__()
        self.parent_item = parent_item
        int_val = 0
        if value is not None:
            try:
                int_val = int(float(value))
            except (ValueError, TypeError):
                int_val = 0
        self.data = {'m_DataType': type or 'Int', 'm_Value': int_val}
        self.setupUI()

    def setupUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.editline = QLineEdit()
        self.editline.setMaximumWidth(64)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(-100)
        self.slider.setMaximum(100)
        self.slider.setFocusPolicy(Qt.StrongFocus)
        self.slider.wheelEvent = lambda event: None
        self.editline.setFocusPolicy(Qt.StrongFocus)

        self.layout.addWidget(self.editline)
        self.layout.addWidget(self.slider)

        value = self.data['m_Value']
        self.editline.setText(str(value))
        try:
            self.slider.setValue(int(value))
        except Exception:
            pass

        self.editline.textChanged.connect(self.on_editline_changed)
        self.slider.valueChanged.connect(self.on_slider_changed)

        self.setLayout(self.layout)

    def on_editline_changed(self):
        text = self.editline.text()
        try:
            value = int(float(text))
        except (ValueError, TypeError):
            value = 0
        if value > self.slider.maximum() or value < self.slider.minimum():
            self.slider.setMaximum(int(abs(value) * 2 + 100))
            self.slider.setMinimum(int(-abs(value) * 2 - 100))
        try:
            self.slider.blockSignals(True)
            self.slider.setValue(value)
        except (ValueError, TypeError, OverflowError):
            pass
        finally:
            self.slider.blockSignals(False)
        self.data['m_Value'] = value
        _sync_item_text(self.parent_item, value)

    def on_slider_changed(self):
        value = self.slider.value()
        self.editline.setText(str(value))
        self.data['m_Value'] = value
        _sync_item_text(self.parent_item, value)

    def set_value(self, value):
        try:
            int_val = int(float(value))
        except (ValueError, TypeError):
            int_val = 0
        self.editline.setText(str(int_val))
        try:
            self.slider.setValue(int_val)
        except Exception:
            pass
        self.data['m_Value'] = int_val
        _sync_item_text(self.parent_item, int_val)


class VariableFloat(QWidget):
    def __init__(self, value=None, type=None, parent_item=None):
        super().__init__()
        self.parent_item = parent_item
        flt_val = 0.0
        if value is not None:
            try:
                flt_val = float(value)
            except (ValueError, TypeError):
                flt_val = 0.0
        self.data = {'m_DataType': type or 'Float', 'm_Value': flt_val}
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
        self.slider.wheelEvent = lambda event: None
        self.editline.setFocusPolicy(Qt.StrongFocus)

        self.layout.addWidget(self.editline)
        self.layout.addWidget(self.slider)

        value = self.data['m_Value']
        self.editline.setText(str(value))
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
        _sync_item_text(self.parent_item, value)

    def on_slider_changed(self):
        value = self.slider.value() / 100
        self.editline.setText(str(value))
        self.data['m_Value'] = value
        _sync_item_text(self.parent_item, value)

    def set_value(self, value):
        self.editline.setText(str(value))
        try:
            self.slider.setValue(int(float(value) * 100))
        except Exception:
            pass
        try:
            self.data['m_Value'] = float(value)
        except (ValueError, TypeError):
            self.data['m_Value'] = 0.0
        _sync_item_text(self.parent_item, self.data['m_Value'])


class VariableBool(QWidget):
    def __init__(self, value=None, type=None, parent_item=None):
        super().__init__()
        self.parent_item = parent_item
        if isinstance(value, str):
            value = value.lower() in ('true', '1', 'yes')
        self.data = {'m_DataType': type or 'Bool', 'm_Value': bool(value) if value is not None else False}
        self.setupUI()

    def setupUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.checkbox = QCheckBox()
        self.layout.addWidget(self.checkbox)

        self.checkbox.setChecked(self.data['m_Value'])
        self.checkbox.setText(str(self.checkbox.isChecked()))
        self.checkbox.checkStateChanged.connect(self.on_checkbox_changed)

        self.setLayout(self.layout)

    def on_checkbox_changed(self):
        self.checkbox.setText(str(self.checkbox.isChecked()))
        self.set_value()

    def set_value(self):
        val = self.checkbox.isChecked()
        self.data.update({'m_Value': val})
        _sync_item_text(self.parent_item, val)


class VariableVector2d(QWidget):
    def __init__(self, value=None, type=None, parent_item=None):
        super().__init__()
        self.parent_item = parent_item
        parsed = _parse_seq(value, [0.0, 0.0], 2)
        self.data = {'m_DataType': type or 'Vector2D', 'm_Value': [float(x) for x in parsed]}
        self.setupUI()

    def setupUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.x_edit = QLineEdit()
        self.y_edit = QLineEdit()

        for idx, edit in enumerate((self.x_edit, self.y_edit)):
            try:
                edit.setText(str(self.data['m_Value'][idx]))
            except Exception:
                edit.setText("0.0")
            edit.setFocusPolicy(Qt.StrongFocus)
            edit.textChanged.connect(self.set_value)
            self.layout.addWidget(edit)

        self.setLayout(self.layout)

    def set_value(self):
        def _get_val(edit):
            try:
                return float(edit.text())
            except Exception:
                return 0.0
        val = [_get_val(self.x_edit), _get_val(self.y_edit)]
        self.data['m_Value'] = val
        _sync_item_text(self.parent_item, val)


class VariableVector3d(QWidget):
    def __init__(self, value=None, type=None, parent_item=None):
        super().__init__()
        self.parent_item = parent_item
        parsed = _parse_seq(value, [1.0, 1.0, 1.0], 3)
        self.data = {'m_DataType': type or 'Vector3D', 'm_Value': [float(x) for x in parsed]}
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
            try:
                return float(edit.text())
            except Exception:
                return 0.0
        val = [
            _get_val(self.x_edit),
            _get_val(self.y_edit),
            _get_val(self.z_edit)
        ]
        self.data['m_Value'] = val
        _sync_item_text(self.parent_item, val)


class VariableVector4d(QWidget):
    def __init__(self, value=None, type=None, parent_item=None):
        super().__init__()
        self.parent_item = parent_item
        parsed = _parse_seq(value, [0.0, 0.0, 0.0, 0.0], 4)
        self.data = {'m_DataType': type or 'Vector4D', 'm_Value': [float(x) for x in parsed]}
        self.setupUI()

    def setupUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.x_edit = QLineEdit()
        self.y_edit = QLineEdit()
        self.z_edit = QLineEdit()
        self.w_edit = QLineEdit()

        for idx, edit in enumerate((self.x_edit, self.y_edit, self.z_edit, self.w_edit)):
            try:
                edit.setText(str(self.data['m_Value'][idx]))
            except Exception:
                edit.setText("0.0")
            edit.setFocusPolicy(Qt.StrongFocus)
            edit.textChanged.connect(self.set_value)
            self.layout.addWidget(edit)

        self.setLayout(self.layout)

    def set_value(self):
        def _get_val(edit):
            try:
                return float(edit.text())
            except Exception:
                return 0.0
        val = [
            _get_val(self.x_edit),
            _get_val(self.y_edit),
            _get_val(self.z_edit),
            _get_val(self.w_edit)
        ]
        self.data['m_Value'] = val
        _sync_item_text(self.parent_item, val)


class VariableColor(QWidget):
    def __init__(self, value=None, type=None, parent_item=None):
        super().__init__()
        self.parent_item = parent_item
        parsed = _parse_seq(value, [255, 255, 255], 3)
        self.data = {'m_DataType': type or 'Color', 'm_Value': [int(float(x)) for x in parsed]}
        self.setupUI()

    def setupUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.r_edit = QLineEdit()
        self.g_edit = QLineEdit()
        self.b_edit = QLineEdit()

        for idx, edit in enumerate((self.r_edit, self.g_edit, self.b_edit)):
            try:
                edit.setText(str(self.data['m_Value'][idx]))
            except Exception:
                edit.setText("255")
            edit.setFocusPolicy(Qt.StrongFocus)
            edit.textChanged.connect(self.set_value)
            self.layout.addWidget(edit)

        self.setLayout(self.layout)

    def set_value(self):
        def _get_val(edit):
            try:
                return max(0, min(255, int(float(edit.text()))))
            except Exception:
                return 255
        val = [
            _get_val(self.r_edit),
            _get_val(self.g_edit),
            _get_val(self.b_edit)
        ]
        self.data['m_Value'] = val
        _sync_item_text(self.parent_item, val)
