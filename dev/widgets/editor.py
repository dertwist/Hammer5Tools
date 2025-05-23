import sys
import json
from dataclasses import dataclass, field, asdict
from typing import Any, List, Optional
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QVBoxLayout, QHBoxLayout, QWidget, QMessageBox
)
from PySide6.QtCore import Qt

@dataclass
class JsonElement:
    name: str
    id: str
    class_: str
    data: Any
    children: List["JsonElement"] = field(default_factory=list)

    @staticmethod
    def from_dict(d: dict) -> "JsonElement":
        return JsonElement(
            name=d.get("name", ""),
            id=d.get("id", ""),
            class_=d.get("class", ""),
            data=d.get("data", {}),
            children=[JsonElement.from_dict(child) for child in d.get("children", [])]
        )

    def to_dict(self) -> dict:
        result = {
            "name": self.name,
            "id": self.id,
            "class": self.class_,
            "data": self.data
        }
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
        return result

class JsonEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JSON Editor")
        self.setGeometry(100, 100, 800, 600)

        # Sample JSON data as dataclass
        self.json_elements = [
            JsonElement(
                name="Item 1",
                id="001",
                class_="TypeA",
                data={"value": 42, "desc": "First item"}
            ),
            JsonElement(
                name="Item 2",
                id="002",
                class_="TypeB",
                data=["array", "of", "values"],
                children=[
                    JsonElement(
                        name="Subitem 2.1",
                        id="002.1",
                        class_="TypeC",
                        data={"nested": True}
                    )
                ]
            )
        ]

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "ID", "Class"])
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 100)
        layout.addWidget(self.tree, 1)

        # Data editor
        self.data_editor = QTextEdit()
        self.data_editor.setPlaceholderText("Select an item to edit its data")
        self.data_editor.textChanged.connect(self.on_data_changed)
        layout.addWidget(self.data_editor, 1)

        # Populate tree
        self.populate_tree(self.json_elements, self.tree.invisibleRootItem())

        # Connect selection change
        self.tree.itemSelectionChanged.connect(self.on_item_selected)

    def populate_tree(self, elements: List[JsonElement], parent_item):
        """Populate the tree widget with JsonElement items."""
        for elem in elements:
            item = QTreeWidgetItem(parent_item)
            item.setText(0, elem.name)
            item.setText(1, elem.id)
            item.setText(2, elem.class_)
            # Store data in Qt.UserRole
            item.setData(0, Qt.UserRole, json.dumps(elem.data))
            # Store reference to dataclass for saving
            item.setData(1, Qt.UserRole, elem)
            # Handle children recursively
            if elem.children:
                self.populate_tree(elem.children, item)

    def on_item_selected(self):
        """Load selected item's data into the editor."""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            self.data_editor.setPlainText("")
            self.data_editor.setEnabled(False)
            return
        item = selected_items[0]
        data_str = item.data(0, Qt.UserRole)
        self.data_editor.setEnabled(True)
        self.data_editor.setPlainText(data_str)

    def on_data_changed(self):
        """Save edited data back to the selected item and dataclass."""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return
        item = selected_items[0]
        data_text = self.data_editor.toPlainText()
        try:
            # Validate JSON
            parsed = json.loads(data_text)
            item.setData(0, Qt.UserRole, data_text)
            # Update dataclass as well
            elem: JsonElement = item.data(1, Qt.UserRole)
            elem.data = parsed
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Invalid JSON", "The entered data is not valid JSON.")

    def save_json(self):
        """Save the tree back to JSON using dataclasses."""
        return {"items": [elem.to_dict() for elem in self.json_elements]}

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = JsonEditor()
    editor.show()
    sys.exit(app.exec())