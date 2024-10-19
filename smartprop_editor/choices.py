from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt
from smartprop_editor.widgets import ComboboxTreeChild, ComboboxDynamicItems, ComboboxVariables
from preferences import debug

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
        self.tree.setItemWidget(item, 0, combobox)