import os.path
import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QTimer, QSettings
from PySide6.QtGui import QCloseEvent
from smartprop_editor.ui_main import Ui_MainWindow
from preferences import get_config_value

class SmartPropEditorMainWindow(QMainWindow):
    def __init__(self, version="1", parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.version_label.setText(version)

        settings_path = get_config_value('PATHS', 'settings')
        self.settings = QSettings(os.path.join(settings_path, "smartprop_editor.cfg"), QSettings.IniFormat)

        self._restore_user_prefs()

    def _restore_user_prefs(self):
        geo = self.settings.value("SmartPropEditorMainWindow/geometry")
        if geo:
            self.restoreGeometry(geo)

        state = self.settings.value("SmartPropEditorMainWindow/windowState")
        if state:
            self.restoreState(state)

    def closeEvent(self, event: QCloseEvent):
        self._save_user_prefs()

    def _save_user_prefs(self):
        self.settings.setValue("SmartPropEditorMainWindow/geometry", self.saveGeometry())
        self.settings.setValue("SmartPropEditorMainWindow/windowState", self.saveState())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartPropEditorMainWindow()
    window.show()
    sys.exit(app.exec())