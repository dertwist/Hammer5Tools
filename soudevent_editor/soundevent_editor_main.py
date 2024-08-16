import os.path
import sys
import time

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QListWidgetItem, QMenu, QScrollArea
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction,QCursor
from soudevent_editor.ui_soundevenet_editor_mainwindow import Ui_SoundEvent_Editor_MainWindow
from preferences import get_config_value, get_cs2_path, get_addon_name
from soudevent_editor.soundevent_editor_mini_windows_explorer import SoundEvent_Editor_MiniWindowsExplorer
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QListWidgetItem, QMenu, QScrollArea, QInputDialog
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
from PySide6.QtWidgets import QProgressBar
from popup_menu.popup_menu_main import PopupMenu

from soudevent_editor.properties.soundevent_editor_properties_list import soundevent_editor_properties
from soudevent_editor.soundevent_editor_kv3_parser import child_merge,child_key, parse_kv3
from soudevent_editor.soundevent_editor_recompile_all import compile


import keyvalues3 as kv3

from soudevent_editor.properties.legacy_property import LegacyProperty
from soudevent_editor.properties.volume_property import VolumeProperty
from soudevent_editor.properties.checkbox_property import CheckboxProperty
from soudevent_editor.properties.origin_property import OriginProperty
from soudevent_editor.properties.combobox_property import ComboboxProperty

class SoundEventEditorMainWidget(QMainWindow):
    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.ui = Ui_SoundEvent_Editor_MainWindow()
        self.ui.setupUi(self)
        self.ui.version.setText(f"Soundevent Editor version: v{version}")

        # Set up the custom file system model
        counter_strike_2_path = get_cs2_path()
        addon_name = get_addon_name()
        self.tree_directory = rf"{counter_strike_2_path}\content\csgo_addons\{addon_name}\sounds"

        # Initialize the mini windows explorer
        self.mini_explorer = SoundEvent_Editor_MiniWindowsExplorer(self.ui.audio_files_explorer, self.tree_directory)

        # Set up the layout for the audio_files_explorer widget
        self.audio_files_explorer_layout = QVBoxLayout(self.ui.audio_files_explorer)
        self.audio_files_explorer_layout.addWidget(self.mini_explorer.tree)
        self.audio_files_explorer_layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setLayout(self.ui.horizontalLayout)
        self.setCentralWidget(container)

        self.soundevent_properties_widget = QWidget()
        self.soundevent_properties_layout = QVBoxLayout(self.ui.soundevent_properties)
        self.soundevent_properties_widget.setLayout(self.soundevent_properties_layout)
        self.ui.scrollArea.setWidget(self.soundevent_properties_widget)
        self.ui.scrollArea.setFocusPolicy(Qt.StrongFocus)

        self.ui.soundevents_list.itemClicked.connect(self.on_soundevent_clicked)
        self.populate_soundevent_list()

        self.ui.save_button.clicked.connect(self.save)
        self.ui.recompile_all_button.clicked.connect(self.recomppile_all)

        self.ui.create_new_soundevent.clicked.connect(self.create_new_soundevent)

    def create_new_soundevent(self):
        existing_items = [self.ui.soundevents_list.item(item).text() for item in
                          range(self.ui.soundevents_list.count())]

        new_soundevent_name = 'new.soundevent'
        unique_name = new_soundevent_name
        counter = 1

        while unique_name in existing_items:
            unique_name = f'{new_soundevent_name}_{counter}'
            counter += 1

        self.ui.soundevents_list.addItem(unique_name)
        self.merge_global_data()


    def populate_soundevent_list(self):
        global soundevents_data
        soundevents_data = parse_kv3(
            os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'soundevents','soundevents_addon.vsndevts'))
        for key, _ in soundevents_data.items():
            item = QListWidgetItem(key)
            self.ui.soundevents_list.addItem(item)



    def save(self):
        global soundevents_data
        self.merge_global_data()
        kv3.write(soundevents_data, (os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'soundevents', 'soundevents_addon.vsndevts')))
        self.ui.status_bar.setText(f"Saved and exported")

        pass
    def get_element_layout_kv3(self, layout, data_out):
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget:
                item = {widget.name: widget.value}
                data_out = child_merge(data_out, item)
        return data_out
    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


    def merge_global_data(self):
        data_out = self.get_element_layout_kv3(self.soundevent_properties_layout, {})
        global soundevents_data
        item_text = self.ui.soundevents_list.currentItem().text()
        try:
            del soundevents_data[item_text]
        except:
            pass
        properties_data = {item_text: data_out}
        soundevents_data = child_merge(soundevents_data, properties_data)
    def on_soundevent_clicked(self, item):
        global soundevents_data
        item_text = item.text()
        self.ui.status_bar.setText(f"Selected: {item_text}")
        self.clear_layout(self.soundevent_properties_layout)
        if item_text in soundevents_data:
            details = soundevents_data[item_text]
            for key, value in details.items():
                value = str(value)
                self.add_property(key, value)

        # if self.soundevent_properties_layout.count() != 0:
        #     data_out = self.get_element_layout_kv3(self.soundevent_properties_layout, {})
        #     self.clear_layout(self.soundevent_properties_layout)
        #     if item_text in soundevents_data:
        #         details = soundevents_data[item_text]
        #         for key, value in details.items():
        #             value = str(value)
        #             self.add_property(key, value)
        #     del soundevents_data[item_text]
        #     properties_data = {item_text: data_out}
        #     soundevents_data = child_merge(soundevents_data, properties_data)
        # else:
        #     if item_text in soundevents_data:
        #         details = soundevents_data[item_text]
        #         for key, value in details.items():
        #             value = str(value)
        #             self.add_property(key, value)


    def add_property(self, name, value):

        # value
        if name == 'volume':
            property_class = VolumeProperty(name=name, display_name="Volume", value=value,widget_list=self.soundevent_properties_layout, min_value=0, max_value=10)
        elif name == 'pitch':
            property_class = VolumeProperty(name=name, display_name="Pitch", value=value,widget_list=self.soundevent_properties_layout, min_value=0, max_value=10)
        elif name == 'delay':
            property_class = VolumeProperty(name=name, display_name="Delay", value=value,widget_list=self.soundevent_properties_layout, min_value=0, max_value=10)
        elif name == 'volume_random_min':
            property_class = VolumeProperty(name=name, display_name="Volume random minimum", value=value,widget_list=self.soundevent_properties_layout, min_value=-10, max_value=10)
        elif name == 'volume_random_max':
            property_class = VolumeProperty(name=name, display_name="Volume random maximum", value=value,widget_list=self.soundevent_properties_layout, min_value=-10, max_value=10)
        elif name == 'pitch_random_min':
            property_class = VolumeProperty(name=name, display_name="Pitch random minimum", value=value,widget_list=self.soundevent_properties_layout, min_value=-10, max_value=10)
        elif name == 'pitch_random_max':
            property_class = VolumeProperty(name=name, display_name="Pitch random maximum", value=value,widget_list=self.soundevent_properties_layout, min_value=-10, max_value=10)
        elif name == 'retrigger_radius':
            property_class = VolumeProperty(name=name, display_name="Retrigger radius", value=value,widget_list=self.soundevent_properties_layout, min_value=0, max_value=19999)
        elif name == 'retrigger_interval_max':
            property_class = VolumeProperty(name=name, display_name="Retrigger interval maximum", value=value,widget_list=self.soundevent_properties_layout, min_value=0, max_value=99)
        elif name == 'retrigger_interval_min':
            property_class = VolumeProperty(name=name, display_name="Retrigger interval minimum", value=value,widget_list=self.soundevent_properties_layout, min_value=0, max_value=99)
        elif name == 'randomize_position_max_radius':
            property_class = VolumeProperty(name=name, display_name="Randomize position maximum", value=value,widget_list=self.soundevent_properties_layout, min_value=0, max_value=19999)
        elif name == 'randomize_position_min_radius':
            property_class = VolumeProperty(name=name, display_name="Randomize position minimum", value=value,widget_list=self.soundevent_properties_layout, min_value=0, max_value=19999)
        elif name == 'reverb_wet':
            property_class = VolumeProperty(name=name, display_name="Reverb wet", value=value,widget_list=self.soundevent_properties_layout, min_value=0, max_value=10)
        elif name == 'block_distance':
            property_class = VolumeProperty(name=name, display_name="Block distance", value=value,widget_list=self.soundevent_properties_layout, min_value=-999, max_value=999)
        elif name == 'vsnd_duration':
            property_class = VolumeProperty(name=name, display_name="Vsound duration", value=value,widget_list=self.soundevent_properties_layout, min_value=0, max_value=9999)
        elif name == 'occlusion_intensity':
            property_class = VolumeProperty(name=name, display_name="Occlusion intensity", value=value,widget_list=self.soundevent_properties_layout, min_value=0, max_value=10)
        elif name == 'distance_effect_mix':
            property_class = VolumeProperty(name=name, display_name="Distance effect mix", value=value,widget_list=self.soundevent_properties_layout, min_value=0, max_value=10)


        # combobox
        elif name == 'base':
            property_class = ComboboxProperty(name=name, display_name="Base", value=value,widget_list=self.soundevent_properties_layout)
        # origin
        elif name == 'position':
            property_class = OriginProperty(name=name, display_name="Position", value=value,widget_list=self.soundevent_properties_layout)
        # bool
        elif name == 'enable_child_events':
            property_class = CheckboxProperty(name=name, display_name="Enable child events", value=value,widget_list=self.soundevent_properties_layout)
        elif name == 'enable_retrigger':
            property_class = CheckboxProperty(name=name, display_name="Enable retrigger", value=value,widget_list=self.soundevent_properties_layout)
        elif name == 'use_time_volume_mapping_curve':
            property_class = CheckboxProperty(name=name, display_name="Use time volume_mapping curve", value=value,widget_list=self.soundevent_properties_layout)
        elif name == 'use_time_volume_mapping_curve':
            property_class = CheckboxProperty(name=name, display_name="Use time volume mapping curve", value=value,widget_list=self.soundevent_properties_layout)
        elif name == 'override_dsp_preset':
            property_class = CheckboxProperty(name=name, display_name="Override dsp preset", value=value,widget_list=self.soundevent_properties_layout)
        elif name == 'set_child_position':
            property_class = CheckboxProperty(name=name, display_name="Set child position", value=value,widget_list=self.soundevent_properties_layout)
        elif name == 'position_relative_to_player':
            property_class = CheckboxProperty(name=name, display_name="Position relative to player", value=value,widget_list=self.soundevent_properties_layout)
        elif name == 'use_world_position':
            property_class = CheckboxProperty(name=name, display_name="Use world position", value=value,widget_list=self.soundevent_properties_layout)
        elif name == 'randomize_position_hemisphere':
            property_class = CheckboxProperty(name=name, display_name="Randomize position hemisphere", value=value,widget_list=self.soundevent_properties_layout)
        elif name == 'use_time_volume_mapping_curve':
            property_class = CheckboxProperty(name=name, display_name="Use time volume mapping curve", value=value,widget_list=self.soundevent_properties_layout)
        elif name == 'use_distance_unfiltered_stereo_mapping_curve':
            property_class = CheckboxProperty(name=name, display_name="Use distance unfiltered stereo mapping curve", value=value,widget_list=self.soundevent_properties_layout)
        elif name == 'restrict_source_reverb':
            property_class = CheckboxProperty(name=name, display_name="Restrict source reverb", value=value,widget_list=self.soundevent_properties_layout)
        elif name == 'block_match_entity':
            property_class = CheckboxProperty(name=name, display_name="Block match entity", value=value,widget_list=self.soundevent_properties_layout)
        elif name == 'block_matching_events':
            property_class = CheckboxProperty(name=name, display_name="Block matching events", value=value,widget_list=self.soundevent_properties_layout)
        elif name == 'use_distance_volume_mapping_curve':
            property_class = CheckboxProperty(name=name, display_name="Use distance volume mapping curve", value=value,widget_list=self.soundevent_properties_layout)
        else:
            property_class = LegacyProperty(name=name, value=value, widget_list=self.soundevent_properties_layout)

        self.soundevent_properties_layout.insertWidget(0, property_class)
        self.soundevent_properties_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def keyPressEvent(self, event):
        focus_widget = QApplication.focusWidget()

        if isinstance(focus_widget, QScrollArea) and focus_widget.viewport().underMouse():
            if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                def get_names_from_layout(layout):
                    names = []
                    for i in range(layout.count()):
                        widget = layout.itemAt(i).widget()
                        if widget:
                            names.append(widget.name)
                    return names
                names_to_remove = get_names_from_layout(self.soundevent_properties_layout)
                elements_in_popupmenu = {}
                for index, item in enumerate(soundevent_editor_properties):
                    for key, value in item.items():
                        if key in names_to_remove:
                            pass
                        else:
                            elements_in_popupmenu.update({key: value})

                elements_in_popupmenu = [elements_in_popupmenu]
                self.popup_menu = PopupMenu(elements_in_popupmenu, add_once=True)
                self.popup_menu.add_property_signal.connect(lambda name, value: self.add_property(name, value))
                self.popup_menu.show()

                event.accept()


            elif event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
                self.select_all_items()
                event.accept()
            elif event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
                self.paste_action()
                event.accept()
        if isinstance(focus_widget, QScrollArea) and focus_widget.viewport().underMouse():
            if event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
                self.save()
                event.accept()

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)

        if self.ui.soundevents_list is QApplication.focusWidget():
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(self.delete_action)
            context_menu.addAction(delete_action)

            rename_action = QAction("Rename", self)
            rename_action.triggered.connect(self.rename_action)
            context_menu.addAction(rename_action)

            duplicate_action = QAction("Duplicate", self)
            duplicate_action.triggered.connect(self.duplicate_action)
            context_menu.addAction(duplicate_action)
        else:
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

    def delete_action(self):
        selected_item = self.ui.soundevents_list.currentItem()
        if selected_item:
            item_text = selected_item.text()
            self.ui.soundevents_list.takeItem(self.ui.soundevents_list.row(selected_item))
            global soundevents_data
            del soundevents_data[item_text]
            # Perform any additional deletion logic here

    def rename_action(self):
        selected_item = self.ui.soundevents_list.currentItem()
        global soundevents_data
        if selected_item:
            item_text = selected_item.text()  # Get the current text of the selected item
            new_name, ok = QInputDialog.getText(self, 'Rename Soundevent', 'Enter new name:', text=item_text)
            if ok and new_name:
                soundevents_data[new_name] = soundevents_data.pop(item_text)
                selected_item.setText(new_name)

    def duplicate_action(self):
        selected_item = self.ui.soundevents_list.currentItem()
        global soundevents_data
        if selected_item:
            item_text = selected_item.text()
            duplicated_data = soundevents_data[item_text].copy()
            new_item_text = f"{item_text}_copy"
            soundevents_data[new_item_text] = duplicated_data
            self.ui.soundevents_list.addItem(new_item_text)

    def recomppile_all(self):
        total_files = len(os.listdir(self.tree_directory))
        progress_bar = QProgressBar()
        progress_bar.setMaximum(total_files)
        progress_bar.show()
        progress_bar.setFixedWidth(300)
        progress_bar.setWindowTitle("Compiling...")

        for index, file_name in enumerate(os.listdir(self.tree_directory), start=1):
            file_path = os.path.join(self.tree_directory, file_name)
            compile(file_path)
            progress_bar.setValue(index)
            QApplication.processEvents()  # Update the GUI to show the progress

        compile(os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'soundevents', 'soundevents_addon.vsndevts'))

        # Hide or reset the progress bar after the loop completes
        progress_bar.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SoundEventEditorMainWidget()
    window.show()
    sys.exit(app.exec())