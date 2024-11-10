import ast
import subprocess
import os
from src.soudevent_editor.ui_properties_window import Ui_MainWindow
from PySide6.QtWidgets import QMainWindow, QWidget, QListWidgetItem, QMenu
from PySide6.QtGui import QKeySequence
from PySide6.QtCore import Qt
from src.preferences import settings, debug
from src.soudevent_editor.property.frame import SoundEventEditorPropertyFrame

class genericObejct:
    def __init__(self):
        super().__init__()

class SoundEventEditorPropertiesWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = settings
        self.realtime_save = False
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)

        self.properties_groups_hide()


    #=======================================================<  Properties widget  >=====================================================

    def properties_groups_hide(self):
        self.ui.properties_spacer.hide()
        self.ui.properties_placeholder.show()
        self.ui.CommetSeciton.hide()
    def properties_groups_show(self):
        self.ui.properties_placeholder.hide()
        self.ui.properties_spacer.show()
        self.ui.CommetSeciton.show()
    def properties_clear(self):
        for i in range(self.ui.properties_layout.count()):
            widget = self.ui.properties_layout.itemAt(i).widget()
            if isinstance(widget, SoundEventEditorPropertyFrame):
                widget.deleteLater()
    def populate_properties(self, _data):
        "Loading properties from given data"
        if isinstance(_data, dict):
            # Reverse input data and use insertWidget with index 0 because in that way all widgets will be upper spacer
            debug(f"_data \n {_data}")
            for item, value in reversed(_data.items()):
                print(f'_data itme populate properties{item}')
                new_widget = SoundEventEditorPropertyFrame(_data={item:value}, widget_list=self.ui.properties_layout)
                self.ui.properties_layout.insertWidget(0,new_widget)
        else:
            print(f"[SoundEventEditorProperties]: Wrong input data format. Given data: \n {_data} \n {type(_data)}")

    #=============================================================<  Property  >==========================================================
    def create_property(self):
        pass
    def delete_property(self):
        pass
    def get_property_value(self):
        pass
    def set_property_value(self):
        pass
    #============================================================<  Context menu  >=========================================================
    def open_context_menu(self, position):
        menu = QMenu()
        menu.addSeparator()
        # New Property action
        new_property = menu.addAction("New Property")
        new_property.setShortcut(QKeySequence(QKeySequence("Ctrl + F")))
        # Paste action
        paste = menu.addAction("Paste")
        paste.setShortcut(QKeySequence(QKeySequence("Ctrl + V")))
        menu.exec(self.ui.scrollArea.viewport().mapToGlobal(position))