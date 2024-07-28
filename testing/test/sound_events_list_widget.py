from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt

class SoundEventsListWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SoundEvents List")

        self.layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.itemChanged.connect(self.on_item_changed)
        self.layout.addWidget(self.list_widget)

        self.setLayout(self.layout)

    def update_list(self, data):
        self.list_widget.clear()
        self.populate_list(data)

    def populate_list(self, data):
        if isinstance(data, dict):
            for key in data.keys():
                item = QListWidgetItem(key)
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.list_widget.addItem(item)
        elif isinstance(data, list):
            for value in data:
                if isinstance(value, dict):
                    for key in value.keys():
                        item = QListWidgetItem(key)
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
                        self.list_widget.addItem(item)

    def add_item(self, key):
        item = QListWidgetItem(key)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.list_widget.addItem(item)

    def remove_item(self, item):
        self.list_widget.takeItem(self.list_widget.row(item))

    def rename_item(self, item, new_key):
        item.setText(new_key)

    def duplicate_item(self, item):
        new_item = QListWidgetItem(item.text())
        new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)
        self.list_widget.addItem(new_item)

    def on_item_changed(self, item):
        # Handle the item changed event here
        print(f"Item changed: {item.text()}")