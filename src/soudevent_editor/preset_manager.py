import subprocess
import os
from pydoc import importfile
import sys
from src.preferences import get_addon_name, get_cs2_path
from src.soudevent_editor.ui_preset_manager import Ui_MainWindow
from src.explorer.main import Explorer
from PySide6.QtWidgets import QMainWindow, QWidget, QListWidgetItem, QMenu, QApplication
from src.preferences import settings
from src.soudevent_editor.properties_window import SoundEventEditorPropertiesWindow


class SoundEventEditorPresetManagerWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = settings


        self.PropertiesWindowInit()

    #==============================================================<  Explorer  >===========================================================
        self.tree_directory = os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name(), 'sounds')
        if os.path.exists(self.tree_directory):
            pass
        else:
            os.makedirs(self.tree_directory)
        self.mini_explorer = Explorer(tree_directory=self.tree_directory, addon=get_addon_name(), editor_name='SoundEvent_Editor', parent=self.ui.explorer_layout_widget)
        self.ui.explorer_layout.addWidget(self.mini_explorer.frame)

    #=======================================================<  Properties Window  >=====================================================

    def PropertiesWindowInit(self):
        PropertiesWindow = SoundEventEditorPropertiesWindow()
        self.ui.frame.layout().addWidget(PropertiesWindow)

    #======================================[Window State]========================================
    def _restore_user_prefs(self):
        """Restore window state"""
        geo = self.settings.value("SoundEventEditorPresetManagerWindow/geometry")
        if geo:
            self.restoreGeometry(geo)

        state = self.settings.value("SoundEventEditorPresetManagerWindow/windowState")
        if state:
            self.restoreState(state)

    def _save_user_prefs(self):
        """Save window state"""
        self.settings.setValue("SoundEventEditorPresetManagerWindow/geometry", self.saveGeometry())
        self.settings.setValue("SoundEventEditorPresetManagerWindow/windowState", self.saveState())
    def closeEvent(self, event):
        self._save_user_prefs()
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = SoundEventEditorPresetManagerWindow()
    main_window.show()
    sys.exit(app.exec())
