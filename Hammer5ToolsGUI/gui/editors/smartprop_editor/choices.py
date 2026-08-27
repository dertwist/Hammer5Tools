"""Widgets that render the SmartProp choices tree.

What a choice *means* -- the KV3 key aliases, which editor a variable class
gets, how a raw value coerces -- lives in choices_model.py. This module only
draws it.
"""
from functools import partial

from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QWidget, QLineEdit, QSlider,
    QHBoxLayout, QCheckBox
)
from PySide6.QtCore import Qt
from gui.editors.smartprop_editor.combobox_variables import ComboboxVariablesWidget
from gui.editors.smartprop_editor._common import is_category_widget
from gui.editors.smartprop_editor.choices_model import (
    DEFAULT_TYPE_NAME, KIND_BOOL, KIND_COLOR, KIND_FLOAT, KIND_INT,
    KIND_STRING, KIND_VECTOR2D, KIND_VECTOR3D, KIND_VECTOR4D,
    clamp_channel, coerce, to_float, to_int, value_kind,
)
from gui.widgets import ComboboxTreeChild


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
        """Swap in the editor that matches the variable's type."""
        if not parent or not parent.treeWidget():
            return

        var_name = value_dict.get('name')
        if var_name:
            parent.setText(0, var_name)

        old_widget = parent.treeWidget().itemWidget(parent, 1)
        if old_widget:
            old_widget.deleteLater()

        parent.treeWidget().setItemWidget(parent, 1, make_value_editor(
            value_dict.get('class') or '', value_dict.get('m_default'), parent))


def make_value_editor(var_class, value, parent_item=None):
    """The editor widget for a variable of `var_class`, showing `value`."""
    kind = value_kind(var_class)
    return _EDITORS[kind](kind, value, var_class, parent_item)


class ValueEditor(QWidget):
    """Base for the inline value editors in the choices tree.

    `data` is what the document and the KV3 writer read back off the widget,
    and column 1 of the tree item mirrors it so a row still reads correctly
    when no editor is attached.
    """

    def __init__(self, kind, value, var_class=None, parent_item=None):
        super().__init__()
        self.kind = kind
        self.parent_item = parent_item
        self.data = {
            'm_DataType': var_class or DEFAULT_TYPE_NAME[kind],
            'm_Value': coerce(kind, value),
        }
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setup_ui()
        self.setLayout(self.layout)

    def setup_ui(self):
        raise NotImplementedError

    def _commit(self, value):
        self.data['m_Value'] = value
        if self.parent_item:
            self.parent_item.setText(1, str(value if value is not None else ""))

    def _line_edit(self, text):
        edit = QLineEdit()
        edit.setText(str(text))
        edit.setFocusPolicy(Qt.StrongFocus)
        self.layout.addWidget(edit)
        return edit


class StringEditor(ValueEditor):
    def setup_ui(self):
        self.editline = self._line_edit(self.data['m_Value'])
        self.editline.textChanged.connect(self.set_value)

    def set_value(self):
        self._commit(self.editline.text())


class BoolEditor(ValueEditor):
    def setup_ui(self):
        self.checkbox = QCheckBox()
        self.layout.addWidget(self.checkbox)
        self.checkbox.setChecked(self.data['m_Value'])
        self.checkbox.setText(str(self.checkbox.isChecked()))
        self.checkbox.checkStateChanged.connect(self.set_value)

    def set_value(self):
        self.checkbox.setText(str(self.checkbox.isChecked()))
        self._commit(self.checkbox.isChecked())


# Per kind: how many slider steps make one unit, the slider's starting bound,
# and how far past a typed value the bound grows when it no longer fits.
_SLIDER = {
    KIND_INT: (1, 100, 2),
    KIND_FLOAT: (100, 1000, 10),
}


class NumberEditor(ValueEditor):
    def setup_ui(self):
        self.scale, base, self.growth = _SLIDER[self.kind]
        value = self.data['m_Value']

        self.editline = self._line_edit(value)
        self.editline.setMaximumWidth(64)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(-base)
        self.slider.setMaximum(base)
        self.slider.setFocusPolicy(Qt.StrongFocus)
        self.slider.wheelEvent = lambda event: None
        self.layout.addWidget(self.slider)

        try:
            self.slider.setValue(int(value * self.scale))
        except (ValueError, TypeError, OverflowError):
            pass

        self.editline.textChanged.connect(self.on_editline_changed)
        self.slider.valueChanged.connect(self.on_slider_changed)

    def _to_number(self, text):
        return to_int(text) if self.kind == KIND_INT else to_float(text)

    def on_editline_changed(self):
        value = self._to_number(self.editline.text())
        steps = value * self.scale
        if steps > self.slider.maximum() or steps < self.slider.minimum():
            bound = int(abs(steps) * self.growth + _SLIDER[self.kind][1])
            self.slider.setMaximum(bound)
            self.slider.setMinimum(-bound)
        # The slider is a second view of the same number; moving it to match
        # what was typed must not read back as a fresh edit.
        try:
            self.slider.blockSignals(True)
            self.slider.setValue(int(steps))
        except (ValueError, TypeError, OverflowError):
            pass
        finally:
            self.slider.blockSignals(False)
        self._commit(value)

    def on_slider_changed(self):
        value = self.slider.value() / self.scale
        if self.kind == KIND_INT:
            value = int(value)
        self.editline.setText(str(value))
        self._commit(value)


# Per kind: the labels of the components, in order.
_COMPONENTS = {
    KIND_VECTOR2D: ('x', 'y'),
    KIND_VECTOR3D: ('x', 'y', 'z'),
    KIND_VECTOR4D: ('x', 'y', 'z', 'w'),
    KIND_COLOR: ('r', 'g', 'b'),
}


class VectorEditor(ValueEditor):
    """One line edit per component, for vectors and for colours."""

    def setup_ui(self):
        self.edits = []
        for name, value in zip(_COMPONENTS[self.kind], self.data['m_Value']):
            edit = self._line_edit(value)
            edit.textChanged.connect(self.set_value)
            setattr(self, f'{name}_edit', edit)
            self.edits.append(edit)

    def set_value(self):
        read = clamp_channel if self.kind == KIND_COLOR else to_float
        self._commit([read(edit.text()) for edit in self.edits])


_EDITORS = {
    KIND_STRING: StringEditor,
    KIND_BOOL: BoolEditor,
    KIND_INT: NumberEditor,
    KIND_FLOAT: NumberEditor,
    KIND_COLOR: VectorEditor,
    KIND_VECTOR2D: VectorEditor,
    KIND_VECTOR3D: VectorEditor,
    KIND_VECTOR4D: VectorEditor,
}


def build_choices_tree(tree, state, variables_scrollArea=None, element_id_generator=None):
    """Append the choices in `state` to `tree`, rows and inline editors both."""
    for choice in state:
        choice_item = AddChoice(
            tree=tree,
            name=choice.get('name', 'Choice'),
            default=choice.get('default', ''),
            variables_scrollArea=variables_scrollArea,
        ).item
        for option in choice.get('options', []):
            option_item = AddOption(
                parent=choice_item, name=option.get('name', 'Option')
            ).item
            for variable in option.get('variables', []):
                AddVariable(
                    element_id_generator=element_id_generator,
                    parent=option_item,
                    variables_scrollArea=variables_scrollArea,
                    name=variable.get('name', ''),
                    type=variable.get('type', ''),
                    value=variable.get('value', ''),
                )
            option_item.setExpanded(option.get('expanded', False))
        choice_item.setExpanded(choice.get('expanded', False))


def read_choices_tree(tree):
    """Read `tree` back into the choices state shape."""
    state = []
    root = tree.invisibleRootItem()
    for ci in range(root.childCount()):
        choice = root.child(ci)
        combo = tree.itemWidget(choice, 1)
        default_txt = combo.currentText() if combo and hasattr(combo, 'currentText') else ''
        if default_txt == "None":
            default_txt = ""
        options = []
        for oi in range(choice.childCount()):
            option = choice.child(oi)
            variables = []
            for vi in range(option.childCount()):
                var_item = option.child(vi)
                name_widget = tree.itemWidget(var_item, 0)
                var_name = (
                    name_widget.combobox.currentText()
                    if name_widget and hasattr(name_widget, 'combobox')
                    else var_item.text(0)
                )
                if var_name == "None" or not var_name:
                    var_name = var_item.text(0)

                val_widget = tree.itemWidget(var_item, 1)
                if val_widget and hasattr(val_widget, 'data'):
                    var_type = val_widget.data.get('m_DataType', '')
                    var_value = val_widget.data.get('m_Value', '')
                else:
                    var_type = ''
                    var_value = var_item.text(1)
                variables.append({
                    'name': var_name,
                    'type': var_type,
                    'value': var_value,
                })
            options.append({
                'name': option.text(0),
                'expanded': option.isExpanded(),
                'variables': variables,
            })
        state.append({
            'name': choice.text(0),
            'default': default_txt,
            'expanded': choice.isExpanded(),
            'options': options,
        })
    return state
