import json
import re
from hotkey_editor.ui_main import Ui_MainWindow
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QSplitter
from PySide6.QtCore import Qt
from hotkey_editor.format import HotkeysOpen
from hotkey_editor.objects import *
import os
app_dir = os.getcwd()
import keyvalues3 as kv3
class HotkeyEditorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # variables definition
        self.selected_preset = ''
        self.hotkeys_path = ''


        self.ui.keySequenceEdit.setMaximumSequenceLength(4)
        self.ui.keySequenceEdit.setClearButtonEnabled(True)
        self.ui.editor_combobox.currentTextChanged.connect(self.populate_presets)
        self.get_path()
        self.populate_presets()

        self.ui.presets_list.itemClicked.connect(lambda item: self.select_preset(item.text()))
        self.ui.new_button.clicked.connect(self.new_preset)
    def get_path(self):
        editor = self.ui.editor_combobox.currentText()
        # convert generic name to source format
        editor = editor.lower()
        editor = editor.replace(' ', '_')

        self.hotkeys_path = os.path.join(app_dir, 'hotkeys', editor)
    def populate_presets(self):
        if os.path.exists(self.hotkeys_path):
            pass
        else:
            os.makedirs(self.hotkeys_path)
        for file in os.listdir(self.hotkeys_path):
            item = os.path.splitext(file)[0]
            self.ui.presets_list.addItem(item)

    def select_preset(self, item):
        self.selected_preset = os.path.join(self.hotkeys_path, f'{item}.txt')
        print(self.selected_preset)
        self.open_preset(self.selected_preset)
    def open_preset(self, file):
        instance = HotkeysOpen(file)
        print(instance.data)
    def new_preset(self):
        name = 'new_preset'
        path = os.path.join(self.hotkeys_path, f'{name}.txt')
        print(path)
        kv3.write(hammer_default, path)
if __name__ == "__main__":
    app = QApplication([])
    app.setStyle('Fusion')
    window = HotkeyEditorMainWindow()
    window.show()
    app.exec()