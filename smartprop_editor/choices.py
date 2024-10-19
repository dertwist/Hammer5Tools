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

        self.add_choice()
    def add_choice(self):
        """Adding choice"""
        item = QTreeWidgetItem()
        item.setText(0,self.name)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        root = self.tree.invisibleRootItem()
        root.addChild(item)
        for option in self.options:
            self.add_option(parent=item, name=option['m_Name'], variables=option['m_VariableValues'])

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
        # Combobox
        combobox = ComboboxVariables(layout=self.variables_scrollArea)
        combobox.setCurrentText(name)
        combobox.addItem(name)

        widget = VariableWidget()
        parent.treeWidget().setItemWidget(item, 1, widget)

        combobox.clicked.connect(lambda : self.variable_edit_line(type, item))
        self.tree.setItemWidget(item, 0, combobox)
    def variable_edit_line(self, type, parent):
        """Select widget basing on the variable type"""
        if type in var_choice_identification_bool:
            debug(f'Var choice type bool')
        elif type in var_choice_identification_float:
            debug(f'Var choice type float')
        elif type in var_choice_identification_int:
            debug(f'Var choice type int')
        else:
            debug(f'Var choice type is generic ({type})')

class VariableWidget(QWidget):
    def __init__(self, value=None, type=None, parent=None):
        super().__init__()
        self.layout = QHBoxLayout()  # Create a QVBoxLayout for the layout
        self.layout.setContentsMargins(0,0,0,0)
        editline = QLineEdit()
        slider = QSlider()
        slider.setOrientation(Qt.Orientation.Horizontal)
        self.layout.addWidget(editline)
        self.layout.addWidget(slider)
        self.setLayout(self.layout)  # Set the layout for the VariableWidget


