import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QListWidgetItem, QMenu
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction,QCursor
from soudevent_editor.ui_soundevenet_editor_mainwindow import Ui_SoundEvent_Editor_MainWindow
from preferences import get_config_value, get_cs2_path, get_addon_name
from soudevent_editor.soundevent_editor_mini_windows_explorer import SoundEvent_Editor_MiniWindowsExplorer
from soudevent_editor.soundevent_editor_properties_popup import PropertiesPopup

from soudevent_editor.properties.legacy_property import LegacyProperty


class SoundEventEditorMainWidget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_SoundEvent_Editor_MainWindow()
        self.ui.setupUi(self)

        # Set up the custom file system model
        counter_strike_2_path = get_cs2_path()
        addon_name = get_addon_name()
        tree_directory = rf"{counter_strike_2_path}\content\csgo_addons\{addon_name}\sounds"

        # Initialize the mini windows explorer
        self.mini_explorer = SoundEvent_Editor_MiniWindowsExplorer(self.ui.audio_files_explorer, tree_directory)

        # Set up the layout for the audio_files_explorer widget
        self.audio_files_explorer_layout = QVBoxLayout(self.ui.audio_files_explorer)
        self.audio_files_explorer_layout.addWidget(self.mini_explorer.tree)
        self.audio_files_explorer_layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setLayout(self.ui.horizontalLayout)
        self.setCentralWidget(container)

        self.presets_manager = PropertiesPopup()
        self.presets_manager.add_property_signal.connect(self.add_property)

    def create_context_menu(self, item):
        context_menu = QMenu()

        delete_action = QAction("Delete", self)
        duplicate_action = QAction("Duplicate", self)
        help_action = QAction("Help", self)

        delete_action.triggered.connect(lambda: self.delete_item(item))
        duplicate_action.triggered.connect(lambda: self.duplicate_item(item))
        help_action.triggered.connect(lambda: self.show_help(item))

        context_menu.addAction(delete_action)
        context_menu.addAction(duplicate_action)
        context_menu.addAction(help_action)

        return context_menu

    def add_property(self, element):
        legacy_property = LegacyProperty(name=element, value='test')

        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 50))
        self.ui.soundevent_properties.addItem(item)

        self.ui.soundevent_properties.setItemWidget(item, legacy_property)

        context_menu = self.create_context_menu(item)

        legacy_property.setContextMenuPolicy(Qt.ActionsContextMenu)
        legacy_property.customContextMenuRequested.connect(
            lambda pos, item=item: self.show_context_menu(pos, item, context_menu))

    def show_context_menu(self, pos, item, context_menu):
        item_widget = self.ui.soundevent_properties.itemWidget(item)
        item_widget.setContextMenuPolicy(Qt.ActionsContextMenu)
        item_widget.customContextMenuRequested.connect(
            lambda: self.show_context_menu(pos, item, context_menu))

    def delete_item(self, item):
        # Implement the logic to delete the item from the list
        self.ui.soundevent_properties.takeItem(self.ui.soundevent_properties.row(item))

    def duplicate_item(self, item):
        duplicated_item = item.clone()
        self.ui.soundevent_properties.addItem(duplicated_item)

    def show_help(self, item):
        print(f"Help for item: {item.text()}")


    def keyPressEvent(self, event):
        if self.ui.soundevent_properties.hasFocus():  # Check if the focus is on self.ui.soundevent_property
            if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                print("Ctrl + F pressed")  # Debugging statement
                self.presets_manager.show_popup()
                event.accept()  # Indicate that the event has been handled
            elif event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
                self.select_all_items()
                event.accept()
        else:
            super().keyPressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SoundEventEditorMainWidget()
    window.show()
    sys.exit(app.exec())