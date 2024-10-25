import sys
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeView, QVBoxLayout, QWidget,
    QTableView, QPlainTextEdit, QSplitter
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QKeySequence, QUndoStack, QUndoCommand
from PySide6.QtCore import Qt, QEvent

class AddItemCommand(QUndoCommand):
    def __init__(self, item_data, model, parent=None):
        super().__init__()
        self.item_data = item_data
        self.model = model
        self.parent = parent
        self.item = None
        self.setText(f"Add item: {item_data['text']}")

    def redo(self):
        if not self.item:
            self.item = QStandardItem(self.item_data["text"])
            for child_data in self.item_data.get("children", []):
                self.add_item_from_data(child_data, self.item)

        if self.parent is not None:
            self.parent.appendRow(self.item)
        else:
            self.model.appendRow(self.item)

    def undo(self):
        if self.parent is not None:
            self.parent.removeRow(self.item.row())
        else:
            self.model.removeRow(self.item.row())

    def add_item_from_data(self, data, parent):
        """ Recursively add items from JSON data """
        item = QStandardItem(data["text"])
        parent.appendRow([item])
        for child_data in data.get("children", []):
            self.add_item_from_data(child_data, item)