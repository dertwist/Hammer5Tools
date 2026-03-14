import ast
import uuid
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QUndoCommand
from src.widgets import HierarchyItemModel


class RenameItemCommand(QUndoCommand):
    """Renames a single tree item and optionally runs a callback after each apply."""
    def __init__(self, item: QTreeWidgetItem, old_name: str, new_name: str, on_renamed=None):
        super().__init__(f"Rename '{new_name}'")
        self.item = item
        self.old_name = old_name
        self.new_name = new_name
        self._on_renamed = on_renamed

    def _apply(self, name: str):
        self.item.setText(0, name)
        if self._on_renamed:
            self._on_renamed()

    def redo(self):
        self._apply(self.new_name)

    def undo(self):
        self._apply(self.old_name)


class DuplicateSoundEventsCommand(QUndoCommand):
    """Duplicate selected soundevent tree items with unique names. Uses window's serialize/deserialize."""
    _item_refs = set()

    def __init__(self, window, tree: QTreeWidget, selected_items):
        super().__init__("Duplicate Event(s)")
        self.window = window
        self.tree = tree
        self.items = list(selected_items) if selected_items else []
        self.added = []  # list of (original_item, new_item) for redo-after-undo

    def redo(self):
        if not self.added:
            # First time: create duplicates and insert after each original
            for item in self.items:
                data = self.window.serialization_hierarchy_items_single(item)
                new_items = self.window.deserialize_hierarchy_items(data)
                cur_index = self.tree.indexOfTopLevelItem(item)
                for i, new_item in enumerate(new_items):
                    DuplicateSoundEventsCommand._item_refs.add(new_item)
                    insert_at = cur_index + 1 + i
                    self.tree.insertTopLevelItem(insert_at, new_item)
                    self.added.append((item, new_item))
        else:
            # Redo after undo: re-insert same new items after their originals
            for orig, new_item in self.added:
                idx = self.tree.indexOfTopLevelItem(orig) + 1
                self.tree.insertTopLevelItem(idx, new_item)

    def undo(self):
        for _orig, new_item in reversed(self.added):
            idx = self.tree.indexOfTopLevelItem(new_item)
            if idx != -1:
                self.tree.takeTopLevelItem(idx)

