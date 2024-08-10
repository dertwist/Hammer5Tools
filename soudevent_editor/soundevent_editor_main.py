import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QListWidgetItem, QMenu, QScrollArea
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction,QCursor
from soudevent_editor.ui_soundevenet_editor_mainwindow import Ui_SoundEvent_Editor_MainWindow
from preferences import get_config_value, get_cs2_path, get_addon_name
from soudevent_editor.soundevent_editor_mini_windows_explorer import SoundEvent_Editor_MiniWindowsExplorer
# from soudevent_editor.soundevent_editor_properties_popup import PropertiesPopup
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
from popup_menu.popup_menu_main import PopupMenu

from soudevent_editor.properties.legacy_property import LegacyProperty
from soudevent_editor.properties.volume_property import  VolumeProperty


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

        self.popup_menu = PopupMenu()
        self.popup_menu.add_property_signal.connect(lambda name, value: self.add_property(name, value))

        self.soundevent_properties_widget = QWidget()
        self.soundevent_properties_layout = QVBoxLayout(self.ui.soundevent_properties)
        self.soundevent_properties_widget.setLayout(self.soundevent_properties_layout)
        self.ui.scrollArea.setWidget(self.soundevent_properties_widget)

    def add_property(self, name, value):
        if name == 'volume':
            property_class = VolumeProperty(name=name, value=value, status_bar=self.ui.status_bar,widget_list=self.soundevent_properties_layout)
        else:
            property_class = LegacyProperty(name=name, value=value, status_bar=self.ui.status_bar, widget_list=self.soundevent_properties_layout)

        self.soundevent_properties_layout.insertWidget(0, property_class)
        self.soundevent_properties_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        name = property_class.name
        self.ui.status_bar.setText(f"Created: {name}")

        # Print indexes, names, and values for all elements in the list
        for index in range(self.soundevent_properties_layout.count()):
            widget = self.soundevent_properties_layout.itemAt(index).widget()
            if isinstance(widget, LegacyProperty):
                print(f"Index: {index}, Name: {widget.name}, Value: {widget.value}")

    def keyPressEvent(self, event):
        focus_widget = QApplication.focusWidget()

        if isinstance(focus_widget, QScrollArea) and focus_widget.viewport().underMouse():
            if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                self.popup_menu.show()
                event.accept()
            elif event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
                self.select_all_items()
                event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SoundEventEditorMainWidget()
    window.show()
    sys.exit(app.exec())