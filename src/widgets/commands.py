import uuid
from PySide6.QtCore import Qt
from src.widgets import HierarchyItemModel
from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem
)
from PySide6.QtGui import QUndoCommand


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
        for item, parent in sorted(zip(self.items, self.parents), key=lambda x: (id(x[1]) if x[1] else -1),
                                   reverse=True):
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
    def __init__(self, tree: QTreeWidget, items, ElementIDGenerator=None):
        super().__init__("Duplicate Item(s)")
        self.tree = tree
        self.items = items if isinstance(items, (list, tuple)) else [items]
        self.duplicates = []  # List of (parent, index, new_item)
        self.id_generator = ElementIDGenerator

    def _deep_copy_item(self, item):
        new_item = HierarchyItemModel()
        for col in range(item.columnCount()):
            if col != 3:
                new_item.setText(col, item.text(col))
            data = item.data(col, Qt.UserRole)
            if self.id_generator and isinstance(data, dict):
                data = self.id_generator.update_value(data.copy(), force=True)
                new_item.setText(3, str(data.get("m_nElementID", "")))
            elif data is not None:
                data = str(uuid.uuid4())
            new_item.setData(col, Qt.UserRole, data)
        for i in range(item.childCount()):
            child_copy = self._deep_copy_item(item.child(i))
            new_item.addChild(child_copy)
        return new_item

    def redo(self):
        if not self.duplicates:
            # First time: create and insert new items
            for item in self.items:
                parent = item.parent() or self.tree.invisibleRootItem()
                index = parent.indexOfChild(item)
                new_item = self._deep_copy_item(item)
                parent.insertChild(index + 1, new_item)
                self.duplicates.append((parent, index + 1, new_item))
                parent.setExpanded(True)
        else:
            # Redo: re-insert the same items
            for parent, index, new_item in self.duplicates:
                parent.insertChild(index, new_item)
                parent.setExpanded(True)

    def undo(self):
        for parent, index, new_item in self.duplicates:
            idx = parent.indexOfChild(new_item)
            if idx != -1:
                parent.takeChild(idx)