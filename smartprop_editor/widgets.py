from PySide6.QtWidgets import QComboBox, QTreeWidgetItem, QTreeWidget
from PySide6.QtCore import Signal

class ComboboxDynamicItems(QComboBox):
    clicked = Signal()

    def __init__(self, parent=None, items=None):
        super().__init__(parent)
        self.setStyleSheet('padding:2px; font: 580 9pt "Segoe UI"; padding-left:4px;')
        self.items = items

    def updateItems(self):
        current = self.currentText()
        self.clear()
        self.addItems(self.items)
        if current in self.items:
            self.setCurrentText(current)

    def showPopup(self):
        self.clicked.emit()
        self.updateItems()
        super().showPopup()


    def wheelEvent(self, event):
        event.ignore()

class ComboboxVariables(ComboboxDynamicItems):

    def __init__(self, parent=None, layout=None):
        super().__init__(parent)
        self.variables_scrollArea = layout
        self.items = None

    def updateItems(self):
        self.items = []
        for item in self.get_variables():
            self.items.append(item['name'])

        current = self.currentText()
        self.clear()
        self.addItems(self.items)
        if current in self.items:
            self.setCurrentText(current)
    def get_variables(self):
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                var = {'name': widget.name, 'class': widget.var_class}
                data_out.append(var)
        return data_out

class ComboboxTreeChild(ComboboxDynamicItems):
    def __init__(self, parent=None, layout=QTreeWidget, root=QTreeWidgetItem):
        super().__init__(parent)
        self.layout = layout
        self.root = root
        self.items = None

    def updateItems(self):
        self.items = ['default']
        self.items.extend(self.get_child(self.root))
        current = self.currentText()
        self.clear()
        self.addItems(self.items)
        if current in self.items:
            self.setCurrentText(current)

    def get_child(self, parent_item):
        data_out = []
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            data_out.append(child_item.text(0))

        return data_out