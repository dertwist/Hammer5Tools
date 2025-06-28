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

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtGui import QUndoCommand
from src.widgets import HierarchyItemModel
from src.editors.smartprop_editor._common import get_clean_class_name_value, get_ElementID_key
import copy

class GroupElementsCommand(QUndoCommand):
    def __init__(self, tree: QTreeWidget):
        super().__init__("Group Selected Items")
        self.tree = tree
        self.group_element = None
        self.moved_items_info = []  # (item, old_parent, old_index)
        self._selected_order = [item for item in self.tree.selectedItems()]
        # Keep references to all items to prevent deletion
        self._item_refs = list(self._selected_order)

    def redo(self):
        group_data = {'_class': 'CSmartPropElement_Group', 'm_Modifiers': [], 'm_SelectionCriteria': []}
        group_id = get_ElementID_key(group_data)
        self.group_element = HierarchyItemModel(_data=group_data, _name='Group', _class='Group', _id=group_id)
        invisible_root = self.tree.invisibleRootItem()
        self.moved_items_info = []
        # Use the original selection order
        for item in self._selected_order:
            if item is None or item == invisible_root:
                continue
            old_parent = item.parent() or invisible_root
            old_index = old_parent.indexOfChild(item)
            self.moved_items_info.append((item, old_parent, old_index))
        # Remove from parents in reverse order to avoid index shifting
        for item, old_parent, old_index in sorted(self.moved_items_info, key=lambda x: (id(x[1]), x[2]), reverse=True):
            old_parent.takeChild(old_index)
        # Add to group in original order
        for item, _, _ in self.moved_items_info:
            self.group_element.addChild(item)
        invisible_root.addChild(self.group_element)
        self.tree.clearSelection()
        self.group_element.setSelected(True)
        self.tree.scrollToItem(self.group_element)

    def undo(self):
        if self.group_element is None:
            return
        invisible_root = self.tree.invisibleRootItem()
        invisible_root.removeChild(self.group_element)
        # Remove from group in reverse order to avoid index shifting
        for item, _, _ in reversed(self.moved_items_info):
            idx = self.group_element.indexOfChild(item)
            if idx != -1:
                self.group_element.takeChild(idx)
        # Restore to original parents/positions in original order
        for item, old_parent, old_index in self.moved_items_info:
            old_parent.insertChild(old_index, item)
        self.tree.clearSelection()
        for item, _, _ in self.moved_items_info:
            item.setSelected(True)
            self.tree.scrollToItem(item)
        # Keep references alive
        self._item_refs = [item for item, _, _ in self.moved_items_info]


class PasteItemsCommand(QUndoCommand):
    def __init__(self, tree, parent, items):
        super().__init__("Paste Items")
        self.tree = tree
        self.parent = parent
        self.items = items
        self.added = []

    def redo(self):
        for item in self.items:
            self.parent.addChild(item)
            self.parent.setExpanded(True)
            self.added.append(item)
        if self.items:
            self.tree.clearSelection()
            self.items[0].setSelected(True)
            self.tree.scrollToItem(self.items[0])

    def undo(self):
        for item in self.added:
            self.parent.removeChild(item)
        self.added.clear()

class BulkModelImportCommand(QUndoCommand):
    def __init__(self, document, parent_item, items):
        super().__init__("Bulk Model Import")
        self.document = document
        self.tree = document.ui.tree_hierarchy_widget
        self.parent_item = parent_item
        self.items = items
        self.added = []

    def redo(self):
        for item in self.items:
            self.parent_item.addChild(item)
            self.parent_item.setExpanded(True)
            self.added.append(item)
        if self.items:
            self.tree.clearSelection()
            self.items[0].setSelected(True)
            self.tree.scrollToItem(self.items[0])

    def undo(self):
        for item in self.added:
            self.parent_item.removeChild(item)
        self.added.clear()

class NewFromPresetCommand(QUndoCommand):
    def __init__(self, tree, parent, items):
        super().__init__("New From Preset")
        self.tree = tree
        self.parent = parent
        self.items = items
        self.added = []

    def redo(self):
        for item in self.items:
            self.parent.addChild(item)
            self.parent.setExpanded(True)
            self.added.append(item)
        if self.items:
            self.tree.clearSelection()
            self.items[0].setSelected(True)
            self.tree.scrollToItem(self.items[0])

    def undo(self):
        for item in self.added:
            self.parent.removeChild(item)
        self.added.clear()

#End of GroupElementsCommand


