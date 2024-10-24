import sys
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeView, QVBoxLayout, QWidget,
    QTableView, QPlainTextEdit, QSplitter
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QKeySequence, QKeyEvent
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Tree, Table, and Plain Text Copy-Paste Example")

        # Set up the main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Use a splitter to hold multiple widgets
        splitter = QSplitter()
        self.layout.addWidget(splitter)

        # Set up the TreeView
        self.tree_view = QTreeView()
        splitter.addWidget(self.tree_view)

        # Set up the TableView
        self.table_view = QTableView()
        splitter.addWidget(self.table_view)

        # Set up the PlainTextEdit
        self.plain_text_edit = QPlainTextEdit()
        splitter.addWidget(self.plain_text_edit)

        # Set up the model for the TreeView and TableView
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(['Tree Items'])
        self.tree_view.setModel(self.tree_model)

        self.table_model = QStandardItemModel(4, 2)  # Example table with 4 rows, 2 columns
        self.table_model.setHorizontalHeaderLabels(['Column 1', 'Column 2'])
        self.table_view.setModel(self.table_model)

        # Add some default items to Tree and Table
        self.add_sample_tree_items()
        self.add_sample_table_items()

        # Make items editable
        self.tree_view.setEditTriggers(QTreeView.DoubleClicked | QTreeView.EditKeyPressed)
        self.table_view.setEditTriggers(QTableView.DoubleClicked | QTableView.EditKeyPressed)

        # Initialize clipboard data
        self.clipboard_data = None

        # Install an event filter to handle Ctrl+C and Ctrl+V in the tree view
        self.tree_view.installEventFilter(self)

    def add_sample_tree_items(self):
        parent1 = QStandardItem("Parent 1")
        child1 = QStandardItem("Child 1.1")
        child2 = QStandardItem("Child 1.2")
        parent1.appendRow([child1])
        parent1.appendRow([child2])

        parent2 = QStandardItem("Parent 2")
        child3 = QStandardItem("Child 2.1")
        parent2.appendRow([child3])

        self.tree_model.appendRow([parent1])
        self.tree_model.appendRow([parent2])

    def add_sample_table_items(self):
        for row in range(4):
            for col in range(2):
                item = QStandardItem(f"Item {row + 1},{col + 1}")
                self.table_model.setItem(row, col, item)

    def eventFilter(self, source, event):
        """Handle keyboard events for the tree view."""
        if event.type() == QKeyEvent.KeyPress and source == self.tree_view:
            if event.matches(QKeySequence.Copy):
                self.copy_tree_items()
                return True
            elif event.matches(QKeySequence.Paste):
                self.paste_tree_items()
                return True
        return super().eventFilter(source, event)

    # Copy-paste for the TreeView
    def copy_tree_items(self):
        selected = self.tree_view.selectedIndexes()

        if not selected:
            return

        # Gather the selected items in JSON format
        item_data = []
        for index in selected:
            item = self.tree_model.itemFromIndex(index)
            item_data.append(self.collect_item_data(item))

        # Store the data in JSON format for later pasting
        self.clipboard_data = json.dumps(item_data)
        print("Copied from tree:", self.clipboard_data)

    def collect_item_data(self, item):
        """ Recursively collect item data into a dictionary """
        data = {"text": item.text(), "children": []}
        for row in range(item.rowCount()):
            child_item = item.child(row)
            data["children"].append(self.collect_item_data(child_item))
        return data

    def paste_tree_items(self):
        if not self.clipboard_data:
            return

        # Load the JSON data from the clipboard
        item_data = json.loads(self.clipboard_data)

        # Paste each item and its children
        for data in item_data:
            self.add_item_from_data(data, self.tree_model)

    def add_item_from_data(self, data, parent):
        """ Recursively add items from JSON data """
        item = QStandardItem(data["text"])
        parent.appendRow([item])

        # Add any children
        for child_data in data["children"]:
            self.add_item_from_data(child_data, item)

    # Copy-paste for the TableView
    def copy_table_items(self):
        selected = self.table_view.selectedIndexes()

        if not selected:
            return

        # Gather the selected table cells in JSON format
        table_data = []
        for index in selected:
            item = self.table_model.itemFromIndex(index)
            table_data.append({"row": index.row(), "col": index.column(), "text": item.text()})

        # Store the table data in JSON format for later pasting
        self.clipboard_data = json.dumps(table_data)
        print("Copied from table:", self.clipboard_data)

    def paste_table_items(self):
        if not self.clipboard_data:
            return

        # Load the JSON data from the clipboard
        table_data = json.loads(self.clipboard_data)

        # Paste the table items back into the model
        for data in table_data:
            item = QStandardItem(data["text"])
            self.table_model.setItem(data["row"], data["col"], item)

    # Copy-paste for the PlainTextEdit
    def copy_plain_text(self):
        text = self.plain_text_edit.toPlainText()

        if text:
            # Store the text in JSON format for consistency
            self.clipboard_data = json.dumps({"text": text})
            print("Copied from plain text:", self.clipboard_data)

    def paste_plain_text(self):
        if not self.clipboard_data:
            return

        # Load the JSON data from the clipboard
        data = json.loads(self.clipboard_data)

        if "text" in data:
            self.plain_text_edit.setPlainText(data["text"])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
