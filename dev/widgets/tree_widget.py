import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QAbstractItemView
)
from PySide6.QtGui import QUndoStack, QUndoCommand
from PySide6.QtCore import Qt  # Import Qt for enums
# from PySide6.QtCore import Qt, QAbstractItemModel

class AddItemCommand(QUndoCommand):
    _item_refs = set()  # Prevent deletion by keeping references

    def __init__(self, tree, parent_item, text, index=None):
        super().__init__("Add Item")
        self.tree = tree
        self.parent_item = parent_item
        self.text = text
        self.index = index
        self.item = QTreeWidgetItem([text])
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

    def __init__(self, tree, item):
        super().__init__("Remove Item")
        self.tree = tree
        self.item = item
        RemoveItemCommand._item_refs.add(self.item)
        self.parent = item.parent()
        self.index = (
            self.parent.indexOfChild(item)
            if self.parent
            else self.tree.indexOfTopLevelItem(item)
        )

    def redo(self):
        if self.parent:
            self.parent.removeChild(self.item)
        else:
            idx = self.tree.indexOfTopLevelItem(self.item)
            if idx != -1:
                self.tree.takeTopLevelItem(idx)

    def undo(self):
        if self.parent:
            if self.index == -1:
                self.parent.addChild(self.item)
            else:
                self.parent.insertChild(self.index, self.item)
            self.parent.setExpanded(True)
        else:
            if self.index == -1:
                self.tree.addTopLevelItem(self.item)
            else:
                self.tree.insertTopLevelItem(self.index, self.item)

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
            sorted_infos = sorted(infos, key=lambda x: (id(x['old_parent']) if x['old_parent'] else -1, x['old_index']), reverse=True)
        else:
            # Remove from new, insert to old
            sorted_infos = sorted(infos, key=lambda x: (id(x['new_parent']) if x['new_parent'] else -1, x['new_index']), reverse=True)
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




class CustomTreeWidget(QTreeWidget):
    def __init__(self, undo_stack):
        super().__init__()
        self.undo_stack = undo_stack
        self.undo_stack.setUndoLimit(400)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(True)
        self._ignore_next_drop  = False
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
    @staticmethod
    def serialize_tree_structure(input, top_level=False):
        """
        Counts all children and columns for a QTreeWidget or QTreeWidgetItem.
        Args:
            input: QTreeWidget or QTreeWidgetItem
            top_level: If True, only count top-level items (not recursive)
        Returns:
            dict with 'item_count' and 'column_count'
        """
        if hasattr(input, 'columnCount'):
            column_count = input.columnCount()
        else:
            column_count = 1

        def count_items(item):
            count = 1  # count self
            for i in range(item.childCount()):
                count += count_items(item.child(i))
            return count

        if hasattr(input, 'topLevelItemCount'):  # QTreeWidget
            if top_level:
                item_count = input.topLevelItemCount()
            else:
                item_count = 0
                for i in range(input.topLevelItemCount()):
                    item_count += count_items(input.topLevelItem(i))
        elif hasattr(input, 'childCount') and not isinstance(input, CustomTreeWidget):  # QTreeWidgetItem
            if top_level:
                item_count = input.childCount()
            else:
                item_count = count_items(input)
        else:
            raise TypeError("Input must be QTreeWidget or QTreeWidgetItem")

        return {'item_count': item_count, 'column_count': column_count}
        return {'item_count': item_count, 'column_count': column_count}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drag And drop Tree Widget")
        self.resize(600, 400)

        self.undo_stack = QUndoStack(self)

        self.tree = CustomTreeWidget(self.undo_stack)
        self.tree.setHeaderLabel("Tree Items")

        # Add some initial items
        self._add_initial_items()

        add_btn = QPushButton("Add Item")
        remove_btn = QPushButton("Remove Item")
        undo_btn = QPushButton("Undo")
        redo_btn = QPushButton("Redo")

        add_btn.clicked.connect(self.add_item)
        remove_btn.clicked.connect(self.remove_item)
        undo_btn.clicked.connect(self.undo_stack.undo)
        redo_btn.clicked.connect(self.undo_stack.redo)

        layout = QVBoxLayout()
        button_layout = QHBoxLayout()
        button_layout.addWidget(add_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addWidget(undo_btn)
        button_layout.addWidget(redo_btn)
        layout.addLayout(button_layout)
        layout.addWidget(self.tree)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _add_initial_items(self):
        p1 = QTreeWidgetItem(["Parent 1"])
        c1 = QTreeWidgetItem(["Child 1"])
        c2 = QTreeWidgetItem(["Child 2"])
        p1.addChildren([c1, c2])
        p1.setExpanded(True)
        self.tree.addTopLevelItem(p1)

        p2 = QTreeWidgetItem(["Parent 2"])
        self.tree.addTopLevelItem(p2)

    def add_item(self):
        selected = self.tree.currentItem()
        cmd = AddItemCommand(self.tree, selected, "New Item")
        self.undo_stack.push(cmd)

    def remove_item(self):
        selected = self.tree.currentItem()
        if selected:
            cmd = RemoveItemCommand(self.tree, selected)
            self.undo_stack.push(cmd)
            


if __name__ == "__main__":
    app = QApplication(sys.argv)
    from src.styles.qt_global_stylesheet import QT_Stylesheet_global
    app.setStyleSheet(QT_Stylesheet_global)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
