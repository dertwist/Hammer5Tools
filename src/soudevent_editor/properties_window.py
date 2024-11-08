import subprocess
import os
from src.soudevent_editor.ui_properties_window import Ui_MainWindow
from PySide6.QtWidgets import QMainWindow, QWidget, QListWidgetItem, QMenu
from src.preferences import settings
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
            for item in reversed(_data):
                new_widget = SoundEventEditorPropertyFrame()
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