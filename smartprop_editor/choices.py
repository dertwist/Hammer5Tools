from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QLineEdit, QVBoxLayout, QSlider, QHBoxLayout
from PySide6.QtCore import Qt
from smartprop_editor.widgets import ComboboxTreeChild, ComboboxDynamicItems, ComboboxVariables
from preferences import debug
var_choice_identification_bool = ['boolean', 'bool']
var_choice_identification_float = ['float']
var_choice_identification_int = ['integer', 'int']
class AddChoice():
    def __init__(self, tree=QTreeWidget, name=None, default=None, options=None, variables_scrollArea=None):
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
        self.options = options
        debug(f'Options of {self.name}: \n {self.options}')
        debug(f'Default of {self.name}: \n {self.default}')
    def add_choice(self):
        """Adding choice"""
        item = QTreeWidgetItem()
        item.setText(0,self.name)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        root = self.tree.invisibleRootItem()
        root.addChild(item)
        for option in self.options:
            self.add_option(parent=item, name=option['m_Name'], variables=option['m_VariableValues'])
            # AddOption(parent=item, name=option['m_Name'])

        combobox = ComboboxTreeChild(layout=root, root=item)
        combobox.setCurrentText(self.default)
        combobox.addItem(self.default)
        self.tree.setItemWidget(item, 1, combobox)


    def add_option(self, name, variables, parent):
        """Adding option"""
        item = QTreeWidgetItem()
        item.setText(0,name)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        parent.addChild(item)
        for variable in variables:
            self.add_variable(name=variable['m_TargetName'], type=variable['m_DataType'], value=variable['m_Value'], parent=item)
    def add_variable(self, name, type, value, parent):
        """Adding variable tree item"""
        item = QTreeWidgetItem()
        item.setText(0,name)
        item.setText(1,str(value))
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        parent.addChild(item)
        # Combobox var
        combobox = ComboboxVariables(layout=self.variables_scrollArea)
        combobox.setCurrentText(name)
        combobox.addItem(name)

        # Init Widget
        # widget = VariableWidget()
        # parent.treeWidget().setItemWidget(item, 1, widget)

        combobox.changed.connect(lambda value_dict: self.variable_edit_line(value_dict, parent=item))
        value_dict = {'name': name, 'class': type, 'm_default': value}
        self.variable_edit_line(value_dict, parent=item)
        self.tree.setItemWidget(item, 0, combobox)
    def variable_edit_line(self, value_dict, parent):
        """Select widget basing on the variable type"""
        print(value_dict)
        type = value_dict['class'].lower()
        if type in var_choice_identification_bool:
            debug(f'Var choice type bool')
        elif type in var_choice_identification_float:
            debug(f'Var choice type float')
            widget = VariableFloat(value=value_dict['m_default'], type=value_dict['class'])
            parent.treeWidget().setItemWidget(parent,1, widget)
        elif type in var_choice_identification_int:
            debug(f'Var choice type int')
            widget = VariableFloat(value=value_dict['m_default'], type=value_dict['class'])
            parent.treeWidget().setItemWidget(parent,1, widget)
        else:
            debug(f'Var choice type is generic ({type})')
            widget = VariableWidget(value=value_dict['m_default'], type=value_dict['class'])
            parent.treeWidget().setItemWidget(parent,1, widget)
class AddOption():
    def __init__(self, parent=None, name=None):
        super().__init__()
        item = QTreeWidgetItem()
        item.setText(0,name)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        parent.addChild(item)
class AddVariable():
    def __init__(self, parent=None, name=None):
        super().__init__()
        item = QTreeWidgetItem()
        item.setText(0,name)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        parent.addChild(item)
class VariableWidget(QWidget):
    def __init__(self, value=None, type=None):
        super().__init__()
        self.data = {'m_Value': value, 'm_DataType': type}
        self.setupUI()

    def setupUI(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        editline = QLineEdit()
        editline.setFocusPolicy(Qt.StrongFocus)
        self.layout.addWidget(editline)
        self.setLayout(self.layout)
    def set_value(self):
        self.data.update({'m_Value': self.editline.text()})


class VariableFloat(QWidget):
    def __init__(self, value=None, type=None):
        super().__init__()
        self.data = {'m_Value': value, 'm_DataType': type}
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
        self.slider.setValue(int(value * 100))

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
        self.data.update({'m_Value': self.editline.text()})
