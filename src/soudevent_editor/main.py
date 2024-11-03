import subprocess

from soudevent_editor.ui_main import Ui_MainWindow
from src.explorer.main import Explorer
from PySide6.QtWidgets import QMainWindow, QWidget, QListWidgetItem, QMenu
from preferences import settings


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