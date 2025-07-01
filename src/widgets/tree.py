import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QAbstractItemView
)
from PySide6.QtGui import QUndoStack, QUndoCommand, QMouseEvent
from PySide6.QtCore import Qt
try:
    from .commands import AddItemCommand, RemoveItemCommand, MoveItemsCommand, DuplicateItemsCommand, SelectItemsCommand
except:
    from commands import AddItemCommand, RemoveItemCommand, MoveItemsCommand, DuplicateItemsCommand, SelectItemsCommand

class HierarchyTreeWidget(QTreeWidget):
    def __init__(self, undo_stack, list_mode=False):
        """
        :param undo_stack:
        :param list_mode:
        Means that tree widget will not have child elements, so it will works the same as the widget list. Drag and drop actions will just move items up and down, but not change parent of items
        """
        super().__init__()
        self.undo_stack = undo_stack
        self.undo_stack.setUndoLimit(400)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(True)
        self._ignore_next_drop = False
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragDropMode(QTreeWidget.InternalMove)
        self.list_mode = list_mode

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

        # In list mode, ensure all items are top-level after drop
        if self.list_mode:
            for item in selected_items:
                if item.parent() is not None:
                    item.parent().removeChild(item)
                    self.addTopLevelItem(item)

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
        
        if self.list_mode:
            parent = self.invisibleRootItem()
        else:
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
    def DuplicateSelectedItems(self, ElementIDGenerator=None):
        selected_items = self.selectedItems()
        if not selected_items:
            return
        cmd = DuplicateItemsCommand(self, selected_items, ElementIDGenerator)
        self.undo_stack.push(cmd)

    def setSelectedItemsWithUndo(self, items):
        """Set selected items with undo support"""
        old_selected = self.selectedItems()
        # Only create command if selection actually changes
        if set(old_selected) != set(items):
            cmd = SelectItemsCommand(self, old_selected, items)
            self.undo_stack.push(cmd)
    def mousePressEvent(self, event: QMouseEvent):
        item = self.itemAt(event.pos())
        if item is None and event.button() == Qt.LeftButton:
            self.clearSelection()
            self.setCurrentItem(None)
        super().mousePressEvent(event)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTreeWidgetItem, QPushButton
    from PySide6.QtGui import QUndoStack
    import sys

    class Winds(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("HierarchyTreeWidget Test")
            self.resize(400, 300)
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)

            self.undo_stack = QUndoStack()
            self.tree = HierarchyTreeWidget(self.undo_stack, list_mode=True)
            self.tree.setHeaderLabels(["Name"])
            self.tree.setRootIsDecorated(False)  # Hide root

            # Add children to invisible root
            child1 = QTreeWidgetItem(["Child 1"])
            child2 = QTreeWidgetItem(["Child 2"])
            self.tree.addTopLevelItem(child1)
            self.tree.addTopLevelItem(child2)

            layout.addWidget(self.tree)

            # Shortcuts
            from PySide6.QtGui import QShortcut, QKeySequence
            QShortcut(QKeySequence("Delete"), self, activated=self.tree.DeleteSelectedItems)
            QShortcut(QKeySequence("Ctrl+D"), self, activated=self.tree.DuplicateSelectedItems)
            QShortcut(QKeySequence("Ctrl+N"), self, activated=self.add_item_shortcut)
            QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.undo_stack.undo)
            QShortcut(QKeySequence("Ctrl+Shift+Z"), self, activated=self.undo_stack.redo)


        def add_item_shortcut(self):
            item = QTreeWidgetItem(["New Item"])
            self.tree.AddItem(item)

    app = QApplication(sys.argv)
    win = Winds()
    win.show()
    sys.exit(app.exec())