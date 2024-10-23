from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QLineEdit, QVBoxLayout, QSlider, QHBoxLayout, QCheckBox
from PySide6.QtCore import Qt
from widgets import ComboboxTreeChild, ComboboxDynamicItems, ComboboxVariables
from preferences import debug
var_choice_identification_bool = ['boolean', 'bool']
var_choice_identification_float = ['float']
var_choice_identification_int = ['integer', 'int']
class AddChoice():
    def __init__(self, tree=QTreeWidget, name=None, default=None, variables_scrollArea=None):
        super().__init__()
        self.tree = tree
        self.variables_scrollArea = variables_scrollArea
        if name == None:
            self.name = 'Choice'
        else:
            self.name = name
        if default == None:
            self.default = 'default'
        else:
            self.default = default
        self.item = QTreeWidgetItem()
        self.item.setText(0,self.name)
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
        self.item.setText(0,name)
        self.item.setText(2,'option')
        self.item.setFlags(self.item.flags() | Qt.ItemIsEditable)
        parent.addChild(self.item)
class AddVariable():
    def __init__(self, parent=QTreeWidgetItem, name=None, value=None, variables_scrollArea=None, type=None):
        super().__init__()
        """Adding variable tree item"""
        item = QTreeWidgetItem()
        item.setText(0, name)
        item.setText(2, 'variable')
        item.setText(1, str(value))
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        parent.addChild(item)
        # Combobox var
        combobox = ComboboxVariables(layout=variables_scrollArea)
        combobox.setCurrentText(name)
        combobox.addItem(name)

        combobox.changed.connect(lambda value_dict: self.variable_edit_line(value_dict, parent=item))
        value_dict = {'name': name, 'class': type, 'm_default': value}
        self.variable_edit_line(value_dict, parent=item)
        parent.treeWidget().setItemWidget(item, 0, combobox)

    def variable_edit_line(self, value_dict, parent):
        """Select widget basing on the variable type"""
        type = value_dict['class'].lower()
        if type in var_choice_identification_bool:
            debug(f'Var choice type bool')
            widget = VariableBool(value=value_dict['m_default'], type=value_dict['class'])
            parent.treeWidget().setItemWidget(parent, 1, widget)
        elif type in var_choice_identification_float:
            debug(f'Var choice type float')
            widget = VariableFloat(value=value_dict['m_default'], type=value_dict['class'])
            parent.treeWidget().setItemWidget(parent, 1, widget)
        elif type in var_choice_identification_int:
            debug(f'Var choice type int')
            widget = VariableFloat(value=value_dict['m_default'], type=value_dict['class'])
            parent.treeWidget().setItemWidget(parent, 1, widget)
        else:
            debug(f'Var choice type is generic ({type})')
            widget = VariableWidget(value=value_dict['m_default'], type=value_dict['class'])
            parent.treeWidget().setItemWidget(parent, 1, widget)
class VariableWidget(QWidget):
    def __init__(self, value=None, type=None):
        super().__init__()
        self.data = {'m_DataType': type, 'm_Value': value}
        self.setupUI()

    def setupUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        editline = QLineEdit()
        editline.setText(str(self.data['m_Value']))
        editline.setFocusPolicy(Qt.StrongFocus)
        self.layout.addWidget(editline)
        self.setLayout(self.layout)
    def set_value(self):
        self.data.update({'m_Value': self.editline.text()})


class VariableFloat(QWidget):
    def __init__(self, value=None, type=None):
        super().__init__()
        self.data = {'m_DataType': type, 'm_Value': value}
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
        self.editline.setFocusPolicy(Qt.StrongFocus)

        self.layout.addWidget(self.editline)
        self.layout.addWidget(self.slider)

        value = self.data['m_Value']
        self.editline.setText(str(value))
        try:
            self.slider.setValue(int(value * 100))
        except:
            pass

        self.editline.textChanged.connect(self.on_editline_changed)
        self.slider.valueChanged.connect(self.on_slider_changed)

        self.setLayout(self.layout)

    def on_editline_changed(self, text_value):
        try:
            float_value = float(text_value)
        except ValueError:
            float_value = 0
        self.slider.setValue(int(float_value * 100))
        self.set_value()

    def on_slider_changed(self, slider_value):
        float_value = slider_value / 100.0
        self.editline.setText(str(float_value))
        self.set_value()
    def set_value(self):
        self.data.update({'m_Value': self.slider.value()/ 100.0})

class VariableBool(QWidget):
    def __init__(self, value=None, type=None):
        super().__init__()
        self.data = {'m_DataType': type, 'm_Value': value}
        self.setupUI()

    def setupUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.checkbox = QCheckBox()

        self.layout.addWidget(self.checkbox)

        value = self.data['m_Value']
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
