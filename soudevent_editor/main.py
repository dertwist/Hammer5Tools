import os.path
import sys
import subprocess

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QListWidgetItem, QMenu, QScrollArea
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QAction,QCursor
from soudevent_editor.ui_main import Ui_MainWindow
from preferences import get_config_value, get_cs2_path, get_addon_name
from explorer.main import Explorer
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QListWidgetItem, QMenu, QScrollArea, QInputDialog
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
from PySide6.QtWidgets import QProgressBar
from popup_menu.popup_menu_main import PopupMenu
from preferences import settings

from soudevent_editor.properties.soundevent_editor_properties_list import soundevent_editor_properties
from soudevent_editor.soundevent_editor_recompile_all import compile

class SoundEventEditorMainWindow(QMainWindow):
    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        print(f"Soundevent Editor version: v{version}")

    #======================================[Window State]========================================
    def _restore_user_prefs(self):
        """Restore window state"""
        geo = self.settings.value("SoundEventEditorMainWindow/geometry")
        if geo:
            self.restoreGeometry(geo)

        state = self.settings.value("SoundEventEditorMainWindow/windowState")
        if state:
            self.restoreState(state)

    def _save_user_prefs(self):
        """Save window state"""
        self.settings.setValue("SoundEventEditorMainWindow/geometry", self.saveGeometry())
        self.settings.setValue("SoundEventEditorMainWindow/windowState", self.saveState())
    def closeEvent(self, event):
        self._save_user_prefs()