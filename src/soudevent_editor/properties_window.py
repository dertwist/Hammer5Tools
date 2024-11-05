import subprocess
import os
from src.soudevent_editor.ui_properties_window import Ui_MainWindow
from PySide6.QtWidgets import QMainWindow, QWidget, QListWidgetItem, QMenu
from src.preferences import settings


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

    #=============================================================<  Property  >==========================================================
    def create_property(self):
        pass
    def delete_property(self):
        pass
    def get_property_value(self):
        pass
    def set_property_value(self):
        pass