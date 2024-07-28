import sys
from PySide6.QtWidgets import (
    QApplication, QTreeWidget, QTreeWidgetItem, QMainWindow, QMenu,
    QInputDialog, QMessageBox, QToolBar, QPushButton, QFileDialog, QTextEdit, QVBoxLayout, QWidget, QHeaderView, QStyledItemDelegate, QHBoxLayout, QSlider, QLabel, QLineEdit, QWidgetAction, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCursor
import json
import keyvalues3 as kv3
from toolbar_functions import export_to_file, quick_export_to_file, tree_item_to_dict, convert_children_to_list
from data import data, square_brackets_group

class VolumeSliderWidget(QWidget):
    valueChanged = Signal(float)  # Signal to emit when the slider value changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(60, 0, 0, 0)  # Set left margin to 60 pixels
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.layout.addWidget(self.slider)
        self.slider.valueChanged.connect(self.emit_value_changed)

    def emit_value_changed(self, value):
        float_value = value / 100.0  # Convert back to float
        self.valueChanged.emit(float_value)

class PresetsDialog(QDialog):
    def __init__(self, presets, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Presets")
        self.presets = presets

        self.layout = QVBoxLayout(self)
        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Preset Key", "Preset Value"])
        self.populate_presets_tree()

        self.layout.addWidget(self.tree)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout.addWidget(button_box)

    def populate_presets_tree(self):
        self.tree.clear()
        for key, value in self.presets.items():
            item = QTreeWidgetItem([key, value])
            self.tree.addTopLevelItem(item)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SoundEvent Editor alpha 0.4")
        self.setFocusPolicy(Qt.StrongFocus)

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

        self.presets = self.load_presets()  # Initialize presets

    # ... rest of the class methods ...

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
            print("Ctrl + F pressed")  # Debugging statement
            self.show_presets_menu()
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

    def show_presets_menu(self):
        print("Showing presets menu")  # Debugging statement
        menu = QMenu(self)
        menu.setWindowFlags(Qt.Popup)  # Set the menu to be a popup

        search_bar = QLineEdit(menu)
        search_bar.setPlaceholderText("Search presets...")
        search_bar.textChanged.connect(lambda text: self.filter_presets(menu, text))
        search_action = QWidgetAction(menu)
        search_action.setDefaultWidget(search_bar)
        menu.addAction(search_action)

        self.populate_presets_menu(menu)

        add_preset_action = menu.addAction("Add Preset")
        add_preset_action.triggered.connect(self.add_preset)

        cursor_pos = QCursor.pos()
        print(f"Cursor position: {cursor_pos}")  # Debugging statement
        menu.exec(cursor_pos)

    def filter_presets(self, menu, text):
        for action in menu.actions():
            if isinstance(action, QWidgetAction):
                continue
            action.setVisible(text.lower() in action.text().lower())

    def populate_presets_menu(self, menu):
        for key, value in self.presets.items():
            action = menu.addAction(f"{key}: {value}")
            action.triggered.connect(lambda checked, k=key, v=value: self.apply_preset(k, v))

    def add_preset(self):
        key, ok = QInputDialog.getText(self, "Add Preset", "Enter preset key:")
        if ok and key:
            value, ok = QInputDialog.getText(self, "Add Preset", "Enter preset value:")
            if ok and value:
                self.presets[key] = value
                self.save_presets()

                # Add the new preset to the tree
                new_item = QTreeWidgetItem([key, value])
                new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)

                selected_item = self.tree.currentItem()
                if selected_item:
                    selected_item.addChild(new_item)
                else:
                    self.tree.addTopLevelItem(new_item)

    def apply_preset(self, key, value):
        print(f"Applying preset: {key} = {value}")  # Debugging statement
        new_item = QTreeWidgetItem([key, value])
        new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)

        selected_item = self.tree.currentItem()
        if selected_item:
            selected_item.addChild(new_item)
        else:
            self.tree.addTopLevelItem(new_item)

        self.update_debug_window()

    def load_presets(self):
        try:
            with open('soundevent_editor.cfg', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def save_presets(self):
        with open('soundevent_editor.cfg', 'w') as file:
            json.dump(self.presets, file)

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
                if key in square_brackets_group and isinstance(value, list):
                    item = QTreeWidgetItem([key])
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    parent.addChild(item)
                    for child_data in value:
                        self.populate_tree(child_data, item)
                else:
                    item = QTreeWidgetItem([key])
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    parent.addChild(item)
                    self.populate_tree(value, item)
        elif isinstance(data, list):
            for value in data:
                self.populate_tree(value, parent)
        else:
            if parent.text(0) == "volume":
                volume_widget = VolumeSliderWidget()
                volume_widget.slider.setValue(int(float(data) * 100))  # Convert float to int for slider
                volume_widget.valueChanged.connect(lambda value, item=parent: self.update_volume_value(item, value))
                self.tree.setItemWidget(parent, 1, volume_widget)
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
            if key == "volume":
                volume_widget = VolumeSliderWidget()
                volume_widget.valueChanged.connect(lambda value, item=new_item: self.update_volume_value(item, value))
                self.tree.setItemWidget(new_item, 1, volume_widget)
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
        bt_config = kv3.read(r"talence.vsndevts")

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())