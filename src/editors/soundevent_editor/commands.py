import ast
import uuid
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QUndoCommand
from src.widgets import HierarchyItemModel

class DeleteTreeItemCommand(QUndoCommand):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.items_data = self.collect_selected_item_data()
        self.setText("Delete Selected Items")

    def redo(self):
        if self.items_data:
            self.remove_tree_items()

    def undo(self):
        if self.items_data:
            self.restore_tree_items(self.items_data)

    def remove_tree_items(self):
        """Remove selected tree items."""
        selected_items = self.model.selectedItems()
        for item in selected_items:
            if item and item != self.model.invisibleRootItem():
                parent = item.parent() or self.model.invisibleRootItem()
                parent.takeChild(parent.indexOfChild(item))

    def restore_tree_items(self, items_data):
        """Restore tree items from stored data."""
        for item_data in items_data:
            self.add_item_from_data(item_data, self.model.invisibleRootItem())

    def add_item_from_data(self, item_data, parent):
        """Restore an item directly under the root."""
        value_dict = ast.literal_eval(item_data['value'])
        new_item = HierarchyItemModel(
            _data=item_data['value'],
            _name=item_data['text'],
        )
        new_item.setData(0, Qt.UserRole, str(uuid.uuid4()))  # Assign a new unique ID

        parent.addChild(new_item)

    def collect_selected_item_data(self):
        """Collect data of selected items."""
        selected_items = self.model.selectedItems()
        selected_items_data = []

        for item in selected_items:
            if item:
                item_data = {
                    'text': item.data(0, Qt.UserRole),
                    'value': item.text(1)
                }
                selected_items_data.append(item_data)

        return selected_items_data