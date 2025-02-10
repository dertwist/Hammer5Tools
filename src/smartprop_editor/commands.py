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
        # Collect a deep copy of the selected items' serialized data
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
                index = parent.indexOfChild(item)
                # Store the sibling index for ordering purposes.
                item_data = self.get_item_data(item)
                item_data['position'] = index
                parent.takeChild(index)

    def restore_tree_items(self, items_data):
        """
        Restore tree items from stored data during undo.
        Reconstruct each item's hierarchy and insert at its original position.
        """
        for item_data in items_data:
            # For top-level items, parent_id is None.
            if item_data['parent_id'] is None:
                parent_item = self.model.invisibleRootItem()
            else:
                parent_item = self.get_parent_item(item_data)
                # If not found, use invisibleRootItem as fallback.
                if parent_item is None:
                    print(f"Warning: Parent not found for '{item_data['text']}' with ID {item_data['parent_id']}. Restoring as top-level.")
                    parent_item = self.model.invisibleRootItem()
            self.add_item_from_data(item_data, parent_item)

    def get_parent_item(self, item_data):
        """
        Retrieve the parent item for a given item data based on its unique ID.
        Returns the parent item reference or None if not found.
        """
        parent_id = item_data['parent_id']
        if parent_id is None:
            return None
        # Recursively search in all top-level items.
        for i in range(self.model.topLevelItemCount()):
            top_item = self.model.topLevelItem(i)
            found_item = self.find_item_by_id(top_item, parent_id)
            if found_item:
                return found_item
        print(f"Warning: Parent with ID {parent_id} not found for item '{item_data['text']}'.")
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

    def add_item_from_data(self, item_data, parent):
        """
        Recursively re-create an item and its children from its serialized data,
        enforcing structure preservation.
        """
        try:
            # Ensure we operate on a dictionary.
            value_dict = ast.literal_eval(item_data['value'])
        except Exception as e:
            print(f"Error while parsing value for '{item_data['text']}': {e}")
            value_dict = {}

        new_item = HierarchyItemModel(
            _data=item_data['value'],
            _name=item_data['text'],
            _class=get_clean_class_name_value(value_dict),
            _id=get_ElementID_key(value_dict)
        )
        # Preserve the item's unique ID.
        new_item.setData(0, Qt.UserRole, item_data.get('id', str(uuid.uuid4())))

        # Recursively restore children.
        for child_data in item_data.get('children', []):
            self.add_item_from_data(child_data, new_item)

        # Insert at the originally serialized position if valid.
        position = item_data.get('position')
        if position is not None and 0 <= position < parent.childCount():
            parent.insertChild(position, new_item)
        else:
            parent.addChild(new_item)

    def collect_selected_item_data(self):
        """
        Collect a deep serialized representation of selected items,
        including their hierarchy and original positions.
        """
        selected_indexes = self.model.selectedIndexes()
        selected_items = [self.model.itemFromIndex(index) for index in selected_indexes]
        # Remove duplicates caused by multiple column selections.
        selected_items = list(set(selected_items))

        items_data = []
        for item in selected_items:
            if item:
                items_data.append(self.get_item_data(item))
        return items_data

    def get_item_data(self, item):
        """
        Gather data of an item, including its text, parsed value,
        child hierarchy, its sibling index, and unique identifiers.
        """
        parent = item.parent() or item.treeWidget().invisibleRootItem()
        position = parent.indexOfChild(item)
        is_top_level = (parent == item.treeWidget().invisibleRootItem())
        # For top-level items, use None for parent_id.
        parent_id = None if is_top_level else parent.data(0, Qt.UserRole)
        # Ensure the unique ID is preserved.
        item_id = item.data(0, Qt.UserRole) or str(uuid.uuid4())
        item.setData(0, Qt.UserRole, item_id)
        # Recursively collect child data.
        children_data = [self.get_item_data(item.child(i)) for i in range(item.childCount())]

        return {
            'id': item_id,
            'text': item.text(0),
            'value': item.text(1),
            'position': position,
            'parent_id': parent_id,
            'is_top_level': is_top_level,
            'children': children_data
        }

# End of DeleteTreeItemCommand class