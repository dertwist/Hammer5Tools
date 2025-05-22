import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QAbstractItemView
)
from PySide6.QtGui import QUndoStack, QUndoCommand
from src.editors.smartprop_editor.commands import AddItemCommand, RemoveItemCommand, MoveItemsCommand, DuplicateItemsCommand

class HierarchyTreeWidget(QTreeWidget):
    def __init__(self, undo_stack):
        super().__init__()
        self.undo_stack = undo_stack
        self.undo_stack.setUndoLimit(400)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(True)
        self._ignore_next_drop = False
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragDropMode(QTreeWidget.InternalMove)

    def dropEvent(self, event):
        if self._ignore_next_drop:
            self._ignore_next_drop = False
            super().dropEvent(event)
            return

        selected_items = self.selectedItems()
        if not selected_items:
            event.ignore()
            return

        # Store old parent and index for each selected item
        old_info = {
            item: (item.parent(), item.parent().indexOfChild(item) if item.parent() else self.indexOfTopLevelItem(item))
            for item in selected_items
        }

        # Perform the default drop handling
        super().dropEvent(event)

        # Collect move infos for items whose position changed
        move_infos = []
        for item in selected_items:
            new_parent = item.parent()
            new_index = new_parent.indexOfChild(item) if new_parent else self.indexOfTopLevelItem(item)
            old_parent, old_index = old_info[item]
            if (old_parent, old_index) != (new_parent, new_index) and new_index != -1:
                move_infos.append({
                    'item': item,
                    'old_parent': old_parent,
                    'old_index': old_index,
                    'new_parent': new_parent,
                    'new_index': new_index
                })

        if move_infos:
            self.undo_stack.push(MoveItemsCommand(self, move_infos))

        event.accept()
    def DeleteSelectedItems(self):
        selected_items = self.selectedItems()
        if not selected_items:
            return
        cmd = RemoveItemCommand(self, selected_items)
        self.undo_stack.push(cmd)
    def AddItem(self, item):
        if not isinstance(item, QTreeWidgetItem):
            raise TypeError("Item must be a QTreeWidgetItem instance.")
        
        if self.currentItem == None:
            parent = self.invisibleRootItem()
        else:
            parent = self.currentItem()
        cmd = AddItemCommand(self, parent, item=item)
        self.undo_stack.push(cmd)
        if self.currentItem() is not None:
            self.setCurrentItem(item)
            self.currentItem().setExpanded(True)
            self.setFocus()
    def DuplicateSelectedItems(self):
        selected_items = self.selectedItems()
        if not selected_items:
            return
        cmd = DuplicateItemsCommand(self, selected_items)
        self.undo_stack.push(cmd)