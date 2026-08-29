import logging
import shutil

from gui.editors.hotkey_editor.ui_main import Ui_MainWindow
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeWidgetItem, QPushButton, QMessageBox
from PySide6.QtCore import Signal
from gui.editors.hotkey_editor.dialog import KeyDialog
from gui.editors.hotkey_editor.objects import hammer_commands, hammer_default, hammer_macros
from gui.settings.common import get_addon_name, get_cs2_path
from gui.other.addon_functions import launch_addon, kill_addon
from gui.widgets.explorer.main import Explorer
import os
import datetime
import keyvalues3 as kv3
from gui.common import app_dir, Hotkeys_Path, user_data_dir
from gui.editors.hotkey_editor.document_model import HotkeyDocument, serialize

log = logging.getLogger(__name__)

class KeyButton(QPushButton):
    key_changed = Signal(object)
    BUTTON_TEXT_DEFAULT = 'Press a key'

    def __init__(self, parent=None, name=None):
        super().__init__(parent)
        self.key = name if name else None
        self.setMaximumWidth(256)
        self.setText(name if name else self.BUTTON_TEXT_DEFAULT)
        self.clicked.connect(self.show_dialog)

    def set_button_style(self, color):
        # DEFAULT_COLOR and ACTIVE_COLOR are the same value, so this button
        # never actually needs a per-call color override.
        self.setProperty("h5Component", "hotkeyKeyButton")

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
            self.key_changed.emit(self.key)
        else:
            pass
class HotkeyEditorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.parent = parent

        # variables definition
        self.selected_preset = ''
        self.hotkeys_path = ''
        self.document = HotkeyDocument()
        self.opened_file = ''
        self.editor = ''
        self.explorer_instance = None

        self.FilterInputInstanceButton = KeyButton()
        self.FilterInputInstanceButton.setMinimumSize(256, 0)
        self.FilterInputInstanceButton.setMaximumHeight(26)
        self.ui.horizontalLayout_4.addWidget(self.FilterInputInstanceButton)


        self.get_path()
        self.editor_switch()
        self.ui.editor_combobox.currentTextChanged.connect(self.editor_switch)

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
        cs2_path = get_cs2_path()
        if not cs2_path:
            QMessageBox.warning(self, "CS2 Path Not Set", "CS2 installation path is not set. Please set it in Settings.")
            return
        path_keybindings = os.path.join(cs2_path, 'game', 'core', 'tools', 'keybindings')
        if explorer_path:
            source = self.explorer_instance.get_current_path()
        else:
            source = self.opened_file

        dest = os.path.join(path_keybindings, f'{self.editor}_key_bindings.txt')
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
        editor = editor.lower()
        self.editor = editor.replace(' ', '_')

        self.hotkeys_path = os.path.join(Hotkeys_Path, editor)
    def editor_switch(self):
        try:
            self.ui.explorer_layout.itemAt(0).widget().deleteLater()
        except:
            pass
        if os.path.exists(self.hotkeys_path):
            pass
        else:
            os.makedirs(self.hotkeys_path)
        self.explorer_instance = Explorer(editor_name='HotkeyEditor', tree_directory=self.hotkeys_path, parent=self.parent, addon=get_addon_name())
        self.ui.explorer_layout.insertWidget(0, self.explorer_instance.frame)

    def populate_editor(self):
        root_item = self.ui.keybindings_tree.invisibleRootItem()
        existing_items = {}

        def is_command_exist(context, command, input_value):
            # Check if the command with the specific input exists in the context
            return (command, input_value) in existing_items.get(context, set())

        def add_context_if_not_exist(context):
            if context not in existing_items:
                existing_items[context] = set()
                context_item = QTreeWidgetItem(root_item)
                context_item.setText(0, context)
                return context_item
            else:
                # Find the existing context item
                for i in range(root_item.childCount()):
                    if root_item.child(i).text(0) == context:
                        return root_item.child(i)
            return None

        for binding in self.document.bindings:
            context = binding.context
            command = binding.command
            input_value = binding.input
            context_item = add_context_if_not_exist(context)

            if not is_command_exist(context, command, input_value):
                existing_items[context].add((command, input_value))
                new_item = QTreeWidgetItem(context_item)
                new_item.setText(0, command)

                key_editor = KeyButton(name=input_value)
                key_editor.key_changed.connect(
                    lambda value, target=binding: setattr(target, "input", value)
                )
                context_item.addChild(new_item)
                self.ui.keybindings_tree.setItemWidget(new_item, 1, key_editor)

        for context, commands in hammer_commands.items():
            context_item = add_context_if_not_exist(context)

            # Collect existing commands once per context
            existing_commands = existing_items.get(context, set())

            for command in commands:
                if command not in {cmd for cmd, _ in existing_commands}:
                    existing_items[context].add((command, ""))  # Assuming no specific input for additional actions
                    new_item = QTreeWidgetItem(context_item)
                    new_item.setText(0, command)
                    key_editor = KeyButton(name="")  # Assuming no specific input for additional actions
                    binding = self.document.ensure(context, command)
                    key_editor.key_changed.connect(
                        lambda value, target=binding: setattr(target, "input", value)
                    )
                    context_item.addChild(new_item)
                    self.ui.keybindings_tree.setItemWidget(new_item, 1, key_editor)

    def open_preset(self):
        self.ui.keybindings_tree.clear()


        filename = self.explorer_instance.get_current_path()
        self.explorer_instance.add_recent_file(filename)
        try:
            self.document = HotkeyDocument.from_mapping(kv3.read(filename).value)
        except Exception as error:
            log.error(error)
        self.opened_file = filename

        self.populate_editor()
        print(f'Opened: {self.opened_file}')


    def save_preset(self):
        if self.opened_file != '':
            self.write_preset(self.opened_file, self.document.to_mapping())
            print('Preset saved')

    def write_preset(self, path, value):
        output = {}
        if self.editor == 'hammer':
            output.update(hammer_macros)
        output.update(value)
        output.pop('editor_info', None)
        with open(path, 'w', encoding='utf-8', newline='\n') as file:
            file.write(serialize(output))

    def serializing(self):
        return self.document.to_mapping()["m_Bindings"]
    def new_preset(self):
        name = f'{self.editor}_new_keybindings_{datetime.datetime.now().strftime("%m_%d_%Y")}'
        path = os.path.join(self.hotkeys_path, f'{name}.keybindings')
        self.write_preset(path, hammer_default)

    def filter_input(self, filter_text, parent_item):
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

        return item_visible or any_child_visible
if __name__ == "__main__":
    app = QApplication([])
    app.setStyle('Fusion')
    window = HotkeyEditorMainWindow()
    window.show()
    app.exec()
