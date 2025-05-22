import ast
import uuid
from PySide6.QtWidgets import QTreeWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QUndoCommand
from src.widgets import HierarchyItemModel
from src.editors.smartprop_editor._common import get_clean_class_name_value, get_ElementID_key
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QAbstractItemView
)
from PySide6.QtGui import QUndoStack, QUndoCommand

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

class GroupElementsCommand(QUndoCommand):
    def __init__(self, tree: QTreeWidget):
        """
        Initialize the command.
        Args:
            tree (QTreeWidget): The tree widget containing items to be grouped.
        """
        super().__init__("Group Selected Items")
        self.tree = tree
        # Will store the created group element and backup info for each moved item
        self.group_element = None
        self.moved_items_info = []  # List of tuples: (item, old_parent, old_index)

    def redo(self):
        """
        Execute the grouping command:
         - Create a new group element.
         - Remove selected items from their current parent.
         - Add selected items as children of the new group.
         - Insert the group element as a child of the invisibleRootItem.

        """
        # Prepare the group element data as a dictionary.
        group_data = {'_class': 'CSmartPropElement_Group',
                      'm_Modifiers': [],
                      'm_SelectionCriteria': []}
        # Retrieve a unique ID for the group element using the get_ElementID_key helper.
        group_id = get_ElementID_key(group_data)
        # Create a new HierarchyItemModel using both data and generated ID.
        self.group_element = HierarchyItemModel(
            _data=group_data,
            _name='Group',
            _class='CSmartPropElement_Group',
            _id=group_id
        )

        # Retrieve selected items from the tree.
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        invisible_root = self.tree.invisibleRootItem()
        self.moved_items_info = []

        # For each selected item, remove it from its current parent and store its original state.
        for item in selected_items:
            if item is None or item == invisible_root:
                continue
            old_parent = item.parent() or invisible_root
            old_index = old_parent.indexOfChild(item)
            self.moved_items_info.append((item, old_parent, old_index))
            # Remove the item from its old parent.
            old_parent.takeChild(old_index)
            # Add the item as a child of the new group element.
            self.group_element.addChild(item)

        # Insert the new group element into the invisible root of the tree.
        invisible_root.addChild(self.group_element)

    def undo(self):
        """
        Undo the grouping:
         - Remove the group element from the tree.
         - Restore each moved item to its original parent and position.
        """
        if self.group_element is None:
            return

        invisible_root = self.tree.invisibleRootItem()
        # Remove the group element from the tree.
        invisible_root.removeChild(self.group_element)

        # For each moved item, remove it from the group element (if exists)
        # and reinsert it into its original parent's children list at the stored index.
        for item, old_parent, old_index in self.moved_items_info:
            current_index = self.group_element.indexOfChild(item)
            if current_index != -1:
                self.group_element.takeChild(current_index)
            old_parent.insertChild(old_index, item)

        # Clear the stored group element reference.
        self.group_element = None


class AddItemCommand(QUndoCommand):
    _item_refs = set()  # Prevent deletion by keeping references

    def __init__(self, tree, parent_item, item: QTreeWidgetItem, index=None):
        super().__init__("Add Item")
        self.tree = tree
        self.parent_item = parent_item
        self.item = item
        self.index = index
        AddItemCommand._item_refs.add(self.item)

    def redo(self):
        if self.parent_item:
            if self.index is None:
                self.parent_item.addChild(self.item)
            else:
                self.parent_item.insertChild(self.index, self.item)
            self.parent_item.setExpanded(True)
        else:
            if self.index is None:
                self.tree.addTopLevelItem(self.item)
            else:
                self.tree.insertTopLevelItem(self.index, self.item)

    def undo(self):
        if self.parent_item:
            self.parent_item.removeChild(self.item)
        else:
            idx = self.tree.indexOfTopLevelItem(self.item)
            if idx != -1:
                self.tree.takeTopLevelItem(idx)


class RemoveItemCommand(QUndoCommand):
    _item_refs = set()  # Prevent deletion by keeping references

    def __init__(self, tree, items):
        super().__init__("Remove Item(s)")
        self.tree = tree
        # Accept a list of items, even if only one
        if not isinstance(items, (list, tuple)):
            items = [items]
        self.items = items
        RemoveItemCommand._item_refs.update(self.items)
        self.parents = []
        self.indices = []
        for item in self.items:
            parent = item.parent()
            self.parents.append(parent)
            if parent:
                idx = parent.indexOfChild(item)
            else:
                idx = self.tree.indexOfTopLevelItem(item)
            self.indices.append(idx)

    def redo(self):
        # Remove items in reverse order to avoid index shifting
        for item, parent in sorted(zip(self.items, self.parents), key=lambda x: (id(x[1]) if x[1] else -1), reverse=True):
            if parent:
                idx = parent.indexOfChild(item)
                if idx != -1:
                    parent.takeChild(idx)
            else:
                idx = self.tree.indexOfTopLevelItem(item)
                if idx != -1:
                    self.tree.takeTopLevelItem(idx)

    def undo(self):
        # Restore items in original order
        for item, parent, idx in zip(self.items, self.parents, self.indices):
            if parent:
                if idx == -1 or idx > parent.childCount():
                    parent.addChild(item)
                else:
                    parent.insertChild(idx, item)
                parent.setExpanded(True)
            else:
                if idx == -1 or idx > self.tree.topLevelItemCount():
                    self.tree.addTopLevelItem(item)
                else:
                    self.tree.insertTopLevelItem(idx, item)


class MoveItemsCommand(QUndoCommand):
    """
    Command to move multiple QTreeWidgetItems, memorizing their original and new positions for undo/redo.
    """

    def __init__(self, tree, move_infos):
        super().__init__("Move Items")
        self.tree = tree
        # move_infos: list of dicts with keys: item, old_parent, old_index, new_parent, new_index
        self.move_infos = move_infos

    def _find_current_index(self, parent, item):
        if parent is None:
            return self.tree.indexOfTopLevelItem(item)
        else:
            return parent.indexOfChild(item)

    def _move(self, infos, src_to_dst=True):
        if src_to_dst:
            # Remove from old, insert to new
            sorted_infos = sorted(infos, key=lambda x: (id(x['old_parent']) if x['old_parent'] else -1, x['old_index']),
                                  reverse=True)
        else:
            # Remove from new, insert to old
            sorted_infos = sorted(infos, key=lambda x: (id(x['new_parent']) if x['new_parent'] else -1, x['new_index']),
                                  reverse=True)
            sorted_infos = sorted(infos, key=lambda x: (x['new_parent'] or self.tree, x['new_index']), reverse=True)

        for info in sorted_infos:
            item = info['item']
            if src_to_dst:
                # Remove from old
                src_parent = info['old_parent']
                src_index = self._find_current_index(src_parent, item)
                if src_index == -1:
                    continue
                if src_parent is None:
                    self.tree.takeTopLevelItem(src_index)
                else:
                    src_parent.takeChild(src_index)
            else:
                # Remove from new
                dst_parent = info['new_parent']
                dst_index = self._find_current_index(dst_parent, item)
                if dst_index == -1:
                    continue
                if dst_parent is None:
                    self.tree.takeTopLevelItem(dst_index)
                else:
                    dst_parent.takeChild(dst_index)

        if src_to_dst:
            sorted_infos = sorted(infos, key=lambda x: (id(x['new_parent']) if x['new_parent'] else -1, x['new_index']))
            for info in sorted_infos:
                item = info['item']
                dst_parent = info['new_parent']
                dst_index = info['new_index']
                if dst_parent is None:
                    self.tree.insertTopLevelItem(dst_index, item)
                else:
                    dst_parent.insertChild(dst_index, item)
                    dst_parent.setExpanded(True)
        else:
            sorted_infos = sorted(infos, key=lambda x: (id(x['old_parent']) if x['old_parent'] else -1, x['old_index']))
            for info in sorted_infos:
                item = info['item']
                dst_parent = info['old_parent']
                dst_index = info['old_index']
                if dst_parent is None:
                    self.tree.insertTopLevelItem(dst_index, item)
                else:
                    dst_parent.insertChild(dst_index, item)
                    dst_parent.setExpanded(True)
        self.tree.viewport().update()
        self.tree.viewport().update()

    def redo(self):
        self._move(self.move_infos, src_to_dst=True)

    def undo(self):
        self._move(self.move_infos, src_to_dst=False)
        
        
class DuplicateItemsCommand(QUndoCommand):
    def __init__(self, tree: QTreeWidget, items):
        """
        Command to duplicate the given items in the tree.
        Args:
            tree (QTreeWidget): The tree widget.
            items (list[QTreeWidgetItem]): Items to duplicate.
        """
        super().__init__("Duplicate Item(s)")
        self.tree = tree
        self.items = items if isinstance(items, (list, tuple)) else [items]
        self.duplicates = []  # List of (parent, index, new_item)

    def _deep_copy_item(self, item):
        """Recursively deep copy a QTreeWidgetItem and its children."""
        new_item = HierarchyItemModel()
        for col in range(item.columnCount()):
            new_item.setText(col, item.text(col))
            new_item.setData(col, Qt.UserRole, str(uuid.uuid4()))  # Assign new unique ID
        # Copy user data if needed (custom roles)
        for i in range(item.childCount()):
            child_copy = self._deep_copy_item(item.child(i))
            new_item.addChild(child_copy)
        return new_item

    def redo(self):
        self.duplicates.clear()
        for item in self.items:
            parent = item.parent()
            if parent is None:
                parent = self.tree.invisibleRootItem()
            index = parent.indexOfChild(item)
            new_item = self._deep_copy_item(item)
            parent.insertChild(index + 1, new_item)
            self.duplicates.append((parent, index + 1, new_item))
            parent.setExpanded(True)

    def undo(self):
        for parent, index, new_item in self.duplicates:
            # Remove the duplicated item
            idx = parent.indexOfChild(new_item)
            if idx != -1:
                parent.takeChild(idx)