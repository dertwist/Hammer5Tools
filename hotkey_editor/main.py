import json
import re
from hotkey_editor.ui_main import Ui_MainWindow
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QSplitter, QLineEdit, QKeySequenceEdit, QPushButton
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
        self.data = {}
        self.opened_file = ''
        self.editor = ''

        if self.ui.input_filter_line.findChild(QLineEdit, "qt_keysequenceedit_lineedit"):
            self.ui.input_filter_line.findChild(QLineEdit, "qt_keysequenceedit_lineedit").setPlaceholderText("Input filter")


        self.ui.editor_combobox.currentTextChanged.connect(self.populate_presets)
        self.get_path()
        self.populate_presets()

        self.ui.presets_list.itemClicked.connect(lambda item: self.select_preset(item.text()))
        self.ui.new_button.clicked.connect(self.new_preset)
        self.ui.save_button.clicked.connect(self.save_preset)
    def get_path(self):
        editor = self.ui.editor_combobox.currentText()
        # convert generic name to source format
        editor = editor.lower()
        self.editor = editor.replace(' ', '_')

        self.hotkeys_path = os.path.join(app_dir, 'hotkeys', editor)
    def populate_presets(self):
        if os.path.exists(self.hotkeys_path):
            pass
        else:
            os.makedirs(self.hotkeys_path)
        for file in os.listdir(self.hotkeys_path):
            item = os.path.splitext(file)[0]
            self.ui.presets_list.addItem(item)
    def populate_editor(self):
        root_item = self.ui.keybindings_tree.invisibleRootItem()
        for key, value in self.data.items():
            if key == 'm_Bindings':
                # Create context categories
                unique_contexts = set()
                for item in value:
                    context = item['m_Context']
                    if context not in unique_contexts:
                        unique_contexts.add(context)
                        context_item = QTreeWidgetItem(root_item)
                        context_item.setText(0, context)
                print(unique_contexts)

                for item in value:
                    # Find the child item with the specific text 'm_Context'
                    for i in range(root_item.childCount()):
                        if root_item.child(i).text(0) == item['m_Context']:
                            new_item = QTreeWidgetItem()
                            new_item.setText(0, item['m_Command'])

                            key_editor = QPushButton()
                            key_editor.setStyleSheet("""
                            QPushButton {
                            
                                font: 580 9pt "Segoe UI";
                            
                            
                                border: 1px solid black;
                                border-radius: 1px;
                                border-color: rgba(80, 80, 80, 150);
                                height:22px;
                                padding-top: 4px;
                                padding-bottom:4px;
                                padding-left: 4px;
                                padding-right: 4px;
                                color: #E3E3E3;
                                background-color: #1C1C1C;
                            }
                            QPushButton:hover {
                                background-color: #414956;
                                color: white;
                            }
                            QPushButton:pressed {
                                background-color: red;
                                background-color: #1C1C1C;
                                margin: 1 px;
                                margin-left: 2px;
                                margin-right: 2px;
                            
                            }""")
                            key_editor.setMaximumWidth(256)
                            key_editor.setText(item['m_Input'])
                            root_item.child(i).addChild(new_item)
                            self.ui.keybindings_tree.setItemWidget(new_item, 1, key_editor)


        self.ui.keybindings_tree.expandAll()

    def select_preset(self, item):
        self.selected_preset = os.path.join(self.hotkeys_path, f'{item}.txt')
        print(self.selected_preset)
        self.open_preset(self.selected_preset)
        self.populate_editor()

    def open_preset(self, file):
        instance = HotkeysOpen(file)
        self.data.update(instance.data)
        self.opened_file = file


    def save_preset(self):
        if self.opened_file != '':
            output = {'editor_info': [{'Info': 'Hammer5Tools Hotkey Editor by Twist', 'GitHub': 'https://github.com/dertwist/Hammer5Tools', 'Steam': 'https://steamcommunity.com/id/der_twist', 'Twitter': 'https://twitter.com/der_twist'}]}
            if self.editor == 'hammer':
                output.update(hammer_macros)
            output.update(self.data)
            # There is a huge problem with python interpretation, avoid \\ in string. GizmoDebugHook have \\ as input.
            # So in output it would be only one \ test
            name = 'test'
            path = os.path.join(self.hotkeys_path, f'{name}.txt')
            kv3.write(output, path)
    def new_preset(self):
        name = 'new_preset'
        path = os.path.join(self.hotkeys_path, f'{name}.txt')
        kv3.write(hammer_default, path)
if __name__ == "__main__":
    app = QApplication([])
    app.setStyle('Fusion')
    window = HotkeyEditorMainWindow()
    window.show()
    app.exec()