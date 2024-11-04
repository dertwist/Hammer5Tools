import subprocess
import os
from pydoc import importfile

from src.preferences import get_addon_name, get_cs2_path
from src.soudevent_editor.ui_main import Ui_MainWindow
from src.explorer.main import Explorer
from PySide6.QtWidgets import QMainWindow, QWidget, QListWidgetItem, QMenu
from src.preferences import settings


class SoundEventEditorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = settings
        self.realtime_save = False

        self.properties_groups_hide()

        # Stylesheet
        self.ui.frame.setStyleSheet("""
        QFrame#frame {
            border: 2px solid black; 
            border-color: rgba(80, 80, 80, 255);
        }
        QFrame#frame QLabel {
            border: 0px solid black; 
        }
        """)

    #==============================================================<  Explorer  >===========================================================
        self.tree_directory = os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name(), 'sounds')
        if os.path.exists(self.tree_directory):
            pass
        else:
            os.makedirs(self.tree_directory)
        self.mini_explorer = Explorer(tree_directory=self.tree_directory, addon=get_addon_name(), editor_name='SoundEvent_Editor', parent=self.ui.explorer_layout_widget)
        self.ui.explorer_layout.addWidget(self.mini_explorer.frame)

    #=======================================================<  Properties widget  >=====================================================

    def properties_groups_hide(self):
        self.ui.properties_spacer.hide()
        self.ui.properties_placeholder.show()
    def properties_groups_show(self):
        self.ui.properties_placeholder.hide()
        self.ui.properties_spacer.show()

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