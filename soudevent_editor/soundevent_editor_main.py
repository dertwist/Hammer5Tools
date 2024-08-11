import os.path
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
from soudevent_editor.properties.soundevent_editor_properties_list import soundevent_editor_properties
from soudevent_editor.soundevent_editor_kv3_parser import child_merge,child_key, parse_kv3
import keyvalues3 as kv3

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

        self.popup_menu = PopupMenu(soundevent_editor_properties)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.add_property(name, value))

        self.soundevent_properties_widget = QWidget()
        self.soundevent_properties_layout = QVBoxLayout(self.ui.soundevent_properties)
        self.soundevent_properties_widget.setLayout(self.soundevent_properties_layout)
        self.ui.scrollArea.setWidget(self.soundevent_properties_widget)
        self.ui.scrollArea.setFocusPolicy(Qt.StrongFocus)

        self.ui.soundevents_list.itemClicked.connect(self.on_soundevent_clicked)
        self.populate_soundevent_list()

        self.ui.save_button.clicked.connect(self.save)



    def populate_soundevent_list(self):
        global soundevents_data
        soundevents_data = parse_kv3(os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'soundevents', 'soundevents_addon.vsndevts'))
        for key, _ in soundevents_data.items():
            self.ui.soundevents_list.addItem(key)


    def save(self):
        data = self.get_element_layout_kv3(self.soundevent_properties_layout, {})
        soundevent = self.ui.soundevents_list.currentItem().text()
        data = {soundevent: data}
        print(kv3.write(data, sys.stdout))

        pass
    def get_element_layout_kv3(self, layout, data_out):
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget:
                item = {widget.name: widget.value}
                data_out = child_merge(data_out, item)
                print(item)
        return data_out
    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def on_soundevent_clicked(self, item):
        global soundevents_data
        item_text = item.text()
        if self.soundevent_properties_layout.count() != 0:
            data_out = self.get_element_layout_kv3(self.soundevent_properties_layout, {})
            self.clear_layout(self.soundevent_properties_layout)
            if item_text in soundevents_data:
                details = soundevents_data[item_text]
                for key, value in details.items():
                    value = str(value)
                    self.add_property(key, value)
            del soundevents_data[item_text]
            properties_data = {item_text: data_out}
            soundevents_data = child_merge(soundevents_data, properties_data)
        else:
            self.clear_layout(self.soundevent_properties_layout)
            if item_text in soundevents_data:
                details = soundevents_data[item_text]
                for key, value in details.items():
                    value = str(value)
                    self.add_property(key, value)


    def add_property(self, name, value):
        if name == 'volume':
            property_class = VolumeProperty(name=name, display_name="Volume", value=value, status_bar=self.ui.status_bar,widget_list=self.soundevent_properties_layout)
        elif name == 'pitch':
            property_class = VolumeProperty(name=name, display_name="Pitch", value=value,status_bar=self.ui.status_bar,widget_list=self.soundevent_properties_layout)
        else:
            property_class = LegacyProperty(name=name, value=value, status_bar=self.ui.status_bar, widget_list=self.soundevent_properties_layout)

        self.soundevent_properties_layout.insertWidget(0, property_class)
        self.soundevent_properties_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        name = property_class.name
        self.ui.status_bar.setText(f"Created: {name}")

        # for index in range(self.soundevent_properties_layout.count()):
        #     widget = self.soundevent_properties_layout.itemAt(index).widget()
        #     if isinstance(widget, LegacyProperty):
        #         print(f"Index: {index}, Name: {widget.name}, Value: {widget.value}")

    def keyPressEvent(self, event):
        focus_widget = QApplication.focusWidget()

        if isinstance(focus_widget, QScrollArea) and focus_widget.viewport().underMouse():
            if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                self.popup_menu.show()
                event.accept()
            elif event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
                self.select_all_items()
                event.accept()
            elif event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
                self.paste_action()
                event.accept()

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)

        paste_action = QAction("Paste", self)
        paste_action.triggered.connect(self.paste_action)
        context_menu.addAction(paste_action)
        context_menu.exec_(event.globalPos())

    def paste_action(self):
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()
        clipboard_data = clipboard_text.split(';;')

        if clipboard_data[0] == "hammer5tools:soundeventeditor":
            self.add_property(clipboard_data[1], clipboard_data[2])
        else:
            print("Clipboard data format is not valid.")
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SoundEventEditorMainWidget()
    window.show()
    sys.exit(app.exec())