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
            _class='Group',
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



#End of GroupElementsCommand


