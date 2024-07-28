import sys
import keyvalues3 as kv3
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout,
                               QWidget, QPushButton, QFileDialog,
                               QMessageBox, QTreeWidget, QTreeWidgetItem, QHBoxLayout, QLineEdit)
from PySide6.QtGui import QFont


class KV3Editor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KV3 Editor")
        self.setGeometry(300, 300, 800, 600)

        self.tree_widget = QTreeWidget(self)
        self.tree_widget.setHeaderLabels(["Key", "Value"])
        self.tree_widget.setFont(QFont("Courier", 10))

        self.open_button = QPushButton("Open", self)
        self.open_button.clicked.connect(self.open_file_dialog)

        self.move_up_button = QPushButton("Move Up", self)
        self.move_up_button.clicked.connect(self.move_item_up)

        self.move_down_button = QPushButton("Move Down", self)
        self.move_down_button.clicked.connect(self.move_item_down)

        self.delete_button = QPushButton("Delete", self)
        self.delete_button.clicked.connect(self.delete_item)

        self.add_button = QPushButton("Add", self)
        self.add_button.clicked.connect(self.add_item)

        self.export_button = QPushButton("Export", self)
        self.export_button.clicked.connect(self.export_kv3)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.move_up_button)
        button_layout.addWidget(self.move_down_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.export_button)

        layout = QVBoxLayout()
        layout.addWidget(self.tree_widget)
        layout.addLayout(button_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Automatically open test2.kv3 file
        self.open_file("D:/CG/Projects/Other/Hammer5Tools/kv3_parcer/soundevents_addon.vsndevts")

    def open_file_dialog(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open KV3 File", "", "KV3 Files (*.vsndevts);;Smart props (*.vsmart);;text (*.txt);;All Files (*)",
                                                   options=options)
        if file_name:
            self.open_file(file_name)

    def open_file(self, file_name):
        if file_name:
            try:
                kv3_data = kv3.read(file_name)
                self.populate_tree(kv3_data.value)
                self.current_kv3_data = kv3_data  # Store the original KV3 data object
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file: {e}")

    def print_tree_structure(self, kv3_data, level=0):
        indent = "  " * level
        if isinstance(kv3_data, dict):
            for key, value in kv3_data.items():
                if isinstance(value, (dict, list)):
                    print(f"{indent}{key}:")
                    self.print_tree_structure(value, level + 1)
                else:
                    print(f"{indent}{key}: {value}")
        elif isinstance(kv3_data, list):
            for index, item in enumerate(kv3_data):
                print(f"{indent}[{index}]:")
                self.print_tree_structure(item, level + 1)
        else:
            print(f"{indent}{kv3_data}")

    def populate_tree(self, kv3_data, parent=None):
        if parent is None:
            self.tree_widget.clear()
            parent = self.tree_widget.invisibleRootItem()

        self.add_items_to_tree(parent, kv3_data)
        self.print_tree_structure(kv3_data)

    def add_items_to_tree(self, parent, kv3_data):
        if isinstance(kv3_data, dict):
            for key, value in kv3_data.items():
                if isinstance(value, dict):
                    item = QTreeWidgetItem([key])
                    parent.addChild(item)
                    self.add_items_to_tree(item, value)
                elif isinstance(value, list):
                    item = QTreeWidgetItem([key, "[...]"])
                    parent.addChild(item)
                    self.add_items_to_tree(item, value)
                else:
                    item = QTreeWidgetItem([key, str(value)])
                    parent.addChild(item)
        elif isinstance(kv3_data, list):
            for index, value in enumerate(kv3_data):
                if isinstance(value, (dict, list)):
                    item = QTreeWidgetItem([f"[{index}]", "[...]"])
                    parent.addChild(item)
                    self.add_items_to_tree(item, value)
                else:
                    item = QTreeWidgetItem([f"[{index}]", str(value)])
                    parent.addChild(item)

    def construct_kv3(self, parent=None):
        if parent is None:
            parent = self.tree_widget.invisibleRootItem()
        kv3_data = {}
        for i in range(parent.childCount()):
            child = parent.child(i)
            key = child.text(0)
            if child.childCount() > 0:
                kv3_data[key] = self.construct_kv3(child)
            else:
                value = child.text(1)
                kv3_data[key] = value
        return kv3_data

    def move_item_up(self):
        selected_item = self.tree_widget.currentItem()
        if not selected_item:
            return

        parent = selected_item.parent()
        if parent is None:
            parent = self.tree_widget.invisibleRootItem()

        index = parent.indexOfChild(selected_item)
        if index > 0:
            parent.takeChild(index)
            parent.insertChild(index - 1, selected_item)
            self.tree_widget.setCurrentItem(selected_item)

    def move_item_down(self):
        selected_item = self.tree_widget.currentItem()
        if not selected_item:
            return

        parent = selected_item.parent()
        if parent is None:
            parent = self.tree_widget.invisibleRootItem()

        index = parent.indexOfChild(selected_item)
        if index < parent.childCount() - 1:
            parent.takeChild(index)
            parent.insertChild(index + 1, selected_item)
            self.tree_widget.setCurrentItem(selected_item)

    def delete_item(self):
        selected_item = self.tree_widget.currentItem()
        if not selected_item:
            return

        parent = selected_item.parent()
        if parent is None:
            parent = self.tree_widget.invisibleRootItem()

        index = parent.indexOfChild(selected_item)
        parent.takeChild(index)

    def add_item(self):
        selected_item = self.tree_widget.currentItem()
        if not selected_item:
            selected_item = self.tree_widget.invisibleRootItem()

        key = "NewKey"
        value = "NewValue"
        new_item = QTreeWidgetItem([key, value])
        selected_item.addChild(new_item)
        self.tree_widget.setCurrentItem(new_item)
        self.tree_widget.editItem(new_item, 0)  # Edit key column

    def export_kv3(self):
        kv3_data = self.construct_kv3()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save KV3 File", "", "KV3 Files (*.vsndevts);;All Files (*)")
        if file_name:
            try:
                kv3_obj = kv3.KV3(data=kv3_data, encoding=kv3.Encoding('text'), format=kv3.Format('generic'))
                kv3.write(kv3_obj, file_name)
                QMessageBox.information(self, "Success", "File saved successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = KV3Editor()
    editor.show()
    sys.exit(app.exec())
