import sys, os
from PySide6.QtWidgets import (
    QApplication, QTreeWidget, QTreeWidgetItem, QMainWindow, QMenu,
    QInputDialog, QMessageBox, QToolBar, QPushButton, QFileDialog, QTextEdit, QVBoxLayout, QWidget, QHeaderView, QStyledItemDelegate, QHBoxLayout, QLabel, QLineEdit, QWidgetAction, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCursor
import json
import keyvalues3 as kv3
from soudevent_editor.toolbar_functions import export_to_file, quick_export_to_file, tree_item_to_dict, convert_children_to_list
from soudevent_editor.data import data, square_brackets_group, data_kv3
from preferences import get_addon_name, get_cs2_path
from soudevent_editor.presets_manager import PresetsManager

class PresetsDialog(QDialog):
    def __init__(self, presets, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Presets")
        self.presets = presets

        self.layout = QVBoxLayout(self)
        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Preset Key", "Preset Value"])
        self.populate_presets_tree(self.presets)

        self.layout.addWidget(self.tree)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout.addWidget(button_box)

    def populate_presets_tree(self, data, parent=None):
        if parent is None:
            parent = self.tree.invisibleRootItem()

        if isinstance(data, dict):
            for key, value in data.items():
                item = QTreeWidgetItem([key])
                parent.addChild(item)
                self.populate_presets_tree(value, item)
        elif isinstance(data, list):
            for value in data:
                list_item = QTreeWidgetItem([""])
                parent.addChild(list_item)
                self.populate_presets_tree(value, list_item)
        else:
            parent.setText(1, str(data))


class SoundEventEditor_Viewport_Window(QMainWindow):
    def __init__(self):
        super().__init__()

        # Get screen resolution
        screen = QApplication.primaryScreen().geometry()
        width, height = screen.width(), screen.height()

        # Set window size to 50% of screen resolution
        self.setGeometry(500, 500, width // 2, height // 2)

        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Key", "Value"])
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_menu)
        self.tree.itemChanged.connect(self.on_item_changed)

        # Enable single selection
        self.tree.setSelectionMode(QTreeWidget.SingleSelection)

        # Enable checkboxes
        self.tree.setSelectionBehavior(QTreeWidget.SelectRows)

        # Set the delegate for padding
        self.tree.setItemDelegateForColumn(1, QStyledItemDelegate())

        # Set the default width of the columns
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Interactive)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)

        # Set the initial width of the columns
        self.tree.header().resizeSection(0, self.width() * 0.3)
        self.tree.header().resizeSection(1, self.width() * 0.3)

        self.debug_window = QTextEdit(self)
        self.debug_window.setReadOnly(True)

        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.tree)
        left_layout.addWidget(self.debug_window)

        left_container = QWidget()
        left_container.setLayout(left_layout)

        main_layout.addWidget(left_container)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        try:
            debug_data_kv3 = kv3.read(r"see_test.txt")
            print(debug_data_kv3.value)
        except:
            pass
        # debug_data_kv3 = kv3.read(data_kv3)


        self.populate_tree(data)

        toolbar = QToolBar()
        self.addToolBar(toolbar)

        export_button = QPushButton("Export to Path")
        export_button.clicked.connect(lambda: export_to_file(self.tree, square_brackets_group, self.update_debug_window))
        toolbar.addWidget(export_button)

        load_button = QPushButton("Load from File")
        load_button.clicked.connect(self.load_file)
        toolbar.addWidget(load_button)

        quick_export_button = QPushButton("Quick Export")
        quick_export_button.clicked.connect(lambda: quick_export_to_file(self.tree, square_brackets_group, self.update_debug_window))
        toolbar.addWidget(quick_export_button)

        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDragDropMode(QTreeWidget.InternalMove)

        self.presets_manager = PresetsManager(self.tree)  # Initialize presets manager

    # ... rest of the class methods ...

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
            print("Ctrl + F pressed")  # Debugging statement
            self.presets_manager.show_presets_menu()
            event.accept()  # Indicate that the event has been handled
        elif event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
            self.select_all_items()
            event.accept()
        else:
            super().keyPressEvent(event)

    def select_all_items(self):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setSelected(True)

    def dropEvent(self, event):
        item = self.tree.currentItem()
        if not item:
            return

        parent = item.parent() or self.tree.invisibleRootItem()
        dropped_item = event.source().currentItem()
        if not dropped_item:
            return

        new_item = QTreeWidgetItem(dropped_item.text(0))
        new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)

        index = self.tree.indexOfTopLevelItem(item)
        if index >= 0:
            parent.insertChild(index, new_item)
        else:
            parent.addChild(new_item)

        event.accept()
        self.update_debug_window()

    def populate_tree(self, data, parent=None):
        if parent is None:
            parent = self.tree.invisibleRootItem()

        if isinstance(data, dict):
            for key, value in data.items():
                item = QTreeWidgetItem([key, ""])
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                parent.addChild(item)
                self.populate_tree(value, item)
        elif isinstance(data, list):
            for value in data:
                if isinstance(value, list):
                    list_item = QTreeWidgetItem(["[ ... ]", ""])
                    list_item.setFlags(list_item.flags() | Qt.ItemIsEditable)
                    parent.addChild(list_item)
                    self.populate_tree(value, list_item)
                else:
                    list_item = QTreeWidgetItem(["", str(value)])
                    list_item.setFlags(list_item.flags() | Qt.ItemIsEditable)
                    parent.addChild(list_item)
        else:
            parent.setText(1, str(data))
            parent.setFlags(parent.flags() | Qt.ItemIsEditable)

    def update_volume_value(self, item, value):
        item.setText(1, f"{value:.2f}")
        self.update_debug_window()

    def on_item_changed(self, item, column):
        self.update_debug_window()

    def open_menu(self, position):
        menu = QMenu()
        move_up_action = menu.addAction("Move Up")
        move_down_action = menu.addAction("Move Down")
        add_action = menu.addAction("Add")
        edit_action = menu.addAction("Edit")
        remove_action = menu.addAction("Remove")
        select_all_action = menu.addAction("Select All")
        invert_selection_action = menu.addAction("Invert Selection")

        move_up_action.triggered.connect(lambda: self.move_item(self.tree.itemAt(position), -1))
        move_down_action.triggered.connect(lambda: self.move_item(self.tree.itemAt(position), 1))
        add_action.triggered.connect(lambda: self.add_item(self.tree.itemAt(position)))
        edit_action.triggered.connect(lambda: self.edit_item(self.tree.itemAt(position)))
        remove_action.triggered.connect(lambda: self.remove_item(self.tree.itemAt(position)))
        select_all_action.triggered.connect(self.select_all_items)
        invert_selection_action.triggered.connect(self.invert_selection)

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def invert_selection(self):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setSelected(not item.isSelected())

    def move_item(self, item, direction):
        if not item:
            return
        parent = item.parent() or self.tree.invisibleRootItem()
        index = parent.indexOfChild(item)
        new_index = index + direction

        if 0 <= new_index < parent.childCount():
            parent.takeChild(index)
            parent.insertChild(new_index, item)
        self.update_debug_window()

    def add_item(self, item):
        key, ok = QInputDialog.getText(self, "Add Item", "Enter key:")
        if ok and key:
            new_item = QTreeWidgetItem([key])
            new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)
            if item:
                item.addChild(new_item)
            else:
                self.tree.addTopLevelItem(new_item)
        self.update_debug_window()

    def edit_item(self, item):
        if item:
            self.tree.editItem(item, 0)
        self.update_debug_window()

    def remove_item(self, item):
        if item:
            parent = item.parent() or self.tree.invisibleRootItem()
            index = parent.indexOfChild(item)
            parent.takeChild(index)
        self.update_debug_window()

    def load_file(self):
        path_to_file = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'soundevents','soundevents_addon.vsndevts')
        print(path_to_file)
        bt_config = kv3.read(path_to_file)

        # Clear the tree before loading new data
        self.tree.clear()

        data = bt_config.value
        self.populate_tree(data)
        print(data)
        self.update_debug_window()

    def update_debug_window(self):
        root = self.tree.invisibleRootItem()
        data = tree_item_to_dict(root)
        data = kv3.write(data, 'debug.kv3')
        with open('debug.kv3', 'r') as file:
            data = file.read()
        self.debug_window.setPlainText(data)
        self.debug_window.setStyleSheet("color: #E3E3E3;")

def main():
    app = QApplication(sys.argv)  # Create an application instance
    main_window = SoundEventEditor_Viewport_Window()  # Create an instance of SoundEventEditor_Viewport_Window
    main_window.show()  # Show the SoundEventEditor_Viewport_Window
    sys.exit(app.exec_())  # Start the event loop


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SoundEventEditor_Viewport_Window()
    window.show()
    sys.exit(app.exec())