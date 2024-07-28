import json
from PySide6.QtWidgets import QTreeWidgetItem, QInputDialog, QMenu, QLineEdit, QWidgetAction
from PySide6.QtGui import QCursor
from PySide6.QtCore import Qt

class PresetsManager:
    def __init__(self, tree):
        self.tree = tree
        self.presets = self.load_presets()

    def load_presets(self):
        try:
            with open('soundevent_editor.cfg', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def save_presets(self):
        with open('soundevent_editor.cfg', 'w') as file:
            json.dump(self.presets, file)

    def show_presets_menu(self):
        print("Showing presets menu")  # Debugging statement
        menu = QMenu()
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
        key, ok = QInputDialog.getText(self.tree, "Add Preset", "Enter preset key:")
        if ok and key:
            value, ok = QInputDialog.getText(self.tree, "Add Preset", "Enter preset value:")
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