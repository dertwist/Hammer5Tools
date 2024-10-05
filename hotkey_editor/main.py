import json
import re
import shutil

from hotkey_editor.ui_main import Ui_MainWindow
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QSplitter, QLineEdit, QKeySequenceEdit, QPushButton, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from hotkey_editor.dialog import KeyDialog
from hotkey_editor.objects import *
from preferences import debug, get_addon_name, get_cs2_path
from minor_features.addon_functions import launch_addon, kill_addon
from explorer.main import Explorer
import os
import datetime
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
        self.explorer_instance = None

        self.FilterInputInstanceButton = KeyButton()
        self.FilterInputInstanceButton.setMinimumSize(256, 0)
        self.FilterInputInstanceButton.setMaximumHeight(26)
        self.ui.horizontalLayout_4.addWidget(self.FilterInputInstanceButton)

        self.ui.editor_combobox.currentTextChanged.connect(self.editor_switch)
        self.get_path()
        self.editor_switch()

        self.ui.open_button.clicked.connect(self.open_preset)
        self.ui.new_button.clicked.connect(self.new_preset)
        self.ui.save_button.clicked.connect(self.save_preset)
        self.ui.set_current_button.clicked.connect(lambda :self.set_current(True))
        self.ui.save_restart_button.clicked.connect(self.set_save_restart)

        self.ui.command_filter_line.textChanged.connect(lambda text: self.filter_command(text, self.ui.keybindings_tree.invisibleRootItem()))
        self.FilterInputInstanceButton.clicked.connect(self.do_filter_input)


    def do_filter_input(self):
        key = self.FilterInputInstanceButton.key
        self.filter_input(key, self.ui.keybindings_tree.invisibleRootItem())
    def set_current(self, explorer_path=True):
        path_keybindings = os.path.join(get_cs2_path(), 'game', 'core', 'tools', 'keybindings')
        if explorer_path:
            index = self.explorer_instance.tree.selectionModel().selectedIndexes()[0]
            source = self.explorer_instance.model.filePath(index)
        else:
            source = self.opened_file

        dest = os.path.join(path_keybindings, f'{self.editor}_key_bindings.txt')
        debug(f'Source:{source}, dest: {dest}')
        shutil.copy2(source, dest)
        reply = QMessageBox.question(self, 'Confirmation', 'Would you like to restart the editor? Keybindings will be applied upon restart.', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        # Check the user's response and restart if they choose 'Yes'
        if reply == QMessageBox.Yes:
            self.restart()
    def set_save_restart(self):
        self.save_preset()
        self.set_current(False)
        self.restart()
    def restart(self):
        kill_addon()
        launch_addon()
    def get_path(self):
        editor = self.ui.editor_combobox.currentText()
        # convert generic name to source format
        editor = editor.lower()
        self.editor = editor.replace(' ', '_')

        self.hotkeys_path = os.path.join(app_dir, 'hotkeys', editor)
    def editor_switch(self):
        try:
            self.ui.explorer_layout.itemAt(0).widget().deleteLater()
        except:
            pass
        if os.path.exists(self.hotkeys_path):
            pass
        else:
            os.makedirs(self.hotkeys_path)
        self.explorer_instance = Explorer(editor_name='HotkeyEditor', tree_directory=self.hotkeys_path, parent=self.ui.frame, addon=get_addon_name())
        self.ui.explorer_layout.insertWidget(0, self.explorer_instance.frame)
    def populate_editor(self):
        root_item = self.ui.keybindings_tree.invisibleRootItem()
        unique_contexts = set()

        # Load from file
        for key, value in self.data.items():
            if key == 'm_Bindings':
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
                            root_item.child(i).addChild(new_item)
                            self.ui.keybindings_tree.setItemWidget(new_item, 1, key_editor)
        # Load additional actions
        for context, commands in hammer_commands.items():
            if context not in unique_contexts:
                unique_contexts.add(context)
                context_item = QTreeWidgetItem(root_item)
                context_item.setText(0, context)
                for i in range(root_item.childCount()):
                    existing_commands = [root_item.child(i).child(j).text(0) for j in
                                         range(root_item.child(i).childCount())]
                    for command in commands:
                        if command not in existing_commands:
                            new_item = QTreeWidgetItem(context_item)
                            new_item.setText(0, command)
                            key_editor = KeyButton(self.ui.keybindings_tree)
                            context_item.addChild(new_item)
                            self.ui.keybindings_tree.setItemWidget(new_item, 1, key_editor)

    def open_preset(self):
        self.ui.keybindings_tree.clear()
        debug(self.selected_preset)


        index = self.explorer_instance.tree.selectionModel().selectedIndexes()[0]
        filename = self.explorer_instance.model.filePath(index)
        try:
            self.data.update(kv3.read(filename).value)
        except Exception as error:
            print(error)
        self.opened_file = filename

        self.populate_editor()
        print(f'Opened: {self.opened_file}')


    def save_preset(self):
        if self.opened_file != '':
            output = {'editor_info': [{'Info': 'Hammer5Tools Hotkey Editor by Twist', 'GitHub': 'https://github.com/dertwist/Hammer5Tools', 'Steam': 'https://steamcommunity.com/id/der_twist', 'Twitter': 'https://twitter.com/der_twist'}]}
            if self.editor == 'hammer':
                output.update(hammer_macros)
            output.update({'m_Bindings': self.serializing()})
            # There is a huge problem with python interpretation, avoid \\ in string. GizmoDebugHook have \\ as input.
            # So in output it would be only one \ test
            kv3.write(output, self.opened_file)
            print('Preset saved')
    def serializing(self):
        output = []
        root = self.ui.keybindings_tree.invisibleRootItem()
        for context_index in range(root.childCount()):
            for command_index in range(root.child(context_index).childCount()):
                input_widget = (self.ui.keybindings_tree.itemWidget(root.child(context_index).child(command_index), 1)).key
                if input_widget is not None:
                    output.append({'m_Context': root.child(context_index).text(0), 'm_Command': root.child(context_index).child(command_index).text(0), 'm_Input': input_widget})
        return output
    def new_preset(self):
        name = f'{self.editor}_new_keybindings_{datetime.datetime.now().strftime("%m_%d_%Y")}'
        path = os.path.join(self.hotkeys_path, f'{name}.keybindings')
        output = {'editor_info': [
            {'Info': 'Hammer5Tools Hotkey Editor by Twist', 'GitHub': 'https://github.com/dertwist/Hammer5Tools',
             'Steam': 'https://steamcommunity.com/id/der_twist', 'Twitter': 'https://twitter.com/der_twist'}]}
        if self.editor == 'hammer':
            output.update(hammer_macros)
        output.update(hammer_default)
        kv3.write(output, path)

    def filter_input(self, filter_text, parent_item):
        debug(('filter text', filter_text))
        # Reset the root visibility and start the filtering process
        self.filter_widget(parent_item, str(filter_text).lower(), True)
    def filter_command(self, filter_text, parent_item):
        # Reset the root visibility and start the filtering process
        self.filter_item(parent_item, filter_text.lower(), True)

    def filter_item(self, item, filter_text, is_root=False):
        if not isinstance(item, QTreeWidgetItem):
            return False

        # Check if the current item's text matches the filter
        item_text = item.text(0).lower()
        item_visible = filter_text in item_text

        # Always show the root, regardless of filter
        if is_root:
            item.setHidden(False)
        else:
            # Hide the item if it doesn't match the filter
            item.setHidden(not item_visible)

        # Track visibility of any child matching the filter
        any_child_visible = False

        # Recursively filter all children
        for i in range(item.childCount()):
            child_item = item.child(i)
            child_visible = self.filter_item(child_item, filter_text, False)

            if child_visible:
                any_child_visible = True

        # If any child is visible, make sure this item is also visible
        if any_child_visible:
            item.setHidden(False)
            item.setExpanded(True)

        # Return True if this item or any of its children is visible
        return item_visible or any_child_visible

    def filter_widget(self, item, filter_text, is_root=False):
        if not isinstance(item, QTreeWidgetItem):
            return False

        # Check if the current item's text matches the filter
        item_widget = self.ui.keybindings_tree.itemWidget(item, 1)
        if item_widget is None:
            item_text = ''
        else:
            item_text = str(item_widget.key).lower()
        if filter_text == 'none':
            item_visible = True
        else:
            item_visible = filter_text in item_text


        debug(('t', item_text, filter_text))
        # Always show the root, regardless of filter
        if is_root:
            item.setHidden(False)
        else:
            # Hide the item if it doesn't match the filter
            item.setHidden(not item_visible)

        # Track visibility of any child matching the filter
        any_child_visible = False

        # Recursively filter all children
        for i in range(item.childCount()):
            child_item = item.child(i)
            child_visible = self.filter_widget(child_item, filter_text, False)

            if child_visible:
                any_child_visible = True

        # If any child is visible, make sure this item is also visible
        if any_child_visible:
            item.setHidden(False)
            item.setExpanded(True)

        # Return True if this item or any of its children is visible
        return item_visible or any_child_visible
if __name__ == "__main__":
    app = QApplication([])
    app.setStyle('Fusion')
    window = HotkeyEditorMainWindow()
    window.show()
    app.exec()