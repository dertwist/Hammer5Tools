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
from PySide6.QtWidgets import QSpacerItem, QSizePolicy

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

        self.properties_manager = PropertiesPopup()
        self.properties_manager.add_property_signal.connect(lambda name, value: self.add_property(name, value))

        self.soundevent_properties_widget = QWidget()
        self.soundevent_properties_layout = QVBoxLayout(self.ui.soundevent_properties)
        self.soundevent_properties_widget.setLayout(self.soundevent_properties_layout)
        self.ui.scrollArea.setWidget(self.soundevent_properties_widget)

    def add_property(self, name, value):
        legacy_property = LegacyProperty(name=name, value=value, status_bar=self.ui.status_bar,widget_list=self.soundevent_properties_layout)
        item = QListWidgetItem()
        item.setText(name)  # Set the text for the item as the 'name' parameter
        item.setSizeHint(QSize(0, 50))

        # Assuming self.ui.soundevent_properties is a QVBoxLayout
        # Insert the legacy_property at the beginning of the layout to add it on top
        self.soundevent_properties_layout.insertWidget(0, legacy_property)

        # Add a vertical spacer at the end of the layout to keep it at the bottom
        self.soundevent_properties_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Extracting name and value for setting variables
        property_name = legacy_property.name
        property_value = legacy_property.value

        # Example usage of the extracted variables
        print(f"Property Name: {property_name}")
        print(f"Property Value: {property_value}")

        # Print indexes, names, and values for all elements in the list
        for index in range(self.soundevent_properties_layout.count()):
            widget = self.soundevent_properties_layout.itemAt(index).widget()
            if isinstance(widget, LegacyProperty):
                print(f"Index: {index}, Name: {widget.name}, Value: {widget.value}")

    def delete_item(self, item):
        # Implement the logic to delete the item from the list
        self.ui.soundevent_properties.takeItem(self.ui.soundevent_properties.row(item))

    def duplicate_item(self, item):
        duplicated_item = item.clone()
        self.ui.soundevent_properties.addItem(duplicated_item)

    def show_help(self, item):
        print(f"Help for item: {item.text()}")


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
            print("Ctrl + F pressed")  # Debugging statement
            self.properties_manager.show_popup()
            event.accept()  # Indicate that the event has been handled
        elif event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
            self.select_all_items()
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SoundEventEditorMainWidget()
    window.show()
    sys.exit(app.exec())