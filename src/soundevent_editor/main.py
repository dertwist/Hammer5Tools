import ast, shutil

from src.settings.main import get_addon_name, get_cs2_path, debug
from src.soundevent_editor.ui_main import Ui_MainWindow
from src.explorer.main import Explorer
from PySide6.QtWidgets import QMainWindow, QMenu, QTreeWidget, QMessageBox, QApplication, QTreeWidgetItem
from PySide6.QtGui import QKeySequence, QUndoStack, QKeyEvent
from PySide6.QtCore import Qt
from src.popup_menu.main import PopupMenu
from src.widgets import HierarchyItemModel, ErrorInfo
from src.settings.main import settings
from src.soundevent_editor.properties_window import SoundEventEditorPropertiesWindow
from src.soundevent_editor.preset_manager import SoundEventEditorPresetManagerWindow
from src.common import *
from src.soundevent_editor.commands import DeleteTreeItemCommand
from src.soundevent_editor.internal_explorer import InternalSoundFileExplorer
from src.soundevent_editor.audio_player import AudioPlayer
from src.widgets_common import exception_handler

class CopyDefaultSoundFolders:
    def __init__(self):
        """Coping  soundevents file and sounds from sounds folder from addon_template to the current addon"""
        super().__init__()
        # Source
        self.soundevents_source_path = os.path.join(get_cs2_path(), 'content', 'csgo_addons', 'addon_template', 'soundevents', 'soundevents_addon.vsndevts')
        self.sounds_source_path = os.path.join(get_cs2_path(), 'content', 'csgo_addons', 'addon_template', 'sounds')
        # Destination
        self.filepath_vsndevts = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'soundevents', 'soundevents_addon.vsndevts')
        self.filepath_sounds = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'sounds')
        self.copy_with_overwrite()

    def copy_with_overwrite(self):
        # Ensure destination directories exist
        os.makedirs(os.path.dirname(self.filepath_vsndevts), exist_ok=True)
        os.makedirs(self.filepath_sounds, exist_ok=True)

        # Copy the soundevents file, overwriting if it exists
        shutil.copy2(self.soundevents_source_path, self.filepath_vsndevts)

        # Copy the sounds directory, overwriting existing files
        if os.path.exists(self.sounds_source_path):
            for item in os.listdir(self.sounds_source_path):
                source_item = os.path.join(self.sounds_source_path, item)
                destination_item = os.path.join(self.filepath_sounds, item)
                if os.path.isdir(source_item):
                    shutil.copytree(source_item, destination_item, dirs_exist_ok=True)
                else:
                    shutil.copy2(source_item, destination_item)
class LoadSoundEvents:
    def __init__(self, tree: QTreeWidget, path: str):
        super().__init__()
        data = open(path, "r")
        data = Kv3ToJson(data.read())
        self.tree = tree
        self.tree.clear()
        self.root = self.tree.invisibleRootItem()
        for key in data:
            if key != "editor_info":
                new_item = HierarchyItemModel(_data=data[key], _name=key)
                self.root.addChild(new_item)

class SaveSoundEvents:
    def __init__(self, tree: QTreeWidget, path:str):
        super().__init__()
        data = {}
        data.update(editor_info)
        for index in range(tree.invisibleRootItem().childCount()):
            item = tree.invisibleRootItem().child(index)
            key = str(item.text(0))
            value = item.text(1)
            value = ast.literal_eval(value)
            item_value = {key:value}
            data.update(item_value)
        # Write to file
        with open(path, 'w') as output:
            output.write(JsonToKv3(data))

class SoundEventEditorMainWindow(QMainWindow):
    def __init__(self, parent=None, update_title=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = settings
        self.undo_stack = QUndoStack(self)
        self.update_title = update_title

        # Variables
        self.filepath_vsndevts = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'soundevents','soundevents_addon.vsndevts')
        self.filepath_sounds = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'sounds')

        # Variables debug
        debug(f"self.filepath_vsndevts : {self.filepath_vsndevts}")
        debug(f"self.filepath_sounds : {self.filepath_sounds}")

        # Init LoadSoundEvents
        self.load_soundevents()
        # Init PropertiesWindow
        self.PropertiesWindowInit()

        # Init Hierarchy
        self.ui.hierarchy_widget.header().setSectionHidden(1, True)
        self.ui.hierarchy_widget.currentItemChanged.connect(self.on_changed_hierarchy_item)
        self.ui.hierarchy_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.hierarchy_widget.customContextMenuRequested.connect(self.open_hierarchy_menu)

        # Init filter
        self.ui.hierarchy_widget.installEventFilter(self)

        # Init Hierarchy filer bar
        self.ui.hierarchy_search_bar_widget.textChanged.connect(lambda text:self.search_hierarchy(text, self.ui.hierarchy_widget.invisibleRootItem()))

        # Connections
        self.ui.open_preset_manager_button.clicked.connect(self.OpenPresetManager)
        self.ui.reload_button.clicked.connect(self.load_soundevents)
        self.ui.output_button.clicked.connect(self.open_soundevnets_file)
        self.ui.save_file_button.clicked.connect(self.save_soundevents)


        # Creating Audioplayer for explorer
        self.audio_player = None

        # Explorer
        if os.path.exists(self.filepath_sounds):
            pass
        else:
            os.makedirs(self.filepath_sounds)
        self.mini_explorer = Explorer(tree_directory=self.filepath_sounds, addon=get_addon_name(), editor_name='SoundEvent_Editor', parent=self.ui.explorer_layout_widget, use_internal_player=True)
        self.mini_explorer.tree.setStyleSheet("""border:none""")
        self.mini_explorer.play_sound.connect(self.play_sound)
        self.ui.explorer_layout.addWidget(self.mini_explorer.frame)

        # Internal Explorer
        self.internal_explorer = InternalSoundFileExplorer(self.audio_player)
        self.internal_explorer.setStyleSheet("""border:none""")
        self.ui.internal_explorer_layout.addWidget(self.internal_explorer)
        self.ui.internal_explorer_search_bar.textChanged.connect(lambda text: self.search_hierarchy(text, self.internal_explorer.invisibleRootItem()))
        self.internal_explorer.play_sound.connect(self.play_sound)

        # Audio player init
        self.add_player()
    #============================================================<  AudioPlayer  >==========================================================
    def add_player(self):
        self.audio_player_widget = AudioPlayer()
        self.ui.explorer_layout_widget.layout().insertWidget(1,self.audio_player_widget)
    def play_sound(self, file_path):
        self.audio_player_widget.deleteLater()
        self.add_player()
        self.audio_player_widget.set_audiopath(file_path)
        self.audio_player_widget.play_sound()
    #     if self.audio_player is not None:
    #         self.audio_player.deleteLater()
    #     self.audio_player = QMediaPlayer()
    #     self.audio_output = QAudioOutput()
    #     self.audio_player.setAudioOutput(self.audio_output)
    #     self.audio_player.setSource(QUrl.fromLocalFile(file_path))
    #     self.audio_player.play()
    # #==============================================================<  Actions  >============================================================
    def realtime_save(self):
        return self.ui.realtime_save_checkbox.isChecked()
    #============================================================<  SoundEvents  >==========================================================
    def open_soundevnets_file(self):
        os.startfile(self.filepath_vsndevts)
    @exception_handler
    def load_soundevents(self):
        """Load soundevents. If there is no soundevents file, ask the user if they want to copy it from the CS2 addon template folder."""
        # Cleanup
        try:
            self.PropertiesWindow.properties_clear()
            self.ui.hierarchy_widget.clear()
        except:
            pass
        if os.path.exists(self.filepath_vsndevts):
            LoadSoundEvents(tree=self.ui.hierarchy_widget, path=self.filepath_vsndevts)
        else:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText(
                "It seems there is no soundevents file available. Would you like to create a default one? Please note: this action may overwrite any existing WAV files in the sounds folder, if they are present.")
            msg_box.setWindowTitle("Warning")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            response = msg_box.exec()
            if response == QMessageBox.Yes:
                CopyDefaultSoundFolders()
                LoadSoundEvents(tree=self.ui.hierarchy_widget, path=self.filepath_vsndevts)

    @exception_handler
    def save_soundevents(self):
        SaveSoundEvents(tree=self.ui.hierarchy_widget, path=(self.filepath_vsndevts))
        if not self.realtime_save():
            print(f'Saved file: {self.filepath_vsndevts}')
            self.update_title('saved', self.filepath_vsndevts)

    #=======================================================<  Properties Window  >=====================================================

    def PropertiesWindowInit(self):
        self.PropertiesWindow = SoundEventEditorPropertiesWindow(tree=self.ui.hierarchy_widget)
        self.ui.frame.layout().addWidget(self.PropertiesWindow)
        self.PropertiesWindow.edited.connect(self.PropertiesWindowUpdate)
    def PropertiesWindowUpdate(self):
        item = self.ui.hierarchy_widget.currentItem()
        _data = self.PropertiesWindow.value
        self.update_hierarchy_item(item, _data)

    #===============================================================<  Filter  >============================================================
    def eventFilter(self, source, event):
        """Handle keyboard and shortcut events for various widgets."""

        if event.type() == QKeyEvent.KeyPress:
            # Handle events for hierarchy_widget
            if source == self.ui.hierarchy_widget:
                # Copy (Ctrl + C)
                if event.matches(QKeySequence.Copy):
                    self.copy_item(self.ui.hierarchy_widget)
                    return True

                # Paste (Ctrl + V)
                if event.matches(QKeySequence.Paste):
                    self.paste_item(self.ui.hierarchy_widget, paste_to_parent=True)
                    return True

                # Delete
                if event.matches(QKeySequence.Delete):
                    self.undo_stack.push(DeleteTreeItemCommand(self.ui.hierarchy_widget))

                    return True
                # Move Up
                if event.modifiers() == (Qt.ControlModifier) and event.key() == Qt.Key_Up:
                    self.move_tree_item(self.ui.hierarchy_widget, -1)
                    return True
                # Move Down
                if event.modifiers() == (Qt.ControlModifier) and event.key() == Qt.Key_Down:
                    self.move_tree_item(self.ui.hierarchy_widget, 1)
                    return True
                # Duplicate
                if event.modifiers() == (Qt.ControlModifier) and event.key() == Qt.Key_D:
                    self.duplicate_hierarchy_items(self.ui.hierarchy_widget)
                    return True

                if event.matches(QKeySequence.Undo):
                    self.undo_stack.undo()
                    return True
                if event.matches(QKeySequence.Redo):
                    self.undo_stack.redo()
                    return True


                if source.viewport().underMouse():
                    if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                        self.call_soundevent_preset_menu()
                        return True

        return super().eventFilter(source, event)

    #=========================================================<  Hierarchy Actions  >=======================================================
    def new_soundevent(self, _data: dict = None, __soundevent_name: str = None):
        """Creates new soundevent using given data. Input dict"""
        if __soundevent_name is None:
            __soundevent_name = "SoundEvent"
        __soundevent_name = self.unique_soundevent_int(__soundevent_name)
        __soundevent = HierarchyItemModel(_name=__soundevent_name, _data=_data)
        self.ui.hierarchy_widget.invisibleRootItem().addChild(__soundevent)

    def unique_soundevent_int(self, _name: str = None):
        """Creating Unique name for new hierarchy element"""
        if _name is None:
            _name = "SoundEvent"

        # Collect existing names
        existing_names = set()
        root = self.ui.hierarchy_widget.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            existing_names.add(item.text(0))

        # Find a unique name with a numerical suffix
        index = 0
        unique_name = f"{_name}.{index:02d}"
        while unique_name in existing_names:
            index += 1
            unique_name = f"{_name}.{index:02d}"

        return unique_name

    def new_soundevent_blank(self):
        """Create empty soundevent using """
        self.new_soundevent(_data={})
    def new_soundevent_preset(self, _preset: str = None, __preset_url: str = None):
        """Call popup menu with all presets that are in the folder"""
        # Load data form preset path
        __data = self.load_preset(__preset_url)
        # Get clean name of preset file
        __name = os.path.splitext(os.path.basename(__preset_url))[0]
        self.new_soundevent(__data, __name)

    #=========================================================<  Preset Popup menu  >=======================================================

    def call_soundevent_preset_menu(self):
        """Calls sound events preset menu"""
        presets = list()
        for root, dirs, files in os.walk(SoundEventEditor_Preset_Path):
            for file in files:
                presets.append({file: os.path.join(root, file)})

        self.soundevent_preset_menu = PopupMenu(properties=list(presets), window_name='soundevent_preset_menu')
        self.soundevent_preset_menu.add_property_signal.connect(lambda name, value: self.new_soundevent_preset(name, value))
        self.soundevent_preset_menu.show()

    def load_preset(self, path: str = None):
        """Load data from preset using url"""
        debug(f"LoadPreset from {path}")
        with open(path, 'r') as file:
            __data = file.read()
        __data = Kv3ToJson(__data)
        return __data

    #================================================================<  Hierarchy  >=============================================================

    def update_hierarchy_item(self, item: HierarchyItemModel, _data: dict):
        """Sets the value to the data column and saves if in realtime mode."""
        # Convert the dictionary to a string representation
        item.setText(1, str(_data))
        debug(f'Updated hierarchy item {item.text(0)} with data: \n {_data}')
        if self.realtime_save():
            self.save_soundevents()

    def on_changed_hierarchy_item(self, current_item: HierarchyItemModel):
        """Handles changes in the hierarchy item by updating the properties window."""
        if current_item is not None:
            self.PropertiesWindow.properties_clear()
            self.PropertiesWindow.properties_groups_show()

            # Safely convert column text to dict value
            try:
                data_text = current_item.text(1)
                if data_text:
                    data = ast.literal_eval(data_text)
                    if isinstance(data, dict):
                        self.PropertiesWindow.populate_properties(data)
                    else:
                        raise ValueError("Parsed data is not a dictionary.")
                else:
                    raise ValueError("No data found in the item.")
            except (ValueError, SyntaxError) as e:
                debug(f"Error parsing item data: {e}")
                QMessageBox.warning(self, "Data Error", "Failed to parse item data. Please check the format.")
        else:
            self.PropertiesWindow.properties_clear()
            self.PropertiesWindow.properties_groups_hide()


    # ======================================[Tree widget hierarchy filter]========================================
    def search_hierarchy(self, filter_text, parent_item):
        # Reset the root visibility and start the filtering process
        self.filter_tree_item(parent_item, filter_text.lower(), True)

    def filter_tree_item(self, item, filter_text, is_root=False):
        if not isinstance(item, (HierarchyItemModel, QTreeWidgetItem)):
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
            child_visible = self.filter_tree_item(child_item, filter_text, False)

            if child_visible:
                any_child_visible = True

        # If any child is visible, make sure this item is also visible
        if any_child_visible:
            item.setHidden(False)
            item.setExpanded(True)

        # Return True if this item or any of its children is visible
        return item_visible or any_child_visible

    # ======================================[Tree widget hierarchy context menu]========================================
    def open_hierarchy_menu(self, position):
        menu = QMenu()
        # add_new_preset_lat_action = menu.addAction("(Last) - New from")
        # menu.addSeparator()
        add_new_preset_action = menu.addAction("New event (Preset)")
        add_new_preset_action.triggered.connect(self.call_soundevent_preset_menu)
        add_new_blank_action = menu.addAction("New event (Blank)")
        add_new_blank_action.triggered.connect(self.new_soundevent_blank)
        add_new_preset_action.setShortcut(QKeySequence(QKeySequence("Ctrl+F")))

        menu.addSeparator()

        move_up_action = menu.addAction("Move Up")
        move_up_action.triggered.connect(lambda: self.move_tree_item(self.ui.hierarchy_widget, -1))
        move_up_action.setShortcut(QKeySequence(QKeySequence("Ctrl+Up")))

        move_down_action = menu.addAction("Move Down")
        move_down_action.triggered.connect(lambda: self.move_tree_item(self.ui.hierarchy_widget, 1))
        move_down_action.setShortcut(QKeySequence(QKeySequence("Ctrl+Down")))
        menu.addSeparator()

        remove_action = menu.addAction("Remove")
        # remove_action.triggered.connect(lambda: self.remove_tree_item(self.ui.hierarchy_widget))
        remove_action.triggered.connect(
            lambda: self.undo_stack.push(DeleteTreeItemCommand(self.ui.hierarchy_widget)))
        remove_action.setShortcut(QKeySequence(QKeySequence("Delete")))

        duplicate_action = menu.addAction("Duplicate")
        duplicate_action.triggered.connect(lambda: self.duplicate_hierarchy_items(self.ui.hierarchy_widget))
        duplicate_action.setShortcut(QKeySequence(QKeySequence("Ctrl+D")))

        menu.addSeparator()

        copy_action = menu.addAction("Copy")
        copy_action.setShortcut(QKeySequence(QKeySequence.Copy))
        copy_action.triggered.connect(lambda: self.copy_item(self.ui.hierarchy_widget))

        paste_action = menu.addAction("Paste")
        paste_action.setShortcut(QKeySequence(QKeySequence.Paste))
        paste_action.triggered.connect(lambda: self.paste_item(self.ui.hierarchy_widget, paste_to_parent=True))

        menu.exec(self.ui.hierarchy_widget.viewport().mapToGlobal(position))

    # ======================================[Tree widget functions]========================================

    def move_tree_item(self, tree, direction):
        """Move selected tree items up or down within their parent."""
        selected_items = tree.selectedItems()
        if not selected_items:
            return  # Exit if no items are selected

        # Group items by parent and sort by current index
        parent_to_items = {}
        for item in selected_items:
            parent = item.parent() or tree.invisibleRootItem()
            if parent not in parent_to_items:
                parent_to_items[parent] = []
            parent_to_items[parent].append(item)

        # Move items for each parent separately
        for parent, items in parent_to_items.items():
            # Sort items by their index in reverse if moving down (to avoid index shifting)
            items.sort(key=lambda item: parent.indexOfChild(item), reverse=(direction > 0))

            for item in items:
                current_index = parent.indexOfChild(item)
                new_index = current_index + direction

                # Check bounds
                if 0 <= new_index < parent.childCount():
                    # Move item
                    parent.takeChild(current_index)
                    parent.insertChild(new_index, item)

        tree.clearSelection()
        for item in selected_items:
            item.setSelected(True)
        tree.scrollToItem(selected_items[-1] if direction > 0 else selected_items[0])

    def copy_item(self, tree, copy_to_clipboard=True):
        """Coping Tree item"""
        # Gathering selected items
        selected_indexes = tree.selectedIndexes()
        selected_items = [tree.itemFromIndex(index) for index in selected_indexes]

        # Remove the same items
        selected_items = list(set(selected_items))

        for tree_item in selected_items:
            item_data = self.serialization_hierarchy_items(item=tree_item)
        # Output
        if copy_to_clipboard:
            clipboard = QApplication.clipboard()
            clipboard.setText(JsonToKv3(item_data))
        else:
            return JsonToKv3(item_data)

    def paste_item(self, tree, data_input=None, paste_to_parent=False):
        """Pasting tree item"""
        if data_input is None:
            data_input = QApplication.clipboard().text()
        try:
            input = Kv3ToJson(data_input)
            if 'm_Children' in input:
                for key in input['m_Children']:
                    tree_item = self.deserialize_hierarchy_item(key)
                    try:
                        if paste_to_parent:
                            tree.currentItem().parent().addChild(tree_item)
                        else:
                            tree.currentItem().addChild(tree_item)
                    except:
                        tree.invisibleRootItem().addChild(tree_item)
            else:
                tree_item = self.deserialize_hierarchy_item(input)
                try:
                    if paste_to_parent:
                        tree.currentItem().parent().addChild(tree_item)
                    else:
                        tree.currentItem().addChild(tree_item)
                except:
                    tree.invisibleRootItem().addChild(tree_item)
        except Exception as error:
            error_message = str(error)
            error_dialog = ErrorInfo(text="Wrong format of the pasting content", details=error_message)
            error_dialog.exec()

    def remove_tree_item(self, tree):
        """Removing Tree item"""
        selected_indexes = tree.selectedIndexes()
        selected_items = [tree.itemFromIndex(index) for index in selected_indexes]
        for item in selected_items:
            if item:
                if item == item.treeWidget().invisibleRootItem():
                    pass
                else:
                    parent = item.parent() or item.treeWidget().invisibleRootItem()
                    index = parent.indexOfChild(item)
                    parent.takeChild(index)

    def duplicate_hierarchy_items(self, tree):
        data = self.copy_item(tree=tree, copy_to_clipboard=False)
        self.paste_item(tree, data, paste_to_parent=True)

    # ======================================[Tree item serialization and deserialization]========================================

    def serialization_hierarchy_items(self, item, data=None):
        """Convert tree structure to json"""
        if data is None:
            data = {'m_Children': []}
        value_row = item.text(1)
        parent_data = ast.literal_eval(value_row)
        # Label form tree element name
        parent_data['m_sLabel'] = item.text(0)
        if item.childCount() > 0:
            parent_data['m_Children'] = []
        data['m_Children'].append(parent_data)
        if item.childCount() > 0:
            for index in range(item.childCount()):
                child = item.child(index)
                key = child.text(0)
                value_row = child.text(1)

                child_data = ast.literal_eval(value_row)
                child_data['m_sLabel'] = key

                if child.childCount() > 0:
                    child_data['m_Children'] = []
                    self.serialization_hierarchy_items(child, child_data)

                parent_data['m_Children'].append(child_data)

        return data

    def deserialize_hierarchy_item(self, m_Children=HierarchyItemModel):
        item_value = {}

        # If there is a dict with child element, copy all expect child key in a new variable, and process it.
        for key in m_Children:
            if key == 'm_Children':
                pass
            else:
                item_value.update({key: m_Children[key]})
        # Get tree item name
        name = item_value.get('m_sLabel', 'None')

        # New element
        tree_item = HierarchyItemModel(_data=item_value, _name=name)
        return tree_item

    #===========================================================<  Preset Manager  >========================================================
    def OpenPresetManager(self):
        self.PresetManager = SoundEventEditorPresetManagerWindow()
        self.PresetManager.show()

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

    #============================================================<  File actions  >=========================================================
    def save_file(self, file_path):
        """Serializing tree and save to the filepath"""
