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

