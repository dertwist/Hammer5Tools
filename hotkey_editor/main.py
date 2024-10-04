import json
import re
from hotkey_editor.ui_main import Ui_MainWindow
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QSplitter, QLineEdit, QKeySequenceEdit, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from hotkey_editor.format import HotkeysOpen
from hotkey_editor.dialog import KeyDialog
from hotkey_editor.objects import *
from preferences import debug
import os
app_dir = os.getcwd()
import keyvalues3 as kv3

class KeyButton(QPushButton):
    DEFAULT_COLOR = "#ababab"
    ACTIVE_COLOR = "#ababab"
    BUTTON_TEXT_DEFAULT = 'Press a key'

    def __init__(self, parent=None, name=None):
        super().__init__(parent)
        self.key = name if name else None
        self.set_button_style(self.DEFAULT_COLOR)
        self.setMaximumWidth(256)
        self.setText(name if name else self.BUTTON_TEXT_DEFAULT)
        self.clicked.connect(self.show_dialog)

    def set_button_style(self, color):
        style = f"""
            QPushButton {{
                font: 580 9pt "Segoe UI";
                border: 1px solid black;
                border-radius: 1px;
                border-color: rgba(80, 80, 80, 150);
                height:22px;
                padding: 4px;
                color: {color};
                background-color: #1C1C1C;
            }}
            QPushButton:hover {{
                background-color: #414956;
                color: white;
            }}
            QPushButton:pressed {{
                background-color: red;
                background-color: #1C1C1C;
                margin: 1px 2px;
            }}
        """
        self.setStyleSheet(style)

    def show_dialog(self):
        dialog = KeyDialog()
        if dialog.exec_():
            val = dialog.value
            if not val:
                self.setText(self.BUTTON_TEXT_DEFAULT)
                self.key = None
            else:
                self.setText(val)
                self.key = val
                self.set_button_style(self.ACTIVE_COLOR)
        else:
            debug((self.key))
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

        Pushinstace = KeyButton()
        Pushinstace.setMinimumSize(256, 0)
        Pushinstace.setMaximumHeight(26)
        self.ui.horizontalLayout_4.addWidget(Pushinstace)

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
        unique_contexts = set()  # Define the set outside the loop
        for context, commands in hammer_commands.items():
            if context not in unique_contexts:
                unique_contexts.add(context)
                context_item = QTreeWidgetItem(root_item)
                context_item.setText(0, context)
                for command in commands:
                    new_item = QTreeWidgetItem(context_item)  # Add new_item as a child of context_item
                    new_item.setText(0, command)

                    key_editor = KeyButton(self.ui.keybindings_tree)  # Initialize KeyButton with parent
                    context_item.addChild(new_item)
                    self.ui.keybindings_tree.setItemWidget(new_item, 1, key_editor)

        # Load from file
        for key, value in self.data.items():
            if key == 'm_Bindings':
                # Create context categories
                # unique_contexts = set()
                for item in value:
                    context = item['m_Context']
                    if context not in unique_contexts:
                        unique_contexts.add(context)
                        context_item = QTreeWidgetItem(root_item)
                        context_item.setText(0, context)
                debug(unique_contexts)

                for item in value:
                    for i in range(root_item.childCount()):
                        if root_item.child(i).text(0) == item['m_Context']:
                            new_item = QTreeWidgetItem()
                            new_item.setText(0, item['m_Command'])

                            key_editor = KeyButton(name=item['m_Input'])
                            for i_child in range(root_item.child(i).childCount()):
                                if item['m_Command'] == root_item.child(i).child(i_child).text(0):
                                    self.ui.keybindings_tree.removeItemWidget(root_item.child(i).child(i_child), 1)
                                    self.ui.keybindings_tree.setItemWidget(root_item.child(i).child(i_child), 1,key_editor)
                                    break
                            else:
                                root_item.child(i).addChild(new_item)
                                self.ui.keybindings_tree.setItemWidget(new_item, 1, key_editor)
        # Add

        # self.ui.keybindings_tree.expandAll()

    def select_preset(self, item):
        self.ui.keybindings_tree.clear()
        self.selected_preset = os.path.join(self.hotkeys_path, f'{item}.txt')
        debug(self.selected_preset)
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