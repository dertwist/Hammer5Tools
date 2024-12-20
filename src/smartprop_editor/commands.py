import ast
import json
import uuid
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QUndoCommand
from src.widgets import HierarchyItemModel
from src.smartprop_editor._common import get_clean_class_name_value, get_ElementID_key
class DeleteTreeItemCommand(QUndoCommand):
    def __init__(self, model, parent=None):
        super().__init__()
        self.model = model
        self.parent = parent
        self.items_data = self.collect_selected_item_data()
        self.setText("Delete Selected Items")

    def redo(self):
        if self.items_data:
            self.remove_tree_items()

    def undo(self):
        if self.items_data:
            self.restore_tree_items(self.items_data)

    def remove_tree_items(self):
        """Remove selected tree items and store their data for undo."""
        selected_items = self.model.selectedItems()

        for item in selected_items:
            if item and item != self.model.invisibleRootItem():
                parent = item.parent() or self.model.invisibleRootItem()
                parent.takeChild(parent.indexOfChild(item))

    def restore_tree_items(self, items_data):
        """Restore tree items from stored data during undo."""
        for item_data in items_data:
            parent_item = self.get_parent_item(item_data)
            if parent_item is not None:
                self.add_item_from_data(item_data, parent_item)
            else:
                # If the parent is None (i.e., invisible root), add to the root.
                if item_data['parent_id'] is None:
                    self.add_item_from_data(item_data, self.model.invisibleRootItem())
                else:
                    print(f"Warning: Parent item not found for '{item_data['text']}'.")

    def get_parent_item(self, item_data):
        """Retrieve the parent item for a given item data based on its unique ID."""
        if item_data['is_top_level']:
            if 0 <= item_data['parent_index'] < self.model.topLevelItemCount():
                return self.model.topLevelItem(item_data['parent_index'])
            else:
                print(f"Warning: Invalid parent index {item_data['parent_index']} for top-level item.")
                return None
        else:
            parent_id = item_data['parent_id']
            for i in range(self.model.topLevelItemCount()):
                top_item = self.model.topLevelItem(i)
                parent_item = self.find_item_by_id(top_item, parent_id)
                if parent_item:
                    return parent_item
            print(f"Warning: Parent not found for item '{item_data['text']}' with ID {parent_id}.")
            return None

    def find_item_by_id(self, item, item_id):
        """Recursively search for an item by its unique ID."""
        if item.data(0, Qt.UserRole) == item_id:
            return item
        for i in range(item.childCount()):
            found_item = self.find_item_by_id(item.child(i), item_id)
            if found_item:
                return found_item
        return None

    def add_item_from_data(self, item_data, parent=None):
        """Helper to restore an item and its children in the original position."""
        value_dict = ast.literal_eval(item_data['value'])
        new_item = HierarchyItemModel(_data=item_data['value'], _name=item_data['text'], _class=get_clean_class_name_value(value_dict), _id=get_ElementID_key(value_dict))
        new_item.setData(0, Qt.UserRole, item_data.get('id', str(uuid.uuid4())))  # Assign unique ID if not provided


        for child_data in item_data.get('children', []):
            self.add_item_from_data(child_data, new_item)

        if parent is not None:
            parent.addChild(new_item)
        else:
            if item_data['is_top_level']:
                self.model.insertTopLevelItem(item_data['position'], new_item)
            else:
                raise ValueError(f"Error: Could not restore item '{item_data['text']}' without a parent.")

    def collect_selected_item_data(self):
        """Collect data of selected items, including position, parent ID, and children."""
        selected_indexes = self.model.selectedIndexes()
        selected_items = [self.model.itemFromIndex(index) for index in selected_indexes]
        selected_items = list(set(selected_items))

        selected_items_data = []

        for item in selected_items:
            if item:
                item_data = self.get_item_data(item)
                selected_items_data.append(item_data)

        return selected_items_data

    def get_item_data(self, item):
        """Gather data of an item, including its position, parent, and unique ID."""
        parent = item.parent() or item.treeWidget().invisibleRootItem()
        position = parent.indexOfChild(item)

        is_top_level = parent == item.treeWidget().invisibleRootItem()
        parent_index = (
            item.treeWidget().indexOfTopLevelItem(item) if is_top_level
            else parent.indexOfChild(item)
        )

        item_id = item.data(0, Qt.UserRole) or str(uuid.uuid4())
        item.setData(0, Qt.UserRole, item_id)

        parent_id = parent.data(0, Qt.UserRole) if parent != item.treeWidget().invisibleRootItem() else None
        children_data = [self.get_item_data(item.child(i)) for i in range(item.childCount())]

        return {
            'id': item_id,
            'text': item.text(0),
            'value': item.text(1),
            'position': position,
            'parent_index': parent_index,
            'parent_id': parent_id,
            'is_top_level': is_top_level,
            'children': children_data
        }
