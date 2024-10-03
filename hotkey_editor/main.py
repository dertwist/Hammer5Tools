import json
import re
from hotkey_editor.ui_main import Ui_MainWindow
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QSplitter
from PySide6.QtCore import Qt
from hotkey_editor.format import HotkeysOpen
from preferences import get_config_value
hotkeys_path = get_config_value('PATHS', 'hotkeys_presets')
class HotkeyEditorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.keySequenceEdit.setMaximumSequenceLength(4)
        self.ui.keySequenceEdit.setClearButtonEnabled(True)

    def populate_presets(self, editor):
        pass
    def open_file(self):
        instance = HotkeysOpen()
        print(instance.data)
if __name__ == "__main__":
    app = QApplication([])
    app.setStyle('Fusion')
    window = HotkeyEditorMainWindow()
    window.show()
    app.exec()