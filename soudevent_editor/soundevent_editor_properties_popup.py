import json
from PySide6.QtWidgets import QTreeWidgetItem, QInputDialog, QMenu, QLineEdit, QWidgetAction
from PySide6.QtGui import QCursor
from PySide6.QtCore import Qt
from soudevent_editor.properties.soundevent_editor_properties_list import soundevent_editor_properties
from PySide6.QtCore import QObject, Signal


class PropertiesPopup(QObject):
    # Define a custom signal with key and value as parameters
    add_property_signal = Signal(str, str)

    def __init__(self):
        super().__init__()
        pass
    def show_popup(self):
        menu = QMenu()
        menu.setWindowFlags(Qt.Popup)

        menu.setFixedWidth(240)

        search_bar = QLineEdit(menu)
        search_bar.setPlaceholderText("Search properties...")

        # Set stylesheet to remove top, right, and left borders
        search_bar.setStyleSheet("border-top: 0px; border-right: 0px; border-left: 0px;")

        search_bar.textChanged.connect(lambda text: self.filter_presets(menu, text))
        search_action = QWidgetAction(menu)
        search_action.setDefaultWidget(search_bar)
        menu.addAction(search_action)

        self.populate_popup(menu)

        cursor_pos = QCursor.pos()
        print(f"Cursor position: {cursor_pos}")  # Debugging statement
        menu.exec(cursor_pos)

    def filter_presets(self, menu, text):
        for action in menu.actions():
            if isinstance(action, QWidgetAction):
                continue
            action.setVisible(text.lower() in action.text().lower())

    def populate_popup(self, menu):
        for item in soundevent_editor_properties:
            for key, value in item.items():
                action = menu.addAction(f"{key}")
                action.triggered.connect(lambda checked, k=key, v=value: self.add_property(k, v))

    def add_property(self, key, value):
        print(f"Applying preset: {key} = {value}")
        self.add_property_signal.emit(key, value)

