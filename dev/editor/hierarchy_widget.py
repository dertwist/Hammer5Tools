from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Signal, Qt


class HierarchyWidget(QTreeWidget):
    item_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("JSON Hierarchy")
        self.itemClicked.connect(self.on_item_clicked)

    def set_data(self, data):
        self.clear()
        self.add_items(self.invisibleRootItem(), data)
        self.expandAll()

    def add_items(self, parent_item, value, key="root"):
        if isinstance(value, dict):
            item = QTreeWidgetItem(parent_item, [str(key)])
            item.setData(0, Qt.UserRole, value)
            for k, v in value.items():
                self.add_items(item, v, k)
        elif isinstance(value, list):
            item = QTreeWidgetItem(parent_item, [str(key)])
            item.setData(0, Qt.UserRole, value)
            for i, v in enumerate(value):
                self.add_items(item, v, f"[{i}]")
        else:
            item = QTreeWidgetItem(parent_item, [f"{key}: {value}"])
            item.setData(0, Qt.UserRole, value)

    def on_item_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        self.item_selected.emit(data)