import os.path
import sys
import time

from qt_material import apply_stylesheet
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QListWidgetItem, QMenu, QScrollArea
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction,QCursor
from smartprop_editor.ui_main import Ui_MainWindow
from preferences import get_config_value, get_cs2_path, get_addon_name, set_config_value
from soudevent_editor.soundevent_editor_mini_windows_explorer import SoundEvent_Editor_MiniWindowsExplorer
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QListWidgetItem, QMenu, QScrollArea, QInputDialog
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
from PySide6.QtWidgets import QProgressBar
from popup_menu.popup_menu_main import PopupMenu
import json

import keyvalues3 as kv3


class SmartPropEditorMainWindow(QMainWindow):
    def __init__(self, version="1", parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.version_label.setText(version)

    def closeEvent(self, event):
        pass

# Main block remains the same
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartPropEditorMainWindow()
    apply_stylesheet(app, theme='dark_yellow.xml')
    window.show()
    sys.exit(app.exec())