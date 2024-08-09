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


        toolbar = QToolBar()
        self.addToolBar(toolbar)

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